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
            WorktreeError: If path is not a git repository, git not found, or timeout
        """
        self.repo_path = Path(repo_path).resolve()
        self._is_git_repo(self.repo_path)  # Raises WorktreeError with specific context

    def _is_git_repo(self, path: Path) -> None:
        """Check if path is a git repository.

        Args:
            path: Path to check

        Raises:
            WorktreeError: With specific error context (git not found, timeout, or not a repo)
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                capture_output=True,
                check=True,
                timeout=5,
            )
            # Success - path is a valid git repo
        except FileNotFoundError as e:
            raise WorktreeError("git command not found in PATH. Is git installed?") from e
        except subprocess.TimeoutExpired as e:
            raise WorktreeError(f"git command timed out after 5s while checking {path}") from e
        except subprocess.CalledProcessError as e:
            # Non-zero exit code means not a git repo
            raise WorktreeError(f"Not a git repository: {path}") from e

    def _cleanup_temp_dir(self, temp_dir: Path) -> None:
        """Clean up temporary directory, ignoring errors.

        Args:
            temp_dir: Path to temporary directory to remove
        """
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    def create_worktree(self, ref: str | None = None) -> Path:
        """Create a new git worktree.

        Args:
            ref: Git ref (branch/tag/commit) to checkout. If None, checks out current HEAD.
                 If a branch name that doesn't exist, creates a new branch from current HEAD.
                 Examples: "main", "v1.0.0", "abc123", None

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
            if ref:
                # Note: -b creates a new branch from current HEAD
                # If ref is an existing branch/tag/commit, don't use -b
                cmd.extend(["-b", ref, ref])

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self._cleanup_temp_dir(temp_dir)
                raise WorktreeError(f"Failed to create worktree at '{temp_dir}': {result.stderr}")

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
                raise WorktreeError(
                    f"Failed to remove worktree at '{worktree_path}': {result.stderr}"
                )

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
    def worktree(self, ref: str | None = None) -> Iterator[Path]:
        """Context manager for creating and automatically cleaning up a worktree.

        Args:
            ref: Git ref (branch/tag/commit) to checkout (default: current HEAD)

        Yields:
            Path to created worktree

        Example:
            with strategy.worktree() as worktree_path:
                # Use worktree_path
                # Automatic cleanup on exit
        """
        worktree_path = None
        original_exception = None
        try:
            worktree_path = self.create_worktree(ref)
            yield worktree_path
        except Exception as e:
            # Preserve original exception to re-raise after cleanup
            original_exception = e
            raise
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
                        # Both git and manual cleanup failed
                        # Only raise cleanup error if there was no original exception
                        if original_exception is None:
                            raise WorktreeError(
                                f"Failed to cleanup worktree at '{worktree_path}'. "
                                f"Git remove failed: {e}. Manual cleanup failed: {cleanup_error}"
                            ) from cleanup_error
                        else:
                            # Log but don't raise - original exception takes precedence
                            logger.error(
                                "worktree_cleanup_failed_during_exception_handling",
                                worktree_path=str(worktree_path),
                                original_error=str(original_exception),
                                cleanup_error=str(cleanup_error),
                            )
