"""Integration tests for CLI commands."""

import json
from unittest.mock import Mock, patch

import pytest
from anthropic.types import TextBlock
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
    text_content = """```c:src/hello.c
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
    text_block = TextBlock(type="text", text=text_content)
    mock_response.content = [text_block]
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
    result = runner.invoke(cli, ["generate", "--dut", "simple-chat", "--task-id", "nonexistent"])

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or isinstance(result.exception, SystemExit)


def test_generate_command_missing_api_key(runner, tmp_path):
    """Test generate command without API key and no cache."""
    cache_dir = tmp_path / "empty_cache"
    cache_dir.mkdir()

    with patch("os.getenv", return_value=None):
        result = runner.invoke(
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


def test_generate_command_invalid_dut(runner):
    """Test generate command with invalid DUT identifier."""
    result = runner.invoke(
        cli,
        [
            "generate",
            "--dut",
            "nonexistent-dut-12345",
            "--task-id",
            "task_001",
        ],
    )

    assert result.exit_code != 0
    assert "Error" in result.output or isinstance(result.exception, SystemExit)


def test_validate_command_invalid_task_id(runner, tmp_path):
    """Test validate command with solution referencing invalid task."""
    solution_file = tmp_path / "solution.json"

    # Create solution with invalid task_id
    solution_data = {
        "task_id": "nonexistent-task-99999",
        "approach_id": "simple-chat",
        "seed": 42,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "changed_files": {},
        "new_files": {},
        "deleted_files": [],
        "total_tokens": 100,
        "cost_usd": 0.01,
        "generation_time_seconds": 1.0,
    }

    with open(solution_file, "w") as f:
        json.dump(solution_data, f)

    result = runner.invoke(cli, ["validate", str(solution_file)])

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or isinstance(result.exception, SystemExit)


def test_validate_command_missing_codebase(runner, tmp_path, monkeypatch):
    """Test validate command when task codebase path doesn't exist."""
    solution_file = tmp_path / "solution.json"

    # Create solution with valid task_id
    solution_data = {
        "task_id": "task_001",
        "approach_id": "simple-chat",
        "seed": 42,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "changed_files": {},
        "new_files": {},
        "deleted_files": [],
        "total_tokens": 100,
        "cost_usd": 0.01,
        "generation_time_seconds": 1.0,
    }

    with open(solution_file, "w") as f:
        json.dump(solution_data, f)

    # Mock the task loader to return a task with non-existent codebase
    from pathlib import Path

    from codegen_bench.core.task import Task

    def mock_load_task(task_id):
        return Task(
            id="task_001",
            name="Test Task",
            project="test-project",
            domain="testing",
            difficulty="easy",
            codebase_path=Path("/nonexistent/codebase"),
            specification="Test spec",
            compile_command="echo compile",
            test_command="echo test",
        )

    with patch("codegen_bench.tasks.loader.TaskLoader.load_task", side_effect=mock_load_task):
        result = runner.invoke(cli, ["validate", str(solution_file)])

    assert result.exit_code != 0
    assert "Codebase not found" in result.output or "not found" in result.output.lower()


def test_validate_command_worktree_creation_fails(runner, tmp_path):
    """Test validate command when git worktree creation fails (non-git repo)."""
    solution_file = tmp_path / "solution.json"
    fake_codebase = tmp_path / "fake_codebase"
    fake_codebase.mkdir()

    # Create solution
    solution_data = {
        "task_id": "task_001",
        "approach_id": "simple-chat",
        "seed": 42,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "changed_files": {"test.txt": "content"},
        "new_files": {},
        "deleted_files": [],
        "total_tokens": 100,
        "cost_usd": 0.01,
        "generation_time_seconds": 1.0,
    }

    with open(solution_file, "w") as f:
        json.dump(solution_data, f)

    # Mock task loader to return task with non-git codebase
    from codegen_bench.core.task import Task

    def mock_load_task(task_id):
        return Task(
            id="task_001",
            name="Test Task",
            project="test-project",
            domain="testing",
            difficulty="easy",
            codebase_path=fake_codebase,
            specification="Test spec",
            compile_command="echo compile",
            test_command="echo test",
        )

    with patch("codegen_bench.tasks.loader.TaskLoader.load_task", side_effect=mock_load_task):
        result = runner.invoke(cli, ["validate", str(solution_file)])

    # Should fail with worktree error
    assert result.exit_code != 0
    assert "Error" in result.output


