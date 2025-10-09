"""Static analysis and auditing for DUT implementations.

This module provides security auditing for DUT (Device Under Test) implementations
to detect potentially dangerous patterns before execution.
"""

import ast
import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from codegen_bench.dut.base import CodeGenerationApproach

logger = structlog.get_logger(__name__)


class RiskLevel(Enum):
    """Risk level for audit findings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditFinding:
    """Single security finding from DUT audit."""

    risk_level: RiskLevel
    category: str
    description: str
    location: str | None = None
    recommendation: str | None = None


@dataclass
class AuditReport:
    """Complete audit report for a DUT implementation."""

    dut_class_name: str
    dut_module: str
    findings: list[AuditFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if audit passed (no CRITICAL or HIGH findings).

        Returns:
            True if no critical/high risk findings, False otherwise
        """
        return not any(f.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH) for f in self.findings)

    @property
    def summary(self) -> str:
        """Generate summary (computed on demand).

        Returns:
            Human-readable summary string
        """
        return self.get_summary()

    def add_finding(
        self,
        risk_level: RiskLevel,
        category: str,
        description: str,
        location: str | None = None,
        recommendation: str | None = None,
    ) -> None:
        """Add a finding to the report.

        Args:
            risk_level: Severity of the finding
            category: Category of the issue
            description: Detailed description
            location: Code location (e.g., line number, function name)
            recommendation: Suggested fix or mitigation
        """
        finding = AuditFinding(
            risk_level=risk_level,
            category=category,
            description=description,
            location=location,
            recommendation=recommendation,
        )
        self.findings.append(finding)

    def get_summary(self) -> str:
        """Generate a summary of the audit.

        Returns:
            Human-readable summary
        """
        if not self.findings:
            return f"✓ {self.dut_class_name}: No security issues found"

        # Count by risk level
        counts = {level: 0 for level in RiskLevel}
        for finding in self.findings:
            counts[finding.risk_level] += 1

        status = "✓ PASSED" if self.passed else "✗ FAILED"
        parts = [f"{status} - {self.dut_class_name}:"]

        for level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            count = counts[level]
            if count > 0:
                parts.append(f"{count} {level.value}")

        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "dut_class_name": self.dut_class_name,
            "dut_module": self.dut_module,
            "passed": self.passed,
            "summary": self.get_summary(),
            "findings": [
                {
                    "risk_level": f.risk_level.value,
                    "category": f.category,
                    "description": f.description,
                    "location": f.location,
                    "recommendation": f.recommendation,
                }
                for f in self.findings
            ],
        }


