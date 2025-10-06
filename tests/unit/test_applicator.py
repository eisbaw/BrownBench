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


def test_apply_diff_success(workspace):
    """Test applying unified diff successfully."""
    import subprocess

    # Initialize git repo in workspace
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )

    # Create a file and commit it
    test_file = workspace / "test.txt"
    test_file.write_text("line 1\nline 2\nline 3\n")
    subprocess.run(["git", "add", "test.txt"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )

    # Create a diff
    diff_content = """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,4 @@
 line 1
+new line
 line 2
 line 3
"""

    applicator = SolutionApplicator(workspace)
    applicator.apply_diff(diff_content)

    # Check the file was modified
    assert "new line" in test_file.read_text()


def test_apply_diff_failure(workspace):
    """Test applying invalid diff raises error."""
    import subprocess

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)

    # Invalid diff
    diff_content = "invalid diff content"

    applicator = SolutionApplicator(workspace)
    with pytest.raises(RuntimeError, match="Failed to apply diff"):
        applicator.apply_diff(diff_content)
