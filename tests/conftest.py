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