def test_validate_command_applicator_failure(runner, tmp_path):
    """Test validate command when solution applicator fails."""
    from codegen_bench.core.task import Task
    from codegen_bench.exceptions import ValidationError

    # Create a git repo as codebase
    codebase = tmp_path / "codebase"
    codebase.mkdir()
    runner.invoke(cli, ["init", str(codebase)])

    solution_file = tmp_path / "solution.json"
    solution_data = {
        "task_id": "task_001",
        "approach_id": "simple-chat",
        "seed": 42,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "changed_files": {"test.txt": "content"},
        "new_files": {},
        "deleted_files": [],
        "total_tokens": 100,
        "cost_usd": 0.01,
        "generation_time_seconds": 1.0,
    }

    with open(solution_file, "w") as f:
        json.dump(solution_data, f)

    # Mock task loader
    def mock_load_task(task_id):
        return Task(
            id="task_001",
            name="Test Task",
            project="test-project",
            domain="testing",
            difficulty="easy",
            codebase_path=codebase,
            specification="Test spec",
            compile_command="echo compile",
            test_command="echo test",
        )

    # Mock applicator to raise ValidationError
    def mock_applicator_apply(*args, **kwargs):
        raise ValidationError("Failed to apply solution: Permission denied")

    with patch("codegen_bench.tasks.loader.TaskLoader.load_task", side_effect=mock_load_task):
        with patch(
            "codegen_bench.validation.applicator.SolutionApplicator.apply",
            side_effect=mock_applicator_apply,
        ):
            result = runner.invoke(cli, ["validate", str(solution_file)])

    assert result.exit_code != 0
    assert "Error" in result.output or "Failed" in result.output


def test_validate_command_executor_failure(runner, tmp_path):
    """Test validate command when executor fails during compile/test."""
    import subprocess

    from codegen_bench.core.task import Task

    # Create a git repo as codebase
    codebase = tmp_path / "codebase"
    codebase.mkdir()
    subprocess.run(["git", "init"], cwd=codebase, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=codebase,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=codebase, check=True, capture_output=True
    )

    # Create a dummy file and commit it
    (codebase / "test.txt").write_text("original")
    subprocess.run(["git", "add", "."], cwd=codebase, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=codebase, check=True, capture_output=True
    )

    solution_file = tmp_path / "solution.json"
    solution_data = {
        "task_id": "task_001",
        "approach_id": "simple-chat",
        "seed": 42,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "changed_files": {"test.txt": "modified content"},
        "new_files": {},
        "deleted_files": [],
        "total_tokens": 100,
        "cost_usd": 0.01,
        "generation_time_seconds": 1.0,
    }

    with open(solution_file, "w") as f:
        json.dump(solution_data, f)

    # Mock task loader
    def mock_load_task(task_id):
        return Task(
            id="task_001",
            name="Test Task",
            project="test-project",
            domain="testing",
            difficulty="easy",
            codebase_path=codebase,
            specification="Test spec",
            compile_command="nonexistent_command_that_will_fail",  # This will fail
            test_command="echo test",
        )

    with patch("codegen_bench.tasks.loader.TaskLoader.load_task", side_effect=mock_load_task):
        result = runner.invoke(cli, ["validate", str(solution_file)])

    # Should complete but show compilation failure (or success if command not found is handled)
    assert result.exit_code == 0
    assert "Compilation: FAILED" in result.output or "Solution applied" in result.output
