"""Tests for Task dataclass."""

from pathlib import Path

import pytest
import yaml

from codegen_bench.core.task import Task
from codegen_bench.exceptions import ValidationError


def test_task_creation(sample_task_dict: dict) -> None:
    """Test basic task creation."""
    task = Task(**sample_task_dict)
    assert task.id == "test_001"
    assert task.name == "Test Task"
    assert task.difficulty == "easy"


def test_task_validation_success(sample_task_dict: dict) -> None:
    """Test task validation with valid data."""
    task = Task(**sample_task_dict)
    task.validate()  # Should not raise


def test_task_validation_missing_codebase(sample_task_dict: dict, tmp_path: Path) -> None:
    """Test task validation fails with missing codebase."""
    sample_task_dict["codebase_path"] = tmp_path / "nonexistent"
    task = Task(**sample_task_dict)
    with pytest.raises(ValidationError, match="codebase path does not exist"):
        task.validate()


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
    with pytest.raises(ValidationError, match="Task ID is required"):
        task.validate()


def test_task_validate_invalid_compile_command(sample_task_dict: dict) -> None:
    """Test that invalid compile command fails validation."""
    sample_task_dict["compile_command"] = "gcc 'unterminated"
    task = Task(**sample_task_dict)
    with pytest.raises(ValidationError, match="invalid compile command"):
        task.validate()


def test_task_validate_invalid_test_command(sample_task_dict: dict) -> None:
    """Test that invalid test command fails validation."""
    sample_task_dict["test_command"] = "pytest 'unterminated"
    task = Task(**sample_task_dict)
    with pytest.raises(ValidationError, match="invalid test command"):
        task.validate()


def test_task_validate_missing_name(sample_task_dict: dict) -> None:
    """Test that missing name fails validation."""
    sample_task_dict["name"] = ""
    task = Task(**sample_task_dict)
    with pytest.raises(ValidationError, match="name is required"):
        task.validate()


def test_task_validate_missing_test_suite_path(sample_task_dict: dict, tmp_path: Path) -> None:
    """Test that non-existent test suite path fails validation."""
    sample_task_dict["test_suite_path"] = tmp_path / "nonexistent_tests"
    task = Task(**sample_task_dict)
    with pytest.raises(ValidationError, match="test suite path does not exist"):
        task.validate()


def test_task_validate_missing_reference_solution(sample_task_dict: dict, tmp_path: Path) -> None:
    """Test that non-existent reference solution path fails validation."""
    sample_task_dict["reference_solution_path"] = tmp_path / "nonexistent_reference"
    task = Task(**sample_task_dict)
    with pytest.raises(ValidationError, match="reference solution path does not exist"):
        task.validate()


def test_task_from_yaml_with_paths(tmp_path: Path, tmp_codebase: Path) -> None:
    """Test from_yaml properly converts path strings to Path objects."""
    test_suite = tmp_path / "tests"
    test_suite.mkdir()
    reference = tmp_path / "reference"
    reference.mkdir()

    yaml_data = {
        "id": "test_yaml",
        "name": "YAML Test",
        "project": "test",
        "domain": "testing",
        "difficulty": "medium",
        "codebase_path": str(tmp_codebase),
        "specification": "Test spec",
        "test_suite_path": str(test_suite),
        "reference_solution_path": str(reference),
    }

    yaml_file = tmp_path / "task_with_paths.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(yaml_data, f)

    task = Task.from_yaml(yaml_file)
    assert isinstance(task.codebase_path, Path)
    assert isinstance(task.test_suite_path, Path)
    assert isinstance(task.reference_solution_path, Path)
    assert task.codebase_path == tmp_codebase
    assert task.test_suite_path == test_suite
    assert task.reference_solution_path == reference


def test_task_from_yaml_empty_file(tmp_path: Path) -> None:
    """Test from_yaml with empty YAML file."""
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("")

    # Should raise ValueError for empty file
    with pytest.raises(ValueError, match="empty or contains only null"):
        Task.from_yaml(yaml_file)


def test_task_from_yaml_malformed(tmp_path: Path) -> None:
    """Test from_yaml with malformed YAML."""
    yaml_file = tmp_path / "malformed.yaml"
    yaml_file.write_text("id: test\n  bad indentation:\n  - item")

    # Should raise yaml.YAMLError
    with pytest.raises(yaml.YAMLError, match="Failed to parse YAML file"):
        Task.from_yaml(yaml_file)


def test_task_from_yaml_not_dict(tmp_path: Path) -> None:
    """Test from_yaml with YAML containing non-dict data."""
    yaml_file = tmp_path / "list.yaml"
    yaml_file.write_text("- item1\n- item2")

    # Should raise ValueError for non-dict data
    with pytest.raises(ValueError, match="must contain a mapping/dict"):
        Task.from_yaml(yaml_file)


def test_task_repr(sample_task_dict: dict) -> None:
    """Test Task __repr__ method."""
    task = Task(**sample_task_dict)
    repr_str = repr(task)
    assert "test_001" in repr_str
    assert "Test Task" in repr_str
    assert "test-project" in repr_str
    assert "easy" in repr_str
