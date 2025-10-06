"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_codebase(tmp_path: Path) -> Path:
    """Create a temporary codebase directory."""
    codebase = tmp_path / "codebase"
    codebase.mkdir()
    (codebase / "main.py").write_text("print('hello')")
    return codebase


@pytest.fixture
def sample_task_dict(tmp_codebase: Path) -> dict:
    """Sample task data."""
    return {
        "id": "test_001",
        "name": "Test Task",
        "project": "test-project",
        "domain": "testing",
        "difficulty": "easy",
        "codebase_path": tmp_codebase,
        "specification": "Add a hello world function",
        "constraints": ["Must be backwards compatible"],
        "key_files": ["main.py"],
    }


@pytest.fixture
def sample_task(sample_task_dict: dict):
    """Sample Task instance."""
    from codegen_bench.core.task import Task

    return Task(**sample_task_dict)


@pytest.fixture
def sample_solution():
    """Sample Solution instance."""
    from datetime import UTC, datetime

    from codegen_bench.core.solution import Solution

    return Solution(
        approach_id="test-dut",
        task_id="test_001",
        seed=42,
        timestamp=datetime.now(UTC),
        changed_files={"main.py": "def hello(): print('Hello')"},
        total_tokens=100,
        cost_usd=0.01,
    )
