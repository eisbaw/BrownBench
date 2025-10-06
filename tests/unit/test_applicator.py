"""Tests for solution applicator."""

from datetime import UTC, datetime

import pytest

from codegen_bench.core.solution import Solution
from codegen_bench.validation.applicator import SolutionApplicator


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def sample_solution():
    """Create a sample solution."""
    return Solution(
        approach_id="test-dut",
        task_id="test_task",
        seed=42,
        timestamp=datetime.now(UTC),
        changed_files={
            "src/main.c": "#include <stdio.h>\n\nint main() {\n    return 0;\n}\n",
            "src/helper.c": "void helper() {}\n",
        },
        new_files={"src/util.c": "void util() {}\n"},
        deleted_files=["src/old.c"],
    )


def test_applicator_init(workspace):
    """Test applicator initialization."""
    applicator = SolutionApplicator(workspace)
    assert applicator.workspace == workspace.resolve()


def test_applicator_init_nonexistent(tmp_path):
    """Test applicator initialization with nonexistent workspace."""
    nonexistent = tmp_path / "nonexistent"
    with pytest.raises(ValueError, match="Workspace does not exist"):
        SolutionApplicator(nonexistent)


def test_apply_changed_files(workspace, sample_solution):
    """Test applying changed files."""
    applicator = SolutionApplicator(workspace)
    applicator.apply(sample_solution)

    # Check changed files were written
    main_file = workspace / "src/main.c"
    assert main_file.exists()
    assert "#include <stdio.h>" in main_file.read_text()

    helper_file = workspace / "src/helper.c"
    assert helper_file.exists()
    assert "void helper()" in helper_file.read_text()


def test_apply_new_files(workspace, sample_solution):
    """Test applying new files."""
    applicator = SolutionApplicator(workspace)
    applicator.apply(sample_solution)

    util_file = workspace / "src/util.c"
    assert util_file.exists()
    assert "void util()" in util_file.read_text()


def test_apply_deleted_files(workspace, sample_solution):
    """Test deleting files."""
    # Create file to be deleted
    old_file = workspace / "src/old.c"
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.write_text("old content")

    assert old_file.exists()

    applicator = SolutionApplicator(workspace)
    applicator.apply(sample_solution)

    assert not old_file.exists()


def test_apply_creates_directories(workspace):
    """Test that parent directories are created."""
    solution = Solution(
        approach_id="test",
        task_id="test",
        seed=42,
        timestamp=datetime.now(UTC),
        changed_files={"deep/nested/dir/file.c": "content"},
    )

    applicator = SolutionApplicator(workspace)
    applicator.apply(solution)

    file_path = workspace / "deep/nested/dir/file.c"
    assert file_path.exists()
    assert file_path.read_text() == "content"


def test_write_file(workspace):
    """Test writing individual file."""
    applicator = SolutionApplicator(workspace)
    applicator._write_file("test.txt", "hello world")

    test_file = workspace / "test.txt"
    assert test_file.exists()
    assert test_file.read_text() == "hello world"


def test_delete_file(workspace):
    """Test deleting individual file."""
    test_file = workspace / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()

    applicator = SolutionApplicator(workspace)
    applicator._delete_file("test.txt")

    assert not test_file.exists()


def test_delete_nonexistent_file(workspace):
    """Test deleting nonexistent file doesn't raise error."""
    applicator = SolutionApplicator(workspace)
    # Should not raise
    applicator._delete_file("nonexistent.txt")


def test_apply_empty_solution(workspace):
    """Test applying solution with no changes."""
    solution = Solution(
        approach_id="test",
        task_id="test",
        seed=42,
        timestamp=datetime.now(UTC),
    )

    applicator = SolutionApplicator(workspace)
    # Should not raise
    applicator.apply(solution)
