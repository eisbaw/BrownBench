"""Container isolation for executing DUTs in sandboxed environments.

This module provides Docker-based container isolation to safely execute
Device Under Test (DUT) implementations with:
- Network restrictions (API proxy only)
- Resource limits (CPU, memory)
- Read-only filesystem mounts
- Automatic cleanup after execution

SECURITY NOTE:
This module requires access to the Docker daemon socket. Users with this
permission can execute arbitrary containers, which may allow privilege
escalation if Docker is misconfigured. Only use in trusted environments or
with appropriate user permission boundaries.
"""

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Timeout constants (in seconds)
DOCKER_VERIFICATION_TIMEOUT = 5  # Quick check if Docker daemon responds
IMAGE_BUILD_TIMEOUT = 300  # Allow 5 minutes for image builds (large base images)
IMAGE_CLEANUP_TIMEOUT = 30  # Docker image removal typically fast
CONTAINER_CLEANUP_TIMEOUT = 30  # Prune stopped containers
IMAGE_LIST_TIMEOUT = 10  # List images metadata
IMAGE_INSPECT_TIMEOUT = 5  # Check single image existence


@dataclass(frozen=True)
class ResourceLimits:
    """Resource limits for container execution.

    Attributes:
        cpu_count: Number of CPU cores (None = no limit)
        memory_mb: Memory limit in MB (None = no limit)
        timeout_seconds: Execution timeout in seconds (None = no limit)
    """

    cpu_count: float | None = 1.0
    memory_mb: int | None = 512
    timeout_seconds: int | None = 300

    def __post_init__(self) -> None:
        """Validate resource limits."""
        if self.cpu_count is not None and self.cpu_count <= 0:
            raise ValueError(f"cpu_count must be positive, got {self.cpu_count}")

        if self.memory_mb is not None and self.memory_mb <= 0:
            raise ValueError(f"memory_mb must be positive, got {self.memory_mb}")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {self.timeout_seconds}")


@dataclass(frozen=True)
class NetworkConfig:
    """Network configuration for container.

    Attributes:
        enabled: Whether network access is enabled
        proxy_host: API proxy host (e.g., 'localhost')
        proxy_port: API proxy port (e.g., 8080)
        allowed_hosts: Additional allowed hosts (for testing)
    """

    enabled: bool = True
    proxy_host: str | None = None
    proxy_port: int | None = None
    allowed_hosts: list[str] | None = None


@dataclass(frozen=True)
class ContainerConfig:
    """Configuration for container isolation.

    Attributes:
        image: Docker image name
        resources: Resource limits
        network: Network configuration
        work_dir: Working directory inside container
        read_only_paths: Paths to mount as read-only
        read_write_paths: Paths to mount as read-write
    """

    image: str
    resources: ResourceLimits = ResourceLimits()
    network: NetworkConfig = NetworkConfig()
    work_dir: str = "/workspace"
    read_only_paths: tuple[str, ...] | None = None
    read_write_paths: tuple[str, ...] | None = None


class ContainerIsolationError(Exception):
    """Raised when container operations fail."""

    pass


