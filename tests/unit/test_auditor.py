"""Unit tests for DUTAuditor security analysis."""

import ast

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach
from codegen_bench.security.auditor import AuditReport, DUTAuditor, RiskLevel


# Test DUT implementations for security testing
class SafeDUT(CodeGenerationApproach):
    """A safe DUT implementation with no security issues."""

    APPROACH_ID = "safe-dut"

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
            name="Safe DUT",
            description="A safe implementation",
            version="1.0.0",
        )


class DangerousEvalDUT(CodeGenerationApproach):
    """DUT that uses eval() - should be flagged as CRITICAL."""

    APPROACH_ID = "dangerous-eval"

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
            name="Dangerous Eval DUT",
            description="Uses eval()",
            version="1.0.0",
        )


class SubprocessDUT(CodeGenerationApproach):
    """DUT that uses subprocess - should be flagged as HIGH."""

    APPROACH_ID = "subprocess-dut"

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution with subprocess."""
        import subprocess

        result = subprocess.run(["echo", "hello"], capture_output=True, text=True, check=True)
        return Solution(
            approach_id=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
            changed_files={"test.py": result.stdout},
        )

    def get_metadata(self) -> ApproachMetadata:
        """Return metadata."""
        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="Subprocess DUT",
            description="Uses subprocess",
            version="1.0.0",
        )


class NetworkAccessDUT(CodeGenerationApproach):
    """DUT that uses network access - should be flagged."""

    APPROACH_ID = "network-dut"

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution with network access."""
        import socket

        # Hypothetical network call (unused but triggers audit)
        _sock = socket.socket()
        return Solution(
            approach_id=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
            changed_files={"test.py": "print('network')"},
        )

    def get_metadata(self) -> ApproachMetadata:
        """Return metadata."""
        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="Network DUT",
            description="Uses network",
            version="1.0.0",
        )


class FileDeleteDUT(CodeGenerationApproach):
    """DUT that deletes files - should be flagged as HIGH."""

    APPROACH_ID = "file-delete-dut"

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution with file deletion."""
        import os

        # Dangerous file operation
        os.remove("/tmp/test.txt")
        return Solution(
            approach_id=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
            changed_files={"test.py": "print('deleted')"},
        )

    def get_metadata(self) -> ApproachMetadata:
        """Return metadata."""
        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="File Delete DUT",
            description="Deletes files",
            version="1.0.0",
        )


class TestAuditReport:
    """Test AuditReport functionality."""

    def test_empty_report(self) -> None:
        """Test report with no findings."""
        report = AuditReport(dut_class_name="TestDUT", dut_module="test.module")

        assert report.passed is True
        assert len(report.findings) == 0
        assert "No security issues" in report.get_summary()

    def test_add_finding_low_risk(self) -> None:
        """Test adding low risk finding doesn't fail audit."""
        report = AuditReport(dut_class_name="TestDUT", dut_module="test.module")
        report.add_finding(
            risk_level=RiskLevel.LOW,
            category="test",
            description="Low risk issue",
        )

        assert report.passed is True
        assert len(report.findings) == 1
        assert report.findings[0].risk_level == RiskLevel.LOW

    def test_add_finding_high_risk(self) -> None:
        """Test adding high risk finding fails audit."""
        report = AuditReport(dut_class_name="TestDUT", dut_module="test.module")
        report.add_finding(
            risk_level=RiskLevel.HIGH,
            category="test",
            description="High risk issue",
        )

        assert report.passed is False
        assert len(report.findings) == 1

    def test_add_finding_critical_risk(self) -> None:
        """Test adding critical risk finding fails audit."""
        report = AuditReport(dut_class_name="TestDUT", dut_module="test.module")
        report.add_finding(
            risk_level=RiskLevel.CRITICAL,
            category="test",
            description="Critical issue",
        )

        assert report.passed is False
        assert len(report.findings) == 1

    def test_summary_with_findings(self) -> None:
        """Test summary generation with multiple findings."""
        report = AuditReport(dut_class_name="TestDUT", dut_module="test.module")
        report.add_finding(RiskLevel.LOW, "test", "Low issue")
        report.add_finding(RiskLevel.MEDIUM, "test", "Medium issue")
        report.add_finding(RiskLevel.HIGH, "test", "High issue")

        summary = report.get_summary()
        assert "TestDUT" in summary
        assert "FAILED" in summary
        assert "high" in summary.lower()

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        report = AuditReport(dut_class_name="TestDUT", dut_module="test.module")
        report.add_finding(
            risk_level=RiskLevel.MEDIUM,
            category="security",
            description="Test issue",
            location="line 42",
            recommendation="Fix it",
        )

        data = report.to_dict()
        assert data["dut_class_name"] == "TestDUT"
        assert data["dut_module"] == "test.module"
        assert data["passed"] is True  # MEDIUM doesn't fail
        assert len(data["findings"]) == 1
        assert data["findings"][0]["risk_level"] == "medium"


