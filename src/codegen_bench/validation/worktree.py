"""Git worktree-based isolation for solution validation."""

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import structlog

from codegen_bench.exceptions import WorktreeError

logger = structlog.get_logger(__name__)


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
            WorktreeError: If path is not a git repository
        """
        self.repo_path = Path(repo_path).resolve()
        if not self._is_git_repo(self.repo_path):
            raise WorktreeError(f"Not a git repository: {self.repo_path}")

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

    def _cleanup_temp_dir(self, temp_dir: Path) -> None:
        """Clean up temporary directory, ignoring errors.

        Args:
            temp_dir: Path to temporary directory to remove
        """
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    def create_worktree(self, branch: str | None = None) -> Path:
        """Create a new git worktree.

        Args:
            branch: Branch to checkout (default: current HEAD)

        Returns:
            Path to created worktree

        Raises:
            WorktreeError: If worktree creation fails
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
                self._cleanup_temp_dir(temp_dir)
                raise WorktreeError(
                    f"Failed to create worktree at {temp_dir}: {result.stderr}"
                )

            return temp_dir

        except subprocess.TimeoutExpired as e:
            self._cleanup_temp_dir(temp_dir)
            raise WorktreeError(f"Worktree creation timed out after 30s: {e}") from e
        except (OSError, subprocess.CalledProcessError) as e:
            self._cleanup_temp_dir(temp_dir)
            raise WorktreeError(f"Failed to create worktree due to system error: {e}") from e

    def remove_worktree(self, worktree_path: Path) -> None:
        """Remove a git worktree.

        Args:
            worktree_path: Path to worktree to remove

        Raises:
            WorktreeError: If worktree removal fails
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
                raise WorktreeError(f"Failed to remove worktree at {worktree_path}: {result.stderr}")

        except subprocess.TimeoutExpired as e:
            raise WorktreeError(f"Worktree removal timed out after 30s: {e}") from e
        except (OSError, subprocess.CalledProcessError) as e:
            raise WorktreeError(f"Failed to remove worktree due to system error: {e}") from e

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
            raise WorktreeError(f"Failed to list worktrees: {e.stderr}") from e

    @contextmanager
    def worktree(self, branch: str | None = None) -> Iterator[Path]:
        """Context manager for creating and automatically cleaning up a worktree.

        Args:
            branch: Branch to checkout (default: current HEAD)

        Yields:
            Path to created worktree

        Example:
            with strategy.worktree() as worktree_path:
                # Use worktree_path
                # Automatic cleanup on exit
        """
        worktree_path = None
        try:
            worktree_path = self.create_worktree(branch)
            yield worktree_path
        finally:
            if worktree_path and worktree_path.exists():
                try:
                    self.remove_worktree(worktree_path)
                except WorktreeError as e:
                    # If git worktree remove fails, try manual cleanup
                    logger.warning(
                        "worktree_remove_failed_fallback_to_manual",
                        worktree_path=str(worktree_path),
                        error=str(e),
                    )
                    try:
                        shutil.rmtree(worktree_path)
                    except OSError as cleanup_error:
                        logger.error(
                            "worktree_manual_cleanup_failed",
                            worktree_path=str(worktree_path),
                            error=str(cleanup_error),
                        )
