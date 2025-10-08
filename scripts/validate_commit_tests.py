#!/usr/bin/env python3
"""Validate that a commit has passing tests before and after the change.

This script checks out a commit and its parent, attempts to build and run tests,
and reports whether both versions pass tests. This is crucial for creating
benchmark tasks where we need a known-good baseline.
"""

import argparse
import contextlib
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of running tests on a commit."""

    commit_sha: str
    build_success: bool
    test_success: bool
    build_output: str
    test_output: str
    error_message: str | None = None


class CommitValidator:
    """Validates commits have passing tests."""

    def __init__(self, repo_path: Path, build_cmd: str | None, test_cmd: str | None):
        """Initialize validator.

        Args:
            repo_path: Path to git repository
            build_cmd: Command to build (e.g., "make" or "cmake . && make")
            test_cmd: Command to run tests (e.g., "make test" or "pytest")
        """
        self.repo_path = repo_path
        self.build_cmd = build_cmd
        self.test_cmd = test_cmd

    def get_current_ref(self) -> str | None:
        """Get the current git ref (branch or commit)."""
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()

        # If not on a branch, get the commit SHA
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    @contextlib.contextmanager
    def safe_checkout(self, sha: str):
        """Context manager for safe checkout with automatic restore.

        Args:
            sha: Commit SHA to checkout

        Yields:
            None
        """
        original_ref = self.get_current_ref()
        logger.debug(f"Saving current ref: {original_ref}")

        try:
            # Checkout target commit
            if not self.checkout_commit(sha):
                raise RuntimeError(f"Failed to checkout commit {sha}")
            yield
        finally:
            # Restore original ref
            if original_ref:
                logger.debug(f"Restoring original ref: {original_ref}")
                subprocess.run(
                    ["git", "-C", str(self.repo_path), "checkout", original_ref],
                    capture_output=True,
                    check=False,  # Don't fail if cleanup fails
                )

    def run_command(self, cmd: str, cwd: Path, timeout: int = 300) -> tuple[bool, str]:
        """Run a shell command.

        Args:
            cmd: Command to run
            cwd: Working directory
            timeout: Timeout in seconds

        Returns:
            (success, output) tuple
        """
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (result.returncode == 0, result.stdout + "\n" + result.stderr)
        except subprocess.TimeoutExpired:
            return (False, f"Command timed out after {timeout}s")
        except Exception as e:
            return (False, f"Command failed: {e}")

    def checkout_commit(self, sha: str) -> bool:
        """Checkout a specific commit.

        Args:
            sha: Commit SHA to checkout

        Returns:
            True if successful
        """
        success, _ = self.run_command(
            f"git -C {self.repo_path} checkout {sha}",
            self.repo_path.parent,
        )
        return success

    def test_commit(self, sha: str) -> TestResult:
        """Test a specific commit.

        Args:
            sha: Commit SHA to test

        Returns:
            TestResult with build and test outcomes
        """
        # Checkout commit
        if not self.checkout_commit(sha):
            return TestResult(
                commit_sha=sha,
                build_success=False,
                test_success=False,
                build_output="",
                test_output="",
                error_message="Failed to checkout commit",
            )

        # Build if build command provided
        build_output = ""
        build_success = True
        if self.build_cmd:
            build_success, build_output = self.run_command(
                self.build_cmd,
                self.repo_path,
                timeout=600,
            )
            if not build_success:
                return TestResult(
                    commit_sha=sha,
                    build_success=False,
                    test_success=False,
                    build_output=build_output,
                    test_output="",
                    error_message="Build failed",
                )

        # Run tests if test command provided
        test_output = ""
        test_success = True
        if self.test_cmd:
            test_success, test_output = self.run_command(
                self.test_cmd,
                self.repo_path,
                timeout=900,
            )

        return TestResult(
            commit_sha=sha,
            build_success=build_success,
            test_success=test_success,
            build_output=build_output,
            test_output=test_output,
        )

    def validate_commit(self, commit_sha: str) -> tuple[TestResult, TestResult]:
        """Validate that both commit and parent pass tests.

        Args:
            commit_sha: SHA of commit to validate

        Returns:
            (parent_result, commit_result) tuple
        """
        # Get parent SHA
        parent_sha_result = subprocess.run(
            ["git", "-C", str(self.repo_path), "rev-parse", f"{commit_sha}^"],
            capture_output=True,
            text=True,
        )
        parent_sha = parent_sha_result.stdout.strip()

        logger.info(f"Testing parent commit: {parent_sha[:10]}")
        with self.safe_checkout(parent_sha):
            # Build if needed
            if self.build_cmd:
                logger.info("Building parent commit...")
            parent_result = self.test_commit(parent_sha)

        logger.info(f"Testing target commit: {commit_sha[:10]}")
        with self.safe_checkout(commit_sha):
            # Build if needed
            if self.build_cmd:
                logger.info("Building target commit...")
            commit_result = self.test_commit(commit_sha)

        return (parent_result, commit_result)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate that a commit has passing tests before and after"
    )
    parser.add_argument("repo_path", type=Path, help="Path to git repository")
    parser.add_argument("commit_sha", help="Commit SHA to validate")
    parser.add_argument("--build-cmd", help="Command to build (optional)")
    parser.add_argument("--test-cmd", help="Command to run tests (required)")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (JSON format)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.repo_path.exists():
        logger.error(f"Repository path does not exist: {args.repo_path}")
        sys.exit(1)

    if not args.test_cmd:
        logger.error("--test-cmd is required for validation")
        sys.exit(1)

    # Create validator
    validator = CommitValidator(args.repo_path, args.build_cmd, args.test_cmd)

    # Validate commit
    print(f"\nValidating commit {args.commit_sha} in {args.repo_path.name}...")
    print("-" * 80)

    parent_result, commit_result = validator.validate_commit(args.commit_sha)

    # Print results
    print("\nResults:")
    print("-" * 80)

    print(f"\nParent commit ({parent_result.commit_sha[:10]}):")
    print(f"  Build: {'✓ PASS' if parent_result.build_success else '✗ FAIL'}")
    print(f"  Tests: {'✓ PASS' if parent_result.test_success else '✗ FAIL'}")
    if parent_result.error_message:
        print(f"  Error: {parent_result.error_message}")

    print(f"\nTarget commit ({commit_result.commit_sha[:10]}):")
    print(f"  Build: {'✓ PASS' if commit_result.build_success else '✗ FAIL'}")
    print(f"  Tests: {'✓ PASS' if commit_result.test_success else '✗ FAIL'}")
    if commit_result.error_message:
        print(f"  Error: {commit_result.error_message}")

    # Overall validation
    print("\n" + "=" * 80)
    both_pass = (
        parent_result.build_success
        and parent_result.test_success
        and commit_result.build_success
        and commit_result.test_success
    )

    if both_pass:
        print("✓ VALIDATION PASSED: Both parent and commit have passing tests")
        print("This commit is suitable for a benchmark task.")
        sys.exit(0)
    else:
        print("✗ VALIDATION FAILED: One or both commits do not pass tests")
        print("This commit is NOT suitable for a benchmark task.")
        sys.exit(1)


if __name__ == "__main__":
    main()
