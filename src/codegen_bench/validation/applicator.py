"""Apply solution code changes to a workspace."""

import subprocess
from pathlib import Path

from codegen_bench.core.solution import Solution
from codegen_bench.exceptions import ValidationError


class SolutionApplicator:
    """Apply code changes from a solution to a workspace."""

    def __init__(self, workspace: Path):
        """Initialize solution applicator.

        Args:
            workspace: Path to workspace where changes will be applied
        """
        self.workspace = Path(workspace).resolve()
        if not self.workspace.exists():
            raise ValidationError(f"Workspace does not exist: {self.workspace}")

    def apply(self, solution: Solution) -> None:
        """Apply solution changes to workspace idempotently.

        Merges changed_files and new_files since both operations are identical
        (write content to file). This makes the operation idempotent: applying
        solution A, then B, then A again produces the same result as A alone.

        Args:
            solution: Solution with code changes

        Raises:
            RuntimeError: If applying changes fails
        """
        # Merge changed and new files - both are just write operations
        # This ensures idempotency: A→B→A produces same result as A
        all_writes = {**solution.changed_files, **solution.new_files}

        for path, content in all_writes.items():
            self._write_file(path, content)

        # Delete removed files
        for path in solution.deleted_files:
            self._delete_file(path)

    def _write_file(self, rel_path: str, content: str) -> None:
        """Write content to file in workspace.

        Args:
            rel_path: Relative path within workspace
            content: File content to write

        Raises:
            RuntimeError: If writing file fails
        """
        file_path = self.workspace / rel_path

        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(file_path, "w") as f:
                f.write(content)

        except (OSError, PermissionError) as e:
            # OSError: general file system errors (includes IOError in Python 3.3+)
            # PermissionError: insufficient permissions
            raise ValidationError(f"Failed to write file {rel_path}: {e}") from e

    def _delete_file(self, rel_path: str) -> None:
        """Delete file from workspace.

        Args:
            rel_path: Relative path within workspace

        Raises:
            RuntimeError: If deleting file fails
        """
        file_path = self.workspace / rel_path

        try:
            if file_path.exists():
                file_path.unlink()
        except (OSError, PermissionError) as e:
            # OSError: file system errors
            # PermissionError: insufficient permissions
            raise ValidationError(f"Failed to delete file {rel_path}: {e}") from e

    def apply_diff(self, diff_content: str) -> None:
        """Apply a unified diff patch to workspace.

        Args:
            diff_content: Unified diff content

        Raises:
            RuntimeError: If applying patch fails
        """
        try:
            result = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", "-"],
                input=diff_content,
                text=True,
                cwd=self.workspace,
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise ValidationError(f"Failed to apply diff: {result.stderr}")

        except subprocess.TimeoutExpired as e:
            raise ValidationError("Diff application timed out") from e
        except (OSError, subprocess.CalledProcessError) as e:
            # OSError: git not found or execution failed
            # CalledProcessError: git returned non-zero
            raise ValidationError(f"Failed to apply diff: {e}") from e
