"""Integration tests for CLI commands."""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from codegen_bench.cli.main import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic API response."""
    mock_response = Mock()
    mock_response.content = [
        Mock(
            text="""```c:src/hello.c
#include "hello.h"
#include <stdio.h>

int hello_world(void) {
    printf("Hello, World!\\n");
    return 0;
}
```

```c:src/hello.h
#ifndef HELLO_H
#define HELLO_H

int hello_world(void);

#endif
```
"""
        )
    ]
    mock_response.usage = Mock(input_tokens=100, output_tokens=50)
    return mock_response


def test_cli_help(runner):
    """Test CLI help output."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "AI Code Generation Benchmark Suite" in result.output
    assert "generate" in result.output
    assert "validate" in result.output
    assert "init" in result.output


def test_init_command(runner, tmp_path):
    """Test init command creates directory structure."""
    output_dir = tmp_path / "benchmark"

    result = runner.invoke(cli, ["init", str(output_dir)])

    assert result.exit_code == 0
    assert output_dir.exists()
    assert (output_dir / "tasks").exists()
    assert (output_dir / "projects").exists()
    assert "Initialization complete" in result.output


def test_init_command_with_tasks(runner, tmp_path):
    """Test init command with task specification."""
    output_dir = tmp_path / "benchmark"

    result = runner.invoke(cli, ["init", "--tasks", "core", str(output_dir)])

    assert result.exit_code == 0
    assert "Task set: core" in result.output


def test_generate_command_missing_task(runner):
    """Test generate command with non-existent task."""
    result = runner.invoke(
        cli, ["generate", "--dut", "simple-chat", "--task-id", "nonexistent"]
    )

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or isinstance(result.exception, SystemExit)


def test_generate_command_missing_api_key(runner, tmp_path):
    """Test generate command without API key and no cache."""
    cache_dir = tmp_path / "empty_cache"
    cache_dir.mkdir()

    with patch("os.getenv", return_value=None):
        result = runner.invoke(
            cli, [
                "--cache-dir", str(cache_dir),
                "generate",
                "--dut", "simple-chat",
                "--task-id", "task_001",
                "--no-cache"
            ]
        )

        # Should fail with API key error
        assert result.exit_code != 0


def test_generate_command_with_mock(runner, tmp_path, mock_anthropic_response):
    """Test generate command with mocked API."""
    output_file = tmp_path / "solution.json"

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client

        with patch("os.getenv", return_value="test-key-12345"):
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--dut",
                    "simple-chat",
                    "--task-id",
                    "task_001",
                    "--output",
                    str(output_file),
                ],
            )

    assert result.exit_code == 0
    assert "Solution generated" in result.output
    assert output_file.exists()

    # Verify solution file
    with open(output_file) as f:
        solution = json.load(f)

    assert solution["task_id"] == "task_001"
    assert solution["approach_id"] == "simple-chat"


def test_generate_command_with_cache(runner, tmp_path, mock_anthropic_response):
    """Test generate command uses cache."""
    cache_dir = tmp_path / "cache"

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client

        with patch("os.getenv", return_value="test-key-12345"):
            # First run - should call API
            result1 = runner.invoke(
                cli,
                [
                    "--cache-dir",
                    str(cache_dir),
                    "generate",
                    "--dut",
                    "simple-chat",
                    "--task-id",
                    "task_001",
                ],
            )

            assert result1.exit_code == 0
            api_calls_1 = mock_client.messages.create.call_count

            # Second run - should use cache
            result2 = runner.invoke(
                cli,
                [
                    "--cache-dir",
                    str(cache_dir),
                    "generate",
                    "--dut",
                    "simple-chat",
                    "--task-id",
                    "task_001",
                ],
            )

            assert result2.exit_code == 0
            assert "Using cached solution" in result2.output
            api_calls_2 = mock_client.messages.create.call_count

            # API should not be called again
            assert api_calls_2 == api_calls_1


def test_generate_command_no_cache(runner, tmp_path, mock_anthropic_response):
    """Test generate command with --no-cache flag."""
    cache_dir = tmp_path / "cache"

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client

        with patch("os.getenv", return_value="test-key-12345"):
            # First run
            result1 = runner.invoke(
                cli,
                [
                    "--cache-dir",
                    str(cache_dir),
                    "generate",
                    "--dut",
                    "simple-chat",
                    "--task-id",
                    "task_001",
                ],
            )

            assert result1.exit_code == 0
            api_calls_1 = mock_client.messages.create.call_count

            # Second run with --no-cache
            result2 = runner.invoke(
                cli,
                [
                    "--cache-dir",
                    str(cache_dir),
                    "generate",
                    "--dut",
                    "simple-chat",
                    "--task-id",
                    "task_001",
                    "--no-cache",
                ],
            )

            assert result2.exit_code == 0
            assert "Using cached" not in result2.output
            api_calls_2 = mock_client.messages.create.call_count

            # API should be called again
            assert api_calls_2 == api_calls_1 + 1


def test_validate_command_missing_solution(runner):
    """Test validate command with non-existent solution file."""
    result = runner.invoke(cli, ["validate", "/nonexistent/solution.json"])

    assert result.exit_code != 0


def test_validate_command(runner, tmp_path, mock_anthropic_response):
    """Test validate command with generated solution."""
    solution_file = tmp_path / "solution.json"

    # First generate a solution
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client

        with patch("os.getenv", return_value="test-key-12345"):
            gen_result = runner.invoke(
                cli,
                [
                    "generate",
                    "--dut",
                    "simple-chat",
                    "--task-id",
                    "task_001",
                    "--output",
                    str(solution_file),
                ],
            )

            assert gen_result.exit_code == 0

    # Now validate it
    val_result = runner.invoke(cli, ["validate", str(solution_file), "--all"])

    # Should succeed (may fail compilation if gcc not available, but CLI should work)
    assert val_result.exit_code == 0 or "Error" in val_result.output
    assert "Validating solution" in val_result.output
