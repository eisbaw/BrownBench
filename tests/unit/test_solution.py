"""Tests for Solution dataclass."""

from datetime import datetime

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
