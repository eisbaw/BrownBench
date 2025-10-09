"""Unit tests for container isolation."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from codegen_bench.security.isolation import (
    ContainerConfig,
    ContainerIsolation,
    ContainerIsolationError,
    NetworkConfig,
    ResourceLimits,
)


class TestResourceLimits:
    """Tests for ResourceLimits dataclass."""

    def test_default_limits(self) -> None:
        """Test default resource limits."""
        limits = ResourceLimits()
        assert limits.cpu_count == 1.0
        assert limits.memory_mb == 512
        assert limits.timeout_seconds == 300

    def test_custom_limits(self) -> None:
        """Test custom resource limits."""
        limits = ResourceLimits(
            cpu_count=2.0,
            memory_mb=1024,
            timeout_seconds=600,
        )
        assert limits.cpu_count == 2.0
        assert limits.memory_mb == 1024
        assert limits.timeout_seconds == 600

    def test_no_limits(self) -> None:
        """Test resource limits with None values."""
        limits = ResourceLimits(
            cpu_count=None,
            memory_mb=None,
            timeout_seconds=None,
        )
        assert limits.cpu_count is None
        assert limits.memory_mb is None
        assert limits.timeout_seconds is None

    def test_invalid_cpu_count(self) -> None:
        """Test validation rejects negative CPU count."""
        with pytest.raises(ValueError, match="cpu_count must be positive"):
            ResourceLimits(cpu_count=-1.0)

    def test_invalid_memory(self) -> None:
        """Test validation rejects negative memory."""
        with pytest.raises(ValueError, match="memory_mb must be positive"):
            ResourceLimits(memory_mb=-512)

    def test_invalid_timeout(self) -> None:
        """Test validation rejects negative timeout."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            ResourceLimits(timeout_seconds=-10)

    def test_zero_cpu_count(self) -> None:
        """Test validation rejects zero CPU count."""
        with pytest.raises(ValueError, match="cpu_count must be positive"):
            ResourceLimits(cpu_count=0.0)


class TestNetworkConfig:
    """Tests for NetworkConfig dataclass."""

    def test_default_network(self) -> None:
        """Test default network configuration."""
        config = NetworkConfig()
        assert config.enabled is True
        assert config.proxy_host is None
        assert config.proxy_port is None
        assert config.allowed_hosts is None

    def test_network_disabled(self) -> None:
        """Test network disabled configuration."""
        config = NetworkConfig(enabled=False)
        assert config.enabled is False

    def test_network_with_proxy(self) -> None:
        """Test network configuration with proxy."""
        config = NetworkConfig(
            enabled=True,
            proxy_host="localhost",
            proxy_port=8080,
        )
        assert config.enabled is True
        assert config.proxy_host == "localhost"
        assert config.proxy_port == 8080

    def test_network_with_allowed_hosts(self) -> None:
        """Test network configuration with allowed hosts."""
        config = NetworkConfig(
            enabled=True,
            allowed_hosts=["api.anthropic.com", "api.openai.com"],
        )
        assert config.allowed_hosts == ["api.anthropic.com", "api.openai.com"]


class TestContainerConfig:
    """Tests for ContainerConfig dataclass."""

    def test_minimal_config(self) -> None:
        """Test minimal container configuration."""
        config = ContainerConfig(image="python:3.11-slim")
        assert config.image == "python:3.11-slim"
        assert config.work_dir == "/workspace"
        assert isinstance(config.resources, ResourceLimits)
        assert isinstance(config.network, NetworkConfig)

    def test_full_config(self) -> None:
        """Test full container configuration."""
        resources = ResourceLimits(cpu_count=2.0, memory_mb=1024)
        network = NetworkConfig(enabled=True, proxy_host="localhost", proxy_port=8080)

        config = ContainerConfig(
            image="python:3.11-slim",
            resources=resources,
            network=network,
            work_dir="/app",
            read_only_paths=("/src",),
            read_write_paths=("/tmp",),
        )

        assert config.image == "python:3.11-slim"
        assert config.resources == resources
        assert config.network == network
        assert config.work_dir == "/app"
        assert config.read_only_paths == ("/src",)
        assert config.read_write_paths == ("/tmp",)