class TestDUTAuditor:
    """Test DUTAuditor security analysis."""

    def test_audit_safe_dut(self) -> None:
        """Test auditing a safe DUT with no issues."""
        auditor = DUTAuditor()
        report = auditor.audit_dut(SafeDUT)

        assert report.passed is True
        assert len(report.findings) == 0
        assert report.dut_class_name == "SafeDUT"

    def test_audit_dangerous_eval(self) -> None:
        """Test detection of eval() usage."""
        auditor = DUTAuditor()
        report = auditor.audit_dut(DangerousEvalDUT)

        assert report.passed is False
        # Should have at least one CRITICAL finding for eval()
        critical_findings = [f for f in report.findings if f.risk_level == RiskLevel.CRITICAL]
        assert len(critical_findings) >= 1
        assert any("eval" in f.description.lower() for f in critical_findings)

    def test_audit_subprocess_usage(self) -> None:
        """Test detection of subprocess module."""
        auditor = DUTAuditor()
        report = auditor.audit_dut(SubprocessDUT)

        assert report.passed is False
        # Should have HIGH risk finding for subprocess
        high_findings = [f for f in report.findings if f.risk_level == RiskLevel.HIGH]
        assert len(high_findings) >= 1
        assert any("subprocess" in f.description.lower() for f in high_findings)

    def test_audit_network_access(self) -> None:
        """Test detection of network modules."""
        auditor = DUTAuditor()
        report = auditor.audit_dut(NetworkAccessDUT)

        # Should detect socket import (may be MEDIUM risk)
        network_findings = [
            f for f in report.findings if "network" in f.category.lower() or "socket" in f.description.lower()
        ]
        assert len(network_findings) >= 1

    def test_audit_file_deletion(self) -> None:
        """Test detection of destructive file operations."""
        auditor = DUTAuditor()
        report = auditor.audit_dut(FileDeleteDUT)

        assert report.passed is False
        # Should have HIGH risk finding for os.remove
        high_findings = [f for f in report.findings if f.risk_level == RiskLevel.HIGH]
        assert len(high_findings) >= 1
        assert any("remove" in f.description.lower() or "filesystem" in f.category.lower() for f in high_findings)

    def test_get_function_name(self) -> None:
        """Test function name extraction from AST."""
        auditor = DUTAuditor()

        # Test simple name
        node = ast.parse("foo()").body[0].value  # type: ignore[attr-defined]
        name = auditor._get_function_name(node.func)
        assert name == "foo"

        # Test attribute
        node = ast.parse("obj.method()").body[0].value  # type: ignore[attr-defined]
        name = auditor._get_function_name(node.func)
        assert name == "method"

    def test_get_full_function_name(self) -> None:
        """Test full dotted function name extraction."""
        auditor = DUTAuditor()

        # Test simple name
        node = ast.parse("foo()").body[0].value  # type: ignore[attr-defined]
        name = auditor._get_full_function_name(node.func)
        assert name == "foo"

        # Test dotted name
        node = ast.parse("os.system()").body[0].value  # type: ignore[attr-defined]
        name = auditor._get_full_function_name(node.func)
        assert name == "os.system"

        # Test nested dotted name
        node = ast.parse("shutil.rmtree()").body[0].value  # type: ignore[attr-defined]
        name = auditor._get_full_function_name(node.func)
        assert name == "shutil.rmtree"

    def test_get_imports(self) -> None:
        """Test import extraction from AST."""
        auditor = DUTAuditor()

        code = """
import os
import sys
from pathlib import Path
import anthropic.types
"""
        tree = ast.parse(code)
        imports = auditor._get_imports(tree)

        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports
        assert "anthropic" in imports

    def test_check_dangerous_calls(self) -> None:
        """Test dangerous function call detection."""
        auditor = DUTAuditor()
        report = AuditReport(dut_class_name="Test", dut_module="test")

        code = """
def foo():
    eval("1 + 1")
    exec("print('hello')")
"""
        tree = ast.parse(code)
        auditor._check_dangerous_calls(tree, report)

        # Should find both eval and exec
        assert len(report.findings) >= 2
        assert any("eval" in f.description.lower() for f in report.findings)
        assert any("exec" in f.description.lower() for f in report.findings)

    def test_check_network_access(self) -> None:
        """Test network access pattern detection."""
        auditor = DUTAuditor()
        report = AuditReport(dut_class_name="Test", dut_module="test")

        code = """
import socket
import requests
import httpx
"""
        tree = ast.parse(code)
        auditor._check_network_access(tree, report)

        # httpx is allowed (used by anthropic SDK)
        # socket and requests should be flagged
        flagged = [f for f in report.findings if "socket" in f.description.lower() or "requests" in f.description.lower()]
        assert len(flagged) >= 1

    def test_check_code_execution(self) -> None:
        """Test code execution pattern detection."""
        auditor = DUTAuditor()
        report = AuditReport(dut_class_name="Test", dut_module="test")

        code = """
import subprocess
import os

def dangerous():
    os.system("ls")
    subprocess.run(["echo", "hello"])
"""
        tree = ast.parse(code)
        auditor._check_code_execution(tree, report)

        # Should flag both subprocess import and os.system call
        assert len(report.findings) >= 2
        assert any("subprocess" in f.description.lower() for f in report.findings)
        assert any("os.system" in f.description.lower() for f in report.findings)