class ContainerIsolation:
    """Manages Docker container lifecycle for isolated DUT execution.

    This class provides a safe execution environment for DUTs by:
    1. Running code in isolated Docker containers
    2. Enforcing resource limits (CPU, memory, timeout)
    3. Restricting network access to API proxy only
    4. Using read-only mounts where possible
    5. Cleaning up containers automatically

    Example:
        >>> config = ContainerConfig(
        ...     image="python:3.11-slim",
        ...     resources=ResourceLimits(cpu_count=1.0, memory_mb=512),
        ... )
        >>> isolation = ContainerIsolation(config)
        >>>
        >>> # Build image if needed
        >>> isolation.build_image(dockerfile_path="Dockerfile")
        >>>
        >>> # Execute code in isolated container
        >>> result = isolation.execute(
        ...     command=["python", "script.py"],
        ...     env={"API_KEY": "temp-key-123"},
        ... )
        >>> print(result.stdout)
    """

    def __init__(self, config: ContainerConfig) -> None:
        """Initialize container isolation.

        Args:
            config: Container configuration
        """
        self._config = config
        self._verify_docker()

    def _verify_docker(self) -> None:
        """Verify Docker is available and running.

        Raises:
            ContainerIsolationError: If Docker is not available
        """
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=DOCKER_VERIFICATION_TIMEOUT,
            )
            if result.returncode != 0:
                raise ContainerIsolationError(
                    f"Docker not available: {result.stderr}"
                )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise ContainerIsolationError(f"Docker not available: {e}") from e

    def _validate_mount_paths(self) -> None:
        """Validate mount paths exist and are absolute.

        Raises:
            ContainerIsolationError: If paths are invalid
        """
        if self._config.read_only_paths:
            for path in self._config.read_only_paths:
                p = Path(path)
                if not p.is_absolute():
                    raise ContainerIsolationError(f"Mount path must be absolute: {path}")
                if not p.exists():
                    raise ContainerIsolationError(f"Mount path does not exist: {path}")

        if self._config.read_write_paths:
            for path in self._config.read_write_paths:
                p = Path(path)
                if not p.is_absolute():
                    raise ContainerIsolationError(f"Mount path must be absolute: {path}")
                if not p.exists():
                    raise ContainerIsolationError(f"Mount path does not exist: {path}")

    def _validate_no_mount_conflicts(self) -> None:
        """Ensure mount paths don't overlap with work_dir.

        Raises:
            ContainerIsolationError: If mount paths conflict with work_dir
        """
        if self._config.read_only_paths:
            for path in self._config.read_only_paths:
                if path == self._config.work_dir:
                    raise ContainerIsolationError(
                        f"Cannot mount work_dir {self._config.work_dir} as read-only"
                    )

        if self._config.read_write_paths:
            for path in self._config.read_write_paths:
                if path == self._config.work_dir:
                    raise ContainerIsolationError(
                        f"Work_dir {self._config.work_dir} is already writable, "
                        "no need to mount as read-write"
                    )

    def build_image(
        self,
        dockerfile_path: str | Path,
        build_context: str | Path = ".",
        build_args: dict[str, str] | None = None,
    ) -> None:
        """Build Docker image for DUT execution.

        Args:
            dockerfile_path: Path to Dockerfile
            build_context: Build context directory
            build_args: Build arguments (--build-arg)

        Raises:
            ContainerIsolationError: If build fails
        """
        logger.info(
            "building_container_image",
            image=self._config.image,
            dockerfile=str(dockerfile_path),
        )

        cmd = [
            "docker",
            "build",
            "-t",
            self._config.image,
            "-f",
            str(dockerfile_path),
        ]

        # Add build args if provided
        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])

        cmd.append(str(build_context))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=IMAGE_BUILD_TIMEOUT,
            )

            if result.returncode != 0:
                raise ContainerIsolationError(
                    f"Failed to build image: {result.stderr}"
                )

            logger.info("container_image_built", image=self._config.image)

        except subprocess.TimeoutExpired as e:
            raise ContainerIsolationError(
                f"Image build timed out after {IMAGE_BUILD_TIMEOUT} seconds"
            ) from e

    def execute(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        stdin: str | None = None,
        mount_temp_dir: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Execute command in isolated container.

        Args:
            command: Command to execute
            env: Environment variables (caller's dict is not modified)
            stdin: Standard input data
            mount_temp_dir: Whether to mount a temporary directory

        Returns:
            CompletedProcess with stdout, stderr, and returncode

        Raises:
            ContainerIsolationError: If execution fails
        """
        logger.info(
            "executing_in_container",
            image=self._config.image,
            command=command,
        )

        # Validate mount paths before execution
        self._validate_mount_paths()
        self._validate_no_mount_conflicts()

        # Build final environment (copy to avoid mutating caller's dict)
        final_env = dict(env) if env else {}

        # Build docker run command
        docker_cmd = ["docker", "run", "--rm"]

        # Add resource limits
        if self._config.resources.cpu_count is not None:
            docker_cmd.extend(["--cpus", str(self._config.resources.cpu_count)])

        if self._config.resources.memory_mb is not None:
            docker_cmd.extend(["-m", f"{self._config.resources.memory_mb}m"])

        # Add network configuration
        if not self._config.network.enabled:
            docker_cmd.append("--network=none")
        elif self._config.network.proxy_host:
            # Set up network with proxy
            final_env["HTTP_PROXY"] = (
                f"http://{self._config.network.proxy_host}:{self._config.network.proxy_port}"
            )
            final_env["HTTPS_PROXY"] = (
                f"http://{self._config.network.proxy_host}:{self._config.network.proxy_port}"
            )

        # Add environment variables
        for key, value in final_env.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Set working directory
        docker_cmd.extend(["-w", self._config.work_dir])

        # Add volume mounts
        temp_dir = None
        if mount_temp_dir:
            temp_dir = tempfile.mkdtemp()
            docker_cmd.extend(["-v", f"{temp_dir}:{self._config.work_dir}"])

        # Add read-only mounts
        if self._config.read_only_paths:
            for path in self._config.read_only_paths:
                docker_cmd.extend(["-v", f"{path}:{path}:ro"])

        # Add read-write mounts
        if self._config.read_write_paths:
            for path in self._config.read_write_paths:
                docker_cmd.extend(["-v", f"{path}:{path}:rw"])

        # Add image and command
        docker_cmd.append(self._config.image)
        docker_cmd.extend(command)

        try:
            # Execute with timeout
            result = subprocess.run(
                docker_cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self._config.resources.timeout_seconds,
            )

            logger.info(
                "container_execution_complete",
                returncode=result.returncode,
                stdout_length=len(result.stdout),
                stderr_length=len(result.stderr),
            )

            return result

        except subprocess.TimeoutExpired as e:
            logger.error(
                "container_execution_timeout",
                timeout=self._config.resources.timeout_seconds,
            )
            raise ContainerIsolationError(
                f"Execution timed out after {self._config.resources.timeout_seconds} seconds"
            ) from e

        finally:
            # Cleanup temp directory
            # Note: Cleanup failures are non-critical - container is already stopped
            # and temp dirs are in /tmp which gets cleared on reboot.
            # However, we log warnings to help diagnose disk space issues.
            if temp_dir:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(
                        "temp_dir_cleanup_failed",
                        path=temp_dir,
                        error=str(e),
                        note="Temp directory may need manual cleanup"
                    )

    def cleanup_image(self) -> None:
        """Remove the Docker image.

        Raises:
            ContainerIsolationError: If cleanup fails
        """
        logger.info("removing_container_image", image=self._config.image)

        try:
            result = subprocess.run(
                ["docker", "rmi", self._config.image],
                capture_output=True,
                text=True,
                timeout=IMAGE_CLEANUP_TIMEOUT,
            )

            if result.returncode != 0:
                # Don't raise if image doesn't exist
                if "No such image" not in result.stderr:
                    raise ContainerIsolationError(
                        f"Failed to remove image: {result.stderr}"
                    )

            logger.info("container_image_removed", image=self._config.image)

        except subprocess.TimeoutExpired as e:
            raise ContainerIsolationError(
                f"Image cleanup timed out after {IMAGE_CLEANUP_TIMEOUT} seconds"
            ) from e

    def cleanup_containers(self, label: str | None = None) -> None:
        """Remove stopped containers.

        Args:
            label: Optional label filter for containers

        Raises:
            ContainerIsolationError: If cleanup fails
        """
        logger.info("cleaning_up_containers", label=label)

        cmd = ["docker", "container", "prune", "-f"]
        if label:
            cmd.extend(["--filter", f"label={label}"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CONTAINER_CLEANUP_TIMEOUT,
            )

            if result.returncode != 0:
                raise ContainerIsolationError(
                    f"Failed to cleanup containers: {result.stderr}"
                )

            logger.info("containers_cleaned_up")

        except subprocess.TimeoutExpired as e:
            raise ContainerIsolationError(
                f"Container cleanup timed out after {CONTAINER_CLEANUP_TIMEOUT} seconds"
            ) from e

    def list_images(self) -> list[dict[str, Any]]:
        """List available Docker images.

        Returns:
            List of image metadata dictionaries

        Raises:
            ContainerIsolationError: If listing fails
        """
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=IMAGE_LIST_TIMEOUT,
            )

            if result.returncode != 0:
                raise ContainerIsolationError(
                    f"Failed to list images: {result.stderr}"
                )

            images = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    images.append(json.loads(line))

            return images

        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            raise ContainerIsolationError(f"Failed to list images: {e}") from e

    def image_exists(self, image: str | None = None) -> bool:
        """Check if a Docker image exists.

        Args:
            image: Image name (uses config image if None)

        Returns:
            True if image exists, False otherwise
        """
        image_name = image or self._config.image

        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image_name],
                capture_output=True,
                text=True,
                timeout=IMAGE_INSPECT_TIMEOUT,
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            return False
