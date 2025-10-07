"""Git worktree-based isolation for solution validation."""

import subprocess
import tempfile
from pathlib import Path


class GitWorktreeStrategy:
    """Create isolated git worktrees for testing solutions.

    This strategy creates a git worktree for each solution validation,
    ensuring that the original repository is not modified.
    """

    def __init__(self, repo_path: Path):
        """Initialize worktree strategy.

        Args:
            repo_path: Path to git repository

        Raises:
            ValueError: If path is not a git repository
        """
        self.repo_path = Path(repo_path).resolve()
        if not self._is_git_repo(self.repo_path):
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is a git repository.

        Args:
            path: Path to check

        Returns:
            True if path is a git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                capture_output=True,
                check=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def create_worktree(self, branch: str | None = None) -> Path:
        """Create a new git worktree.

        Args:
            branch: Branch to checkout (default: current HEAD)

        Returns:
            Path to created worktree

        Raises:
            RuntimeError: If worktree creation fails
        """
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="brownbench_worktree_"))

        try:
            # Create worktree
            cmd = ["git", "worktree", "add", str(temp_dir)]
            if branch:
                cmd.extend(["-b", branch, branch])

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                temp_dir.rmdir()
                raise RuntimeError(f"Failed to create worktree: {result.stderr}")

            return temp_dir

        except Exception as e:
            # Clean up temp directory on failure
            if temp_dir.exists():
                temp_dir.rmdir()
            raise RuntimeError(f"Failed to create worktree: {e}") from e

    def remove_worktree(self, worktree_path: Path) -> None:
        """Remove a git worktree.

        Args:
            worktree_path: Path to worktree to remove

        Raises:
            RuntimeError: If worktree removal fails
        """
        worktree_path = Path(worktree_path).resolve()

        try:
            # Remove worktree
            result = subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to remove worktree: {result.stderr}")

        except Exception as e:
            raise RuntimeError(f"Failed to remove worktree: {e}") from e

    def list_worktrees(self) -> list[Path]:
        """List all worktrees for this repository.

        Returns:
            List of worktree paths
        """
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            worktrees = []
            for line in result.stdout.splitlines():
                if line.startswith("worktree "):
                    worktree_path = line[len("worktree ") :].strip()
                    worktrees.append(Path(worktree_path))

            return worktrees

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to list worktrees: {e.stderr}") from e