class TestDUTAuditorIntegration:
    """Integration tests for DUTAuditor with real DUTs."""

    def test_audit_simple_chat_dut(self) -> None:
        """Test auditing SimpleChatDUT (should be safe)."""
        from codegen_bench.dut.simple_chat import SimpleChatDUT

        auditor = DUTAuditor()
        report = auditor.audit_dut(SimpleChatDUT)

        # SimpleChatDUT should be relatively safe
        # It may have some findings but shouldn't fail
        assert report.dut_class_name == "SimpleChatDUT"
        # Check there are no CRITICAL findings
        critical = [f for f in report.findings if f.risk_level == RiskLevel.CRITICAL]
        assert len(critical) == 0

    def test_audit_elaborate_prompt_dut(self) -> None:
        """Test auditing ElaboratePromptDUT (should be safe)."""
        from codegen_bench.dut.elaborate_prompt import ElaboratePromptDUT

        auditor = DUTAuditor()
        report = auditor.audit_dut(ElaboratePromptDUT)

        # ElaboratePromptDUT uses open() to read files
        # This should be flagged but not critical
        assert report.dut_class_name == "ElaboratePromptDUT"

        # Should have finding for open() usage
        open_findings = [f for f in report.findings if "open" in f.description.lower()]
        assert len(open_findings) >= 1

        # But shouldn't fail (open is HIGH at most, not CRITICAL)
        # Actually, open is flagged for review, not critical
        critical = [f for f in report.findings if f.risk_level == RiskLevel.CRITICAL]
        assert len(critical) == 0
