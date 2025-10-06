"""Execute validation commands (compile, test) on solutions."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of validation execution."""

    success: bool
    output: str
    error: str
    returncode: int
    timed_out: bool = False


class ValidationExecutor:
    """Execute compile and test commands in a workspace."""

    def __init__(self, workspace: Path):
        """Initialize validation executor.

        Args:
            workspace: Path to workspace where commands will run
        """
        self.workspace = Path(workspace).resolve()
        if not self.workspace.exists():
            raise ValueError(f"Workspace does not exist: {self.workspace}")

    def run_compile(
        self, compile_command: str, timeout: int = 300
    ) -> ValidationResult:
        """Run compile command.

        Args:
            compile_command: Shell command to run
            timeout: Timeout in seconds

        Returns:
            ValidationResult with compile results
        """
        return self._run_command(compile_command, timeout)

    def run_tests(
        self, test_command: str, timeout: int = 600
    ) -> ValidationResult:
        """Run test command.

        Args:
            test_command: Shell command to run
            timeout: Timeout in seconds

        Returns:
            ValidationResult with test results
        """
        return self._run_command(test_command, timeout)

    def _run_command(self, command: str, timeout: int) -> ValidationResult:
        """Run shell command in workspace.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds

        Returns:
            ValidationResult
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return ValidationResult(
                success=(result.returncode == 0),
                output=result.stdout,
                error=result.stderr,
                returncode=result.returncode,
                timed_out=False,
            )

        except subprocess.TimeoutExpired as e:
            return ValidationResult(
                success=False,
                output=e.stdout.decode() if e.stdout else "",
                error=e.stderr.decode() if e.stderr else "",
                returncode=-1,
                timed_out=True,
            )

        except Exception as e:
            return ValidationResult(
                success=False,
                output="",
                error=str(e),
                returncode=-1,
                timed_out=False,
            )

    def parse_test_output(self, output: str, framework: str = "pytest") -> dict[str, int | str]:
        """Parse test output to extract metrics.

        Args:
            output: Test output text
            framework: Test framework name (pytest, unittest, etc.)

        Returns:
            Dictionary with test metrics (passed, failed, skipped, etc.)
        """
        if framework == "pytest":
            return self._parse_pytest_output(output)
        elif framework == "unittest":
            return self._parse_unittest_output(output)
        else:
            return {"framework": framework, "raw_output": output}

    def _parse_pytest_output(self, output: str) -> dict[str, int | str]:
        """Parse pytest output.

        Args:
            output: Pytest output

        Returns:
            Dictionary with test counts
        """
        import re

        metrics = {
            "framework": "pytest",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Look for summary line like "5 passed, 2 failed, 1 skipped in 0.5s"
        pattern = r"(\d+)\s+(passed|failed|skipped|error)"
        for match in re.finditer(pattern, output):
            count = int(match.group(1))
            status = match.group(2)
            if status == "passed":
                metrics["passed"] = count
            elif status == "failed":
                metrics["failed"] = count
            elif status == "skipped":
                metrics["skipped"] = count
            elif status == "error":
                metrics["errors"] = count

        return metrics

    def _parse_unittest_output(self, output: str) -> dict[str, int | str]:
        """Parse unittest output.

        Args:
            output: Unittest output

        Returns:
            Dictionary with test counts
        """
        import re

        metrics = {
            "framework": "unittest",
            "passed": 0,
            "failed": 0,
            "errors": 0,
        }

        # Look for summary like "Ran 10 tests in 0.5s" and "OK" or "FAILED"
        tests_match = re.search(r"Ran (\d+) tests", output)
        if tests_match:
            total = int(tests_match.group(1))
            if "OK" in output:
                metrics["passed"] = total
            elif "FAILED" in output:
                # Look for failures/errors
                fail_match = re.search(r"failures=(\d+)", output)
                err_match = re.search(r"errors=(\d+)", output)
                if fail_match:
                    metrics["failed"] = int(fail_match.group(1))
                if err_match:
                    metrics["errors"] = int(err_match.group(1))
                failed_count = metrics["failed"] if isinstance(metrics["failed"], int) else 0
                errors_count = metrics["errors"] if isinstance(metrics["errors"], int) else 0
                metrics["passed"] = total - failed_count - errors_count

        return metrics
