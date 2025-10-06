"""Tests for TaskLoader."""

from pathlib import Path

import pytest
import yaml

from codegen_bench.tasks.loader import TaskLoader


@pytest.fixture
def task_dir(tmp_path: Path) -> Path:
    """Create a directory with test tasks."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    # Create a codebase
    codebase = tmp_path / "codebase"
    codebase.mkdir()
    (codebase / "main.py").write_text("print('hello')")

    # Create core subdirectory
    core_dir = tasks_dir / "core"
    core_dir.mkdir()

    # Create task 1
    task1_data = {
        "id": "task_001",
        "name": "Task 1",
        "project": "test",
        "domain": "testing",
        "difficulty": "easy",
        "codebase_path": str(codebase),
        "specification": "Test spec",
        "key_files": ["main.py"],
    }
    with open(core_dir / "task_001.yaml", "w") as f:
        yaml.dump(task1_data, f)

    # Create task 2
    task2_data = task1_data.copy()
    task2_data["id"] = "task_002"
    task2_data["name"] = "Task 2"
    with open(core_dir / "task_002.yaml", "w") as f:
        yaml.dump(task2_data, f)

    return tasks_dir


def test_load_single_task(task_dir: Path) -> None:
    """Test loading a single task by ID."""
    loader = TaskLoader(task_dir)
    task = loader.load_task("task_001")
    assert task.id == "task_001"
    assert task.name == "Task 1"


def test_load_nonexistent_task(task_dir: Path) -> None:
    """Test loading a nonexistent task raises FileNotFoundError."""
    loader = TaskLoader(task_dir)
    with pytest.raises(FileNotFoundError):
        loader.load_task("nonexistent")


def test_load_task_set_core(task_dir: Path) -> None:
    """Test loading core task set."""
    loader = TaskLoader(task_dir)
    tasks = loader.load_task_set("core")
    assert len(tasks) == 2
    assert tasks[0].id == "task_001"
    assert tasks[1].id == "task_002"


def test_load_task_set_all(task_dir: Path) -> None:
    """Test loading all tasks."""
    loader = TaskLoader(task_dir)
    tasks = loader.load_task_set("all")
    assert len(tasks) == 2


def test_load_task_set_custom_pattern(task_dir: Path) -> None:
    """Test loading tasks with custom pattern."""
    loader = TaskLoader(task_dir)
    tasks = loader.load_task_set("**/task_001.yaml")
    assert len(tasks) == 1
    assert tasks[0].id == "task_001"


def test_load_task_set_no_matches(task_dir: Path) -> None:
    """Test loading with no matching pattern raises error."""
    loader = TaskLoader(task_dir)
    with pytest.raises(FileNotFoundError):
        loader.load_task_set("nonexistent/*.yaml")


def test_list_available_tasks(task_dir: Path) -> None:
    """Test listing available tasks."""
    loader = TaskLoader(task_dir)
    tasks = loader.list_available_tasks()
    assert tasks == ["task_001", "task_002"]


def test_load_invalid_task_fails_validation(tmp_path: Path) -> None:
    """Test that invalid tasks fail validation."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    # Create task with invalid codebase path
    invalid_task = {
        "id": "invalid",
        "name": "Invalid Task",
        "project": "test",
        "domain": "testing",
        "difficulty": "easy",
        "codebase_path": "/nonexistent",
        "specification": "Test spec",
    }
    with open(tasks_dir / "invalid.yaml", "w") as f:
        yaml.dump(invalid_task, f)

    loader = TaskLoader(tasks_dir)
    with pytest.raises(ValueError, match="failed validation"):
        loader.load_task("invalid")