class DUTAuditor:
    """Static analyzer for DUT implementations to detect security issues.

    The auditor performs static analysis on DUT classes to identify:
    - Dangerous function calls (exec, eval, subprocess, etc.)
    - Network access patterns
    - File system manipulation
    - Command injection vectors
    - API key handling issues
    """

    # Dangerous built-in functions
    DANGEROUS_BUILTINS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",  # Flag for review, not always dangerous
    }

    # Dangerous modules/functions for code execution
    DANGEROUS_MODULES = {
        "subprocess",
        "os.system",
        "os.popen",
        "os.exec",
        "commands",
        "pty",
    }

    # Network-related modules
    NETWORK_MODULES = {
        "socket",
        "urllib",
        "urllib3",
        "requests",
        "httpx",
        "aiohttp",
        "ftplib",
        "smtplib",
        "telnetlib",
    }

    # File system manipulation
    FILESYSTEM_MODULES = {
        "shutil.rmtree",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "pathlib.Path.unlink",
    }

    def audit_dut(self, dut_class: type[CodeGenerationApproach]) -> AuditReport:
        """Audit a DUT implementation for security issues.

        Args:
            dut_class: The DUT class to audit

        Returns:
            AuditReport with findings
        """
        logger.info("starting_dut_audit", dut_class=dut_class.__name__)

        report = AuditReport(
            dut_class_name=dut_class.__name__,
            dut_module=dut_class.__module__,
        )

        try:
            # Get source code
            source = inspect.getsource(dut_class)
            tree = ast.parse(source)

            # Run static analysis checks
            self._check_dangerous_calls(tree, report)
            self._check_network_access(tree, report)
            self._check_filesystem_operations(tree, report)
            self._check_code_execution(tree, report)

        except (OSError, TypeError) as e:
            logger.warning(
                "audit_source_unavailable",
                dut_class=dut_class.__name__,
                error=str(e),
            )
            report.add_finding(
                risk_level=RiskLevel.LOW,
                category="metadata",
                description=f"Could not retrieve source code: {e}",
                recommendation="Ensure DUT source code is available for auditing",
            )

        logger.info(
            "dut_audit_complete",
            dut_class=dut_class.__name__,
            passed=report.passed,
            num_findings=len(report.findings),
        )

        return report

    def _check_dangerous_calls(self, tree: ast.AST, report: AuditReport) -> None:
        """Check for dangerous built-in function calls.

        Args:
            tree: AST of the DUT source code
            report: Report to add findings to
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_function_name(node.func)
                if func_name in self.DANGEROUS_BUILTINS:
                    risk = RiskLevel.CRITICAL if func_name in {"eval", "exec"} else RiskLevel.HIGH
                    report.add_finding(
                        risk_level=risk,
                        category="dangerous_call",
                        description=f"Use of dangerous built-in: {func_name}()",
                        location=f"line {node.lineno}",
                        recommendation=f"Remove {func_name}() or justify its necessity",
                    )

    def _check_network_access(self, tree: ast.AST, report: AuditReport) -> None:
        """Check for network access patterns.

        Args:
            tree: AST of the DUT source code
            report: Report to add findings to
        """
        imports = self._get_imports(tree)

        for module in self.NETWORK_MODULES:
            if module in imports:
                # Check if it's an expected module (anthropic, openai are expected)
                if module not in {"httpx"}:  # httpx is used by anthropic SDK
                    report.add_finding(
                        risk_level=RiskLevel.MEDIUM,
                        category="network_access",
                        description=f"Network module imported: {module}",
                        location=f"import {module}",
                        recommendation="Ensure network access is necessary and properly restricted",
                    )

    def _check_filesystem_operations(self, tree: ast.AST, report: AuditReport) -> None:
        """Check for potentially dangerous filesystem operations.

        Args:
            tree: AST of the DUT source code
            report: Report to add findings to
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_full_function_name(node.func)

                # Check for destructive operations
                for dangerous_op in self.FILESYSTEM_MODULES:
                    if dangerous_op in func_name:
                        report.add_finding(
                            risk_level=RiskLevel.HIGH,
                            category="filesystem",
                            description=f"Destructive filesystem operation: {func_name}",
                            location=f"line {node.lineno}",
                            recommendation="Verify this operation is necessary and properly scoped",
                        )
                        break

    def _check_code_execution(self, tree: ast.AST, report: AuditReport) -> None:
        """Check for code execution patterns (subprocess, os.system, etc.).

        Args:
            tree: AST of the DUT source code
            report: Report to add findings to
        """
        imports = self._get_imports(tree)

        if "subprocess" in imports:
            report.add_finding(
                risk_level=RiskLevel.HIGH,
                category="code_execution",
                description="subprocess module imported - potential command execution",
                location="imports",
                recommendation="Verify all subprocess calls use shell=False and validate inputs",
            )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_full_function_name(node.func)

                # Check for os.system, os.popen, etc.
                for dangerous_exec in ["os.system", "os.popen", "os.exec"]:
                    if dangerous_exec in func_name:
                        report.add_finding(
                            risk_level=RiskLevel.CRITICAL,
                            category="code_execution",
                            description=f"Dangerous code execution: {func_name}",
                            location=f"line {node.lineno}",
                            recommendation=f"Replace {func_name} with safer alternatives",
                        )

    def _get_function_name(self, node: ast.expr) -> str:
        """Extract function name from AST node.

        Args:
            node: AST expression node

        Returns:
            Function name or empty string
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def _get_full_function_name(self, node: ast.expr) -> str:
        """Extract full dotted function name from AST node.

        Args:
            node: AST expression node

        Returns:
            Full function name (e.g., 'os.system')
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_full_function_name(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr
        return ""

    def _get_imports(self, tree: ast.AST) -> set[str]:
        """Extract all imported modules from AST.

        Args:
            tree: AST of source code

        Returns:
            Set of imported module names
        """
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

        return imports
