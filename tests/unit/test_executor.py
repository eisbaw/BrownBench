"""Tests for validation executor."""

from pathlib import Path

import pytest

from codegen_bench.validation.executor import ValidationExecutor, ValidationResult


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_executor_init(workspace):
    """Test executor initialization."""
    executor = ValidationExecutor(workspace)
    assert executor.workspace == workspace.resolve()


def test_executor_init_nonexistent(tmp_path):
    """Test executor initialization with nonexistent workspace."""
    nonexistent = tmp_path / "nonexistent"
    with pytest.raises(ValueError, match="Workspace does not exist"):
        ValidationExecutor(nonexistent)


def test_run_compile_success(workspace):
    """Test successful compile command."""
    executor = ValidationExecutor(workspace)
    result = executor.run_compile("echo 'compile successful'")

    assert result.success is True
    assert result.returncode == 0
    assert "compile successful" in result.output
    assert result.timed_out is False


def test_run_compile_failure(workspace):
    """Test failed compile command."""
    executor = ValidationExecutor(workspace)
    result = executor.run_compile("false")

    assert result.success is False
    assert result.returncode != 0
    assert result.timed_out is False


def test_run_tests_success(workspace):
    """Test successful test command."""
    executor = ValidationExecutor(workspace)
    result = executor.run_tests("echo 'tests passed'")

    assert result.success is True
    assert "tests passed" in result.output


def test_run_command_timeout(workspace):
    """Test command timeout."""
    executor = ValidationExecutor(workspace)
    result = executor._run_command("sleep 10", timeout=1)

    assert result.success is False
    assert result.timed_out is True
    assert result.returncode == -1


def test_run_command_in_workspace(workspace):
    """Test command runs in correct workspace."""
    # Create a test file
    test_file = workspace / "test.txt"
    test_file.write_text("hello")

    executor = ValidationExecutor(workspace)
    result = executor._run_command("cat test.txt", timeout=30)

    assert result.success is True
    assert "hello" in result.output


def test_parse_pytest_output():
    """Test parsing pytest output."""
    executor = ValidationExecutor(Path("/tmp"))
    output = """
============================= test session starts ==============================
collected 10 items

tests/test_example.py ..........                                         [100%]

============================== 10 passed in 0.5s ===============================
"""
    metrics = executor.parse_test_output(output, "pytest")

    assert metrics["framework"] == "pytest"
    assert metrics["passed"] == 10
    assert metrics["failed"] == 0


def test_parse_pytest_output_with_failures():
    """Test parsing pytest output with failures."""
    executor = ValidationExecutor(Path("/tmp"))
    output = """
============================== test session starts ==============================
collected 12 items

tests/test_example.py .....F..F...                                       [100%]

========================= 10 passed, 2 failed in 1.2s ==========================
"""
    metrics = executor.parse_test_output(output, "pytest")

    assert metrics["passed"] == 10
    assert metrics["failed"] == 2


def test_parse_pytest_output_with_skips():
    """Test parsing pytest output with skipped tests."""
    executor = ValidationExecutor(Path("/tmp"))
    output = """
============================== test session starts ==============================
collected 15 items

tests/test_example.py ..........sss..                                    [100%]

===================== 12 passed, 3 skipped in 0.8s =====================
"""
    metrics = executor.parse_test_output(output, "pytest")

    assert metrics["passed"] == 12
    assert metrics["skipped"] == 3


def test_parse_unittest_output():
    """Test parsing unittest output."""
    executor = ValidationExecutor(Path("/tmp"))
    output = """
..........
----------------------------------------------------------------------
Ran 10 tests in 0.5s

OK
"""
    metrics = executor.parse_test_output(output, "unittest")

    assert metrics["framework"] == "unittest"
    assert metrics["passed"] == 10
    assert metrics["failed"] == 0


def test_parse_unittest_output_with_failures():
    """Test parsing unittest output with failures."""
    executor = ValidationExecutor(Path("/tmp"))
    output = """
.....F..E..
----------------------------------------------------------------------
Ran 11 tests in 1.2s

FAILED (failures=1, errors=1)
"""
    metrics = executor.parse_test_output(output, "unittest")

    assert metrics["passed"] == 9
    assert metrics["failed"] == 1
    assert metrics["errors"] == 1


def test_validation_result_creation():
    """Test ValidationResult dataclass."""
    result = ValidationResult(
        success=True,
        output="output text",
        error="error text",
        returncode=0,
        timed_out=False,
    )

    assert result.success is True
    assert result.output == "output text"
    assert result.error == "error text"
    assert result.returncode == 0
    assert result.timed_out is False
