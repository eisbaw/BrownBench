"""Tests for Solution dataclass."""

from datetime import datetime

import pytest

from codegen_bench.core.solution import Solution


def test_solution_creation() -> None:
    """Test basic solution creation."""
    solution = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
    )
    assert solution.approach_id == "test-dut"
    assert solution.task_id == "test_001"
    assert solution.seed == 42
    assert isinstance(solution.timestamp, datetime)


def test_solution_with_metrics() -> None:
    """Test solution with metrics."""
    solution = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
        total_tokens=1000,
        prompt_tokens=200,
        completion_tokens=800,
        api_calls=1,
        cost_usd=0.05,
    )
    assert solution.total_tokens == 1000
    assert solution.cost_usd == 0.05


def test_solution_to_dict() -> None:
    """Test solution serialization."""
    solution = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
        changed_files={"main.py": "print('hello')"},
    )
    data = solution.to_dict()
    assert data["approach_id"] == "test-dut"
    assert data["changed_files"] == {"main.py": "print('hello')"}
    assert isinstance(data["timestamp"], str)


def test_solution_from_dict() -> None:
    """Test solution deserialization."""
    data = {
        "approach_id": "test-dut",
        "task_id": "test_001",
        "seed": 42,
        "timestamp": "2024-01-01T12:00:00",
        "changed_files": {},
        "new_files": {},
        "deleted_files": [],
        "tests": None,
        "documentation": None,
        "generation_time_seconds": 0.0,
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "api_calls": 0,
        "cost_usd": 0.0,
        "reasoning_trace": None,
        "iterations": 1,
        "compiles": None,
        "tests_pass": None,
        "test_output": None,
    }
    solution = Solution.from_dict(data)
    assert solution.approach_id == "test-dut"
    assert isinstance(solution.timestamp, datetime)


def test_solution_roundtrip() -> None:
    """Test serialization roundtrip."""
    original = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
        changed_files={"main.py": "code"},
    )
    data = original.to_dict()
    restored = Solution.from_dict(data)
    assert restored.approach_id == original.approach_id
    assert restored.task_id == original.task_id
    assert restored.seed == original.seed


def test_solution_from_dict_missing_required_field() -> None:
    """Test from_dict raises ValueError when required field is missing."""
    # Missing approach_id
    data = {
        "task_id": "test_001",
        "seed": 42,
    }
    with pytest.raises(ValueError, match="Missing required fields"):
        Solution.from_dict(data)

    # Missing task_id
    data = {
        "approach_id": "test-dut",
        "seed": 42,
    }
    with pytest.raises(ValueError, match="Missing required fields"):
        Solution.from_dict(data)

    # Missing seed
    data = {
        "approach_id": "test-dut",
        "task_id": "test_001",
    }
    with pytest.raises(ValueError, match="Missing required fields"):
        Solution.from_dict(data)


def test_solution_repr_unvalidated() -> None:
    """Test __repr__ for unvalidated solution."""
    solution = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
        changed_files={"main.py": "code"},
        new_files={"test.py": "test code"},
    )
    repr_str = repr(solution)
    assert "test-dut" in repr_str
    assert "test_001" in repr_str
    assert "seed=42" in repr_str
    assert "files=2" in repr_str
    assert "unvalidated" in repr_str


def test_solution_repr_with_validation_results() -> None:
    """Test __repr__ with validation results."""
    solution = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
        changed_files={"main.py": "code"},
        compiles=True,
        tests_pass=False,
    )
    repr_str = repr(solution)
    assert "compiles=True" in repr_str
    assert "tests_pass=False" in repr_str
    assert "unvalidated" not in repr_str


def test_solution_repr_partial_validation() -> None:
    """Test __repr__ with partial validation (only compiles set)."""
    solution = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
        compiles=False,
    )
    repr_str = repr(solution)
    assert "compiles=False" in repr_str
    # tests_pass is None, so shouldn't appear
    assert "tests_pass" not in repr_str


def test_solution_repr_no_files() -> None:
    """Test __repr__ with no files changed."""
    solution = Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
    )
    repr_str = repr(solution)
    assert "files=0" in repr_str
