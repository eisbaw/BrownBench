"""Tests for git worktree isolation."""

import subprocess

import pytest

from codegen_bench.exceptions import WorktreeError
from codegen_bench.validation.worktree import GitWorktreeStrategy


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


def test_worktree_init_valid_repo(git_repo):
    """Test initializing with valid git repository."""
    strategy = GitWorktreeStrategy(git_repo)
    assert strategy.repo_path == git_repo.resolve()


def test_worktree_init_invalid_repo(tmp_path):
    """Test initializing with non-git directory."""
    with pytest.raises(WorktreeError, match="Not a git repository"):
        GitWorktreeStrategy(tmp_path)


def test_is_git_repo(git_repo, tmp_path):
    """Test git repository detection."""
    strategy = GitWorktreeStrategy(git_repo)
    assert strategy._is_git_repo(git_repo) is True
    assert strategy._is_git_repo(tmp_path) is False


def test_create_worktree(git_repo):
    """Test creating a worktree."""
    strategy = GitWorktreeStrategy(git_repo)
    worktree_path = strategy.create_worktree()

    assert worktree_path.exists()
    assert worktree_path.is_dir()
    assert (worktree_path / "README.md").exists()

    # Clean up
    strategy.remove_worktree(worktree_path)


def test_remove_worktree(git_repo):
    """Test removing a worktree."""
    strategy = GitWorktreeStrategy(git_repo)
    worktree_path = strategy.create_worktree()

    assert worktree_path.exists()

    strategy.remove_worktree(worktree_path)

    # Worktree should be removed from git's tracking
    worktrees = strategy.list_worktrees()
    assert worktree_path not in worktrees


def test_list_worktrees(git_repo):
    """Test listing worktrees."""
    strategy = GitWorktreeStrategy(git_repo)

    # Initially just main worktree
    worktrees = strategy.list_worktrees()
    assert git_repo in worktrees

    # Create additional worktree
    worktree_path = strategy.create_worktree()
    worktrees = strategy.list_worktrees()
    assert len(worktrees) >= 2
    assert worktree_path in worktrees

    # Clean up
    strategy.remove_worktree(worktree_path)


def test_worktree_isolation(git_repo):
    """Test that worktree is isolated from main repo."""
    strategy = GitWorktreeStrategy(git_repo)
    worktree_path = strategy.create_worktree()

    # Modify file in worktree
    test_file = worktree_path / "README.md"
    test_file.write_text("# Modified in worktree\n")

    # Original repo should be unchanged
    original_file = git_repo / "README.md"
    assert "Test Repository" in original_file.read_text()
    assert "Modified in worktree" not in original_file.read_text()

    # Clean up
    strategy.remove_worktree(worktree_path)


def test_create_worktree_failure(tmp_path):
    """Test worktree creation failure handling."""
    # Create a non-git directory
    non_git = tmp_path / "non_git"
    non_git.mkdir()

    with pytest.raises(WorktreeError, match="Not a git repository"):
        GitWorktreeStrategy(non_git)


def test_remove_nonexistent_worktree(git_repo):
    """Test removing non-existent worktree raises error."""
    strategy = GitWorktreeStrategy(git_repo)
    fake_path = git_repo.parent / "nonexistent_worktree"

    with pytest.raises(WorktreeError, match="Failed to remove worktree"):
        strategy.remove_worktree(fake_path)


def test_worktree_context_manager_success(git_repo):
    """Test worktree context manager creates and cleans up successfully."""
    strategy = GitWorktreeStrategy(git_repo)

    with strategy.worktree() as worktree_path:
        # Worktree should exist during context
        assert worktree_path.exists()
        assert worktree_path.is_dir()
        assert (worktree_path / "README.md").exists()

        # Track path for verification after context
        tracked_path = worktree_path

    # Worktree should be cleaned up after context
    worktrees = strategy.list_worktrees()
    assert tracked_path not in worktrees


def test_worktree_context_manager_with_exception(git_repo):
    """Test worktree context manager cleans up even when exception is raised."""
    strategy = GitWorktreeStrategy(git_repo)
    tracked_path = None

    with pytest.raises(RuntimeError, match="Test exception"):
        with strategy.worktree() as worktree_path:
            tracked_path = worktree_path
            assert worktree_path.exists()
            # Raise exception to test cleanup
            raise RuntimeError("Test exception")

    # Worktree should still be cleaned up
    worktrees = strategy.list_worktrees()
    assert tracked_path not in worktrees


def test_worktree_context_manager_multiple(git_repo):
    """Test multiple context managers can be used sequentially."""
    strategy = GitWorktreeStrategy(git_repo)
    paths = []

    # Create and cleanup first worktree
    with strategy.worktree() as path1:
        assert path1.exists()
        paths.append(path1)

    # Create and cleanup second worktree
    with strategy.worktree() as path2:
        assert path2.exists()
        paths.append(path2)
        # Should be different paths
        assert path1 != path2

    # Both should be cleaned up
    worktrees = strategy.list_worktrees()
    for path in paths:
        assert path not in worktrees


def test_list_worktrees_error(git_repo, monkeypatch):
    """Test list_worktrees handles subprocess errors."""
    strategy = GitWorktreeStrategy(git_repo)

    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["git"], stderr="error")

    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(WorktreeError, match="Failed to list worktrees"):
        strategy.list_worktrees()


def test_create_worktree_timeout(git_repo, monkeypatch):
    """Test create_worktree handles timeout."""
    strategy = GitWorktreeStrategy(git_repo)

    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(["git"], 30)

    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(WorktreeError, match="Worktree creation timed out"):
        strategy.create_worktree()


def test_remove_worktree_timeout(git_repo, monkeypatch):
    """Test remove_worktree handles timeout."""
    strategy = GitWorktreeStrategy(git_repo)
    worktree_path = strategy.create_worktree()

    def mock_run(*args, **kwargs):
        # Only timeout on remove, not on create
        if "remove" in args[0]:
            raise subprocess.TimeoutExpired(["git"], 30)
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(WorktreeError, match="Worktree removal timed out"):
        strategy.remove_worktree(worktree_path)


def test_worktree_context_manager_fallback_cleanup(git_repo, monkeypatch):
    """Test context manager fallback to manual cleanup when git remove fails."""
    strategy = GitWorktreeStrategy(git_repo)
    tracked_path = None

    # Mock remove_worktree to fail
    remove_called = [False]

    def mock_remove(path):
        remove_called[0] = True
        from codegen_bench.exceptions import WorktreeError

        raise WorktreeError("Git worktree remove failed")

    with strategy.worktree() as worktree_path:
        tracked_path = worktree_path
        assert worktree_path.exists()
        # Patch remove_worktree to fail
        monkeypatch.setattr(strategy, "remove_worktree", mock_remove)

    # Should have tried git remove
    assert remove_called[0]
    # Path should still be cleaned up (via shutil.rmtree fallback)
    assert not tracked_path.exists()