class TestContainerIsolation:
    """Tests for ContainerIsolation class."""

    @patch("subprocess.run")
    def test_verify_docker_success(self, mock_run: MagicMock) -> None:
        """Test Docker verification succeeds."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker", "version"],
            returncode=0,
            stdout="Docker version 20.10.0",
            stderr="",
        )

        config = ContainerConfig(image="python:3.11-slim")
        isolation = ContainerIsolation(config)
        assert isolation is not None

        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_verify_docker_failure(self, mock_run: MagicMock) -> None:
        """Test Docker verification fails."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker", "version"],
            returncode=1,
            stdout="",
            stderr="Docker not running",
        )

        config = ContainerConfig(image="python:3.11-slim")
        with pytest.raises(ContainerIsolationError, match="Docker not available"):
            ContainerIsolation(config)

    @patch("subprocess.run")
    def test_verify_docker_not_found(self, mock_run: MagicMock) -> None:
        """Test Docker not installed."""
        mock_run.side_effect = FileNotFoundError("docker not found")

        config = ContainerConfig(image="python:3.11-slim")
        with pytest.raises(ContainerIsolationError, match="Docker not available"):
            ContainerIsolation(config)

    @patch("subprocess.run")
    def test_build_image_success(self, mock_run: MagicMock) -> None:
        """Test successful image build."""
        # Mock docker version check
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "build"], returncode=0, stdout="Successfully built", stderr=""
            ),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)
        isolation.build_image("Dockerfile", build_context=".")

        # Verify build command
        build_call = mock_run.call_args_list[1]
        assert "docker" in build_call[0][0]
        assert "build" in build_call[0][0]
        assert "-t" in build_call[0][0]
        assert "test-image:latest" in build_call[0][0]

    @patch("subprocess.run")
    def test_build_image_with_args(self, mock_run: MagicMock) -> None:
        """Test image build with build args."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "build"], returncode=0, stdout="", stderr=""
            ),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)
        isolation.build_image(
            "Dockerfile",
            build_args={"PYTHON_VERSION": "3.11", "BASE_IMAGE": "slim"},
        )

        build_call = mock_run.call_args_list[1]
        args = build_call[0][0]
        assert "--build-arg" in args
        assert "PYTHON_VERSION=3.11" in args
        assert "BASE_IMAGE=slim" in args

    @patch("subprocess.run")
    def test_build_image_failure(self, mock_run: MagicMock) -> None:
        """Test image build failure."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "build"],
                returncode=1,
                stdout="",
                stderr="Build failed",
            ),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)

        with pytest.raises(ContainerIsolationError, match="Failed to build image"):
            isolation.build_image("Dockerfile")

    @patch("subprocess.run")
    def test_build_image_timeout(self, mock_run: MagicMock) -> None:
        """Test image build timeout."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.TimeoutExpired(cmd=["docker", "build"], timeout=300),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)

        with pytest.raises(ContainerIsolationError, match="build timed out"):
            isolation.build_image("Dockerfile")

    @patch("subprocess.run")
    def test_execute_basic_command(self, mock_run: MagicMock) -> None:
        """Test basic command execution."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "run"],
                returncode=0,
                stdout="Hello, World!",
                stderr="",
            ),
        ]

        config = ContainerConfig(image="python:3.11-slim")
        isolation = ContainerIsolation(config)
        result = isolation.execute(["echo", "Hello, World!"], mount_temp_dir=False)

        assert result.returncode == 0
        assert result.stdout == "Hello, World!"

        # Verify docker run command
        run_call = mock_run.call_args_list[1]
        args = run_call[0][0]
        assert "docker" in args
        assert "run" in args
        assert "--rm" in args
        assert "python:3.11-slim" in args

    @patch("subprocess.run")
    def test_execute_with_resource_limits(self, mock_run: MagicMock) -> None:
        """Test command execution with resource limits."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(args=["docker", "run"], returncode=0, stdout="", stderr=""),
        ]

        resources = ResourceLimits(cpu_count=2.0, memory_mb=1024, timeout_seconds=60)
        config = ContainerConfig(image="python:3.11-slim", resources=resources)
        isolation = ContainerIsolation(config)
        isolation.execute(["python", "--version"], mount_temp_dir=False)

        run_call = mock_run.call_args_list[1]
        args = run_call[0][0]
        assert "--cpus" in args
        assert "2.0" in args
        assert "-m" in args
        assert "1024m" in args

    @patch("subprocess.run")
    def test_execute_with_network_disabled(self, mock_run: MagicMock) -> None:
        """Test command execution with network disabled."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(args=["docker", "run"], returncode=0, stdout="", stderr=""),
        ]

        network = NetworkConfig(enabled=False)
        config = ContainerConfig(image="python:3.11-slim", network=network)
        isolation = ContainerIsolation(config)
        isolation.execute(["python", "--version"], mount_temp_dir=False)

        run_call = mock_run.call_args_list[1]
        args = run_call[0][0]
        assert "--network=none" in args

    @patch("subprocess.run")
    def test_execute_with_proxy(self, mock_run: MagicMock) -> None:
        """Test command execution with proxy configuration."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(args=["docker", "run"], returncode=0, stdout="", stderr=""),
        ]

        network = NetworkConfig(enabled=True, proxy_host="localhost", proxy_port=8080)
        config = ContainerConfig(image="python:3.11-slim", network=network)
        isolation = ContainerIsolation(config)
        isolation.execute(["python", "--version"], mount_temp_dir=False)

        run_call = mock_run.call_args_list[1]
        args = run_call[0][0]
        assert "-e" in args
        # Check for proxy environment variables
        proxy_vars = [arg for arg in args if "PROXY" in arg]
        assert any("HTTP_PROXY=http://localhost:8080" in var for var in proxy_vars)
        assert any("HTTPS_PROXY=http://localhost:8080" in var for var in proxy_vars)

    @patch("subprocess.run")
    def test_execute_with_env_vars(self, mock_run: MagicMock) -> None:
        """Test command execution with environment variables."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(args=["docker", "run"], returncode=0, stdout="", stderr=""),
        ]

        config = ContainerConfig(image="python:3.11-slim")
        isolation = ContainerIsolation(config)
        isolation.execute(
            ["python", "--version"],
            env={"API_KEY": "test-key", "DEBUG": "true"},
            mount_temp_dir=False,
        )

        run_call = mock_run.call_args_list[1]
        args = run_call[0][0]
        assert "API_KEY=test-key" in args
        assert "DEBUG=true" in args

    @patch("subprocess.run")
    def test_execute_timeout(self, mock_run: MagicMock) -> None:
        """Test command execution timeout."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.TimeoutExpired(cmd=["docker", "run"], timeout=60),
        ]

        resources = ResourceLimits(timeout_seconds=60)
        config = ContainerConfig(image="python:3.11-slim", resources=resources)
        isolation = ContainerIsolation(config)

        with pytest.raises(ContainerIsolationError, match="timed out after 60 seconds"):
            isolation.execute(["sleep", "120"], mount_temp_dir=False)

    @patch("subprocess.run")
    def test_cleanup_image_success(self, mock_run: MagicMock) -> None:
        """Test successful image cleanup."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(args=["docker", "rmi"], returncode=0, stdout="", stderr=""),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)
        isolation.cleanup_image()

        rmi_call = mock_run.call_args_list[1]
        assert "rmi" in rmi_call[0][0]
        assert "test-image:latest" in rmi_call[0][0]

    @patch("subprocess.run")
    def test_cleanup_image_not_found(self, mock_run: MagicMock) -> None:
        """Test cleanup when image doesn't exist."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "rmi"],
                returncode=1,
                stdout="",
                stderr="No such image",
            ),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)
        # Should not raise error when image doesn't exist
        isolation.cleanup_image()

    @patch("subprocess.run")
    def test_cleanup_containers(self, mock_run: MagicMock) -> None:
        """Test container cleanup."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "container", "prune"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)
        isolation.cleanup_containers()

        prune_call = mock_run.call_args_list[1]
        args = prune_call[0][0]
        assert "container" in args
        assert "prune" in args
        assert "-f" in args

    @patch("subprocess.run")
    def test_cleanup_containers_with_label(self, mock_run: MagicMock) -> None:
        """Test container cleanup with label filter."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "container", "prune"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        config = ContainerConfig(image="test-image:latest")
        isolation = ContainerIsolation(config)
        isolation.cleanup_containers(label="app=brownbench")

        prune_call = mock_run.call_args_list[1]
        args = prune_call[0][0]
        assert "--filter" in args
        assert "label=app=brownbench" in args

    @patch("subprocess.run")
    def test_image_exists_true(self, mock_run: MagicMock) -> None:
        """Test image exists check returns True."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "image", "inspect"],
                returncode=0,
                stdout="[{...}]",
                stderr="",
            ),
        ]

        config = ContainerConfig(image="python:3.11-slim")
        isolation = ContainerIsolation(config)
        assert isolation.image_exists() is True

    @patch("subprocess.run")
    def test_image_exists_false(self, mock_run: MagicMock) -> None:
        """Test image exists check returns False."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "image", "inspect"],
                returncode=1,
                stdout="",
                stderr="No such image",
            ),
        ]

        config = ContainerConfig(image="nonexistent:latest")
        isolation = ContainerIsolation(config)
        assert isolation.image_exists() is False

    @patch("subprocess.run")
    def test_list_images(self, mock_run: MagicMock) -> None:
        """Test listing Docker images."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "version"], returncode=0, stdout="", stderr=""
            ),
            subprocess.CompletedProcess(
                args=["docker", "images"],
                returncode=0,
                stdout='{"Repository":"python","Tag":"3.11-slim"}\n{"Repository":"ubuntu","Tag":"22.04"}',
                stderr="",
            ),
        ]

        config = ContainerConfig(image="python:3.11-slim")
        isolation = ContainerIsolation(config)
        images = isolation.list_images()

        assert len(images) == 2
        assert images[0]["Repository"] == "python"
        assert images[1]["Repository"] == "ubuntu"
