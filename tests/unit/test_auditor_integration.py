"""Integration tests for DUTAuditor with DUTRegistry."""

import pytest

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.exceptions import DUTError


class SafeTestDUT(CodeGenerationApproach):
    """A safe DUT for testing."""

    APPROACH_ID = "safe-test-dut"

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution safely."""
        return Solution(
            approach_id=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
            changed_files={"test.py": "print('hello')"},
        )

    def get_metadata(self) -> ApproachMetadata:
        """Return metadata."""
        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="Safe Test DUT",
            description="A safe implementation",
            version="1.0.0",
        )


class DangerousTestDUT(CodeGenerationApproach):
    """A dangerous DUT that should fail audit."""

    APPROACH_ID = "dangerous-test-dut"

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution with eval()."""
        code = eval("'print(hello)'")  # noqa: S307
        return Solution(
            approach_id=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
            changed_files={"test.py": code},
        )

    def get_metadata(self) -> ApproachMetadata:
        """Return metadata."""
        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="Dangerous Test DUT",
            description="Uses eval()",
            version="1.0.0",
        )


class TestDUTRegistryAuditing:
    """Test DUTRegistry integration with auditing."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        DUTRegistry.clear()
        DUTRegistry.set_audit_on_register(False)

    def teardown_method(self) -> None:
        """Clean up after each test."""
        DUTRegistry.clear()
        DUTRegistry.set_audit_on_register(False)

    def test_register_without_audit(self) -> None:
        """Test registering DUT without auditing."""
        DUTRegistry.register(SafeTestDUT)
        assert "safe-test-dut" in DUTRegistry.list_available()

    def test_register_with_audit_safe_dut(self) -> None:
        """Test registering safe DUT with auditing enabled."""
        # Should succeed
        DUTRegistry.register(SafeTestDUT, audit=True)
        assert "safe-test-dut" in DUTRegistry.list_available()

    def test_register_with_audit_dangerous_dut(self) -> None:
        """Test registering dangerous DUT with auditing should fail."""
        # Should raise DUTError due to failed audit
        with pytest.raises(DUTError, match="failed security audit"):
            DUTRegistry.register(DangerousTestDUT, audit=True)

        # Should not be registered
        assert "dangerous-test-dut" not in DUTRegistry.list_available()

    def test_global_audit_setting(self) -> None:
        """Test global audit-on-register setting."""
        # Enable global auditing
        DUTRegistry.set_audit_on_register(True)

        # Safe DUT should register fine
        DUTRegistry.register(SafeTestDUT)
        assert "safe-test-dut" in DUTRegistry.list_available()

        # Dangerous DUT should fail
        with pytest.raises(DUTError, match="failed security audit"):
            DUTRegistry.register(DangerousTestDUT)

        assert "dangerous-test-dut" not in DUTRegistry.list_available()

    def test_manual_audit(self) -> None:
        """Test manually auditing a registered DUT."""
        # Register without audit
        DUTRegistry.register(SafeTestDUT, audit=False)
        DUTRegistry.register(DangerousTestDUT, audit=False)

        # Manually audit safe DUT
        report = DUTRegistry.audit_dut("safe-test-dut")
        assert report.passed is True

        # Manually audit dangerous DUT
        report = DUTRegistry.audit_dut("dangerous-test-dut")
        assert report.passed is False

    def test_audit_override_global_setting(self) -> None:
        """Test that explicit audit parameter overrides global setting."""
        # Enable global auditing
        DUTRegistry.set_audit_on_register(True)

        # But explicitly disable for this registration
        DUTRegistry.register(DangerousTestDUT, audit=False)

        # Should be registered despite being dangerous
        assert "dangerous-test-dut" in DUTRegistry.list_available()

    def test_manual_audit_nonexistent_dut(self) -> None:
        """Test manually auditing a DUT that doesn't exist."""
        with pytest.raises(DUTError, match="Unknown DUT"):
            DUTRegistry.audit_dut("nonexistent-dut")
