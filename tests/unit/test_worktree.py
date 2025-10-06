"""Tests for git worktree isolation."""

import subprocess

import pytest

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
    with pytest.raises(ValueError, match="Not a git repository"):
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
