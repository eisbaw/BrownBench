"""Tests for Task dataclass."""

from pathlib import Path

import yaml

from codegen_bench.core.task import Task


def test_task_creation(sample_task_dict: dict) -> None:
    """Test basic task creation."""
    task = Task(**sample_task_dict)
    assert task.id == "test_001"
    assert task.name == "Test Task"
    assert task.difficulty == "easy"


def test_task_validation_success(sample_task_dict: dict) -> None:
    """Test task validation with valid data."""
    task = Task(**sample_task_dict)
    assert task.validate() is True


def test_task_validation_missing_codebase(sample_task_dict: dict, tmp_path: Path) -> None:
    """Test task validation fails with missing codebase."""
    sample_task_dict["codebase_path"] = tmp_path / "nonexistent"
    task = Task(**sample_task_dict)
    assert task.validate() is False


def test_task_to_dict(sample_task_dict: dict) -> None:
    """Test task serialization."""
    task = Task(**sample_task_dict)
    data = task.to_dict()
    assert data["id"] == "test_001"
    assert data["name"] == "Test Task"
    assert isinstance(data["codebase_path"], str)


def test_task_from_yaml(sample_task_dict: dict, tmp_path: Path) -> None:
    """Test loading task from YAML."""
    yaml_file = tmp_path / "task.yaml"

    # Convert paths to strings for YAML
    yaml_data = sample_task_dict.copy()
    yaml_data["codebase_path"] = str(yaml_data["codebase_path"])

    with open(yaml_file, "w") as f:
        yaml.dump(yaml_data, f)

    task = Task.from_yaml(yaml_file)
    assert task.id == "test_001"
    assert task.name == "Test Task"
    assert isinstance(task.codebase_path, Path)


def test_task_empty_id_invalid() -> None:
    """Test that empty ID makes task invalid."""
    task = Task(
        id="",
        name="Test",
        project="test",
        domain="test",
        difficulty="easy",
        codebase_path=Path("/nonexistent"),
        specification="test",
    )
    assert task.validate() is False


def test_task_validate_invalid_compile_command(sample_task_dict: dict) -> None:
    """Test that invalid compile command fails validation."""
    sample_task_dict["compile_command"] = "gcc 'unterminated"
    task = Task(**sample_task_dict)
    assert task.validate() is False


def test_task_validate_invalid_test_command(sample_task_dict: dict) -> None:
    """Test that invalid test command fails validation."""
    sample_task_dict["test_command"] = "pytest 'unterminated"
    task = Task(**sample_task_dict)
    assert task.validate() is False
