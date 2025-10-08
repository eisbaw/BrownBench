"""DUT registry for managing available approaches.

Note: DUT classes can be used directly without registration:
    dut = SimpleChatDUT(config={...})
    solution = dut.solve(task, seed=42)

The registry is an optional convenience for dynamic DUT loading and CLI usage.
"""

import threading
from typing import Any

import structlog

from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.exceptions import DUTError

logger = structlog.get_logger(__name__)


class DUTRegistry:
    """Thread-safe registry of available DUTs.

    This registry is an optional convenience for dynamic DUT discovery.
    All DUT classes can be instantiated and used directly without registration.

    Thread safety: All operations on the registry are protected by a lock
    to support concurrent registration and lookups.
    """

    _registry: dict[str, type[CodeGenerationApproach]] = {}
    _lock = threading.RLock()
    _audit_on_register: bool = False  # Set to True to audit DUTs on registration

    @classmethod
    def register(
        cls, dut_class: type[CodeGenerationApproach], audit: bool | None = None
    ) -> type[CodeGenerationApproach]:
        """Register a DUT implementation in a thread-safe manner.

        Args:
            dut_class: DUT class to register
            audit: Whether to audit the DUT for security issues. If None, uses _audit_on_register.

        Returns:
            The same class (for use as decorator)

        Raises:
            DUTError: If DUT class doesn't define APPROACH_ID or fails security audit
        """
        # Get ID from class attribute (no instance needed)
        dut_id = dut_class.APPROACH_ID
        if not dut_id:
            raise DUTError(f"{dut_class.__name__} must define APPROACH_ID class attribute")

        # Optionally audit the DUT for security issues
        should_audit = audit if audit is not None else cls._audit_on_register
        if should_audit:
            from codegen_bench.security.auditor import DUTAuditor

            auditor = DUTAuditor()
            report = auditor.audit_dut(dut_class)

            logger.info(
                "dut_audit_completed",
                dut_id=dut_id,
                passed=report.passed,
                num_findings=len(report.findings),
            )

            if not report.passed:
                logger.error(
                    "dut_audit_failed",
                    dut_id=dut_id,
                    summary=report.get_summary(),
                    findings=[f.description for f in report.findings if f.risk_level.value in ("critical", "high")],
                )
                raise DUTError(
                    f"DUT {dut_id} failed security audit: {report.get_summary()}"
                )

        with cls._lock:
            cls._registry[dut_id] = dut_class

        return dut_class

    @classmethod
    def get(cls, dut_id: str) -> type[CodeGenerationApproach]:
        """Get DUT class by ID in a thread-safe manner.

        Args:
            dut_id: DUT identifier

        Returns:
            DUT class

        Raises:
            DUTError: If DUT not found
        """
        with cls._lock:
            if dut_id not in cls._registry:
                raise DUTError(f"Unknown DUT: {dut_id}")
            return cls._registry[dut_id]

    @classmethod
    def create(cls, dut_id: str, config: dict[str, Any]) -> CodeGenerationApproach:
        """Create DUT instance by ID.

        Args:
            dut_id: DUT identifier
            config: Configuration for DUT

        Returns:
            DUT instance
        """
        dut_class = cls.get(dut_id)
        return dut_class(config=config)

    @classmethod
    def list_available(cls) -> list[str]:
        """List all registered DUTs in a thread-safe manner.

        Returns:
            Sorted list of DUT IDs
        """
        with cls._lock:
            return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear registry (for testing).

        Warning: Not thread-safe with respect to imports.
        Only use in single-threaded test setup/teardown.
        """
        with cls._lock:
            cls._registry.clear()

    @classmethod
    def set_audit_on_register(cls, enabled: bool) -> None:
        """Enable or disable automatic security auditing on DUT registration.

        Args:
            enabled: Whether to audit DUTs when they are registered
        """
        with cls._lock:
            cls._audit_on_register = enabled

    @classmethod
    def audit_dut(cls, dut_id: str) -> Any:
        """Manually audit a registered DUT for security issues.

        Args:
            dut_id: DUT identifier to audit

        Returns:
            AuditReport with findings

        Raises:
            DUTError: If DUT not found
        """
        from codegen_bench.security.auditor import DUTAuditor

        dut_class = cls.get(dut_id)
        auditor = DUTAuditor()
        return auditor.audit_dut(dut_class)
