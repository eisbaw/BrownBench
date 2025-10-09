"""DUT registry for managing available approaches.

Note: DUT classes can be used directly without registration:
    dut = SimpleChatDUT(config={...})
    solution = dut.solve(task, seed=42)

The registry is an optional convenience for dynamic DUT loading and CLI usage.

Instance vs Class Usage:
    For isolated testing, create an instance:
        registry = DUTRegistry()
        registry.register(MyDUT)

    For global usage (CLI, backward compatibility):
        DUTRegistry.register(MyDUT)  # Uses default instance
"""

import threading
from contextlib import contextmanager
from typing import Any, Iterator

import structlog

from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.exceptions import DUTError

logger = structlog.get_logger(__name__)


class DUTRegistry:
    """Thread-safe registry of available DUTs.

    This registry is an optional convenience for dynamic DUT discovery.
    All DUT classes can be instantiated and used directly without registration.

    Supports both instance-based (for testing) and class-based (for backward compatibility) usage:

    Instance usage (recommended for testing):
        registry = DUTRegistry()
        registry.register(MyDUT)

    Class usage (backward compatible):
        DUTRegistry.register(MyDUT)  # Uses default instance

    Thread safety: All operations on the registry are protected by a lock
    to support concurrent registration and lookups.
    """

    # Default instance for class-level methods (backward compatibility)
    _default_instance: "DUTRegistry | None" = None
    _default_lock = threading.Lock()

    def __init__(self):
        """Initialize a new registry instance."""
        self._registry: dict[str, type[CodeGenerationApproach]] = {}
        self._lock = threading.RLock()
        self._audit_on_register: bool = False

    @classmethod
    def _get_default_instance(cls) -> "DUTRegistry":
        """Get or create the default registry instance."""
        if cls._default_instance is None:
            with cls._default_lock:
                if cls._default_instance is None:
                    cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def register(
        cls, dut_class: type[CodeGenerationApproach], audit: bool | None = None
    ) -> type[CodeGenerationApproach]:
        """Register a DUT implementation (class method for backward compatibility).

        Args:
            dut_class: DUT class to register
            audit: Whether to audit the DUT for security issues. If None, uses _audit_on_register.

        Returns:
            The same class (for use as decorator)

        Raises:
            DUTError: If DUT class doesn't define APPROACH_ID or fails security audit
        """
        return cls._get_default_instance().register_instance(dut_class, audit)

    def register_instance(
        self, dut_class: type[CodeGenerationApproach], audit: bool | None = None
    ) -> type[CodeGenerationApproach]:
        """Register a DUT implementation in this registry instance.

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
        should_audit = audit if audit is not None else self._audit_on_register
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
                    findings=[
                        f.description
                        for f in report.findings
                        if f.risk_level.value in ("critical", "high")
                    ],
                )
                raise DUTError(f"DUT {dut_id} failed security audit: {report.get_summary()}")

        with self._lock:
            self._registry[dut_id] = dut_class

        return dut_class

    @classmethod
    def get(cls, dut_id: str) -> type[CodeGenerationApproach]:
        """Get DUT class by ID (class method for backward compatibility).

        Args:
            dut_id: DUT identifier

        Returns:
            DUT class

        Raises:
            DUTError: If DUT not found
        """
        return cls._get_default_instance().get_instance(dut_id)

    def get_instance(self, dut_id: str) -> type[CodeGenerationApproach]:
        """Get DUT class by ID from this registry instance.

        Args:
            dut_id: DUT identifier

        Returns:
            DUT class

        Raises:
            DUTError: If DUT not found
        """
        with self._lock:
            if dut_id not in self._registry:
                raise DUTError(f"Unknown DUT: {dut_id}")
            return self._registry[dut_id]

    @classmethod
    def create(cls, dut_id: str, config: dict[str, Any]) -> CodeGenerationApproach:
        """Create DUT instance by ID (class method for backward compatibility).

        Args:
            dut_id: DUT identifier
            config: Configuration for DUT

        Returns:
            DUT instance
        """
        return cls._get_default_instance().create_instance(dut_id, config)

    def create_instance(self, dut_id: str, config: dict[str, Any]) -> CodeGenerationApproach:
        """Create DUT instance by ID from this registry.

        Args:
            dut_id: DUT identifier
            config: Configuration for DUT

        Returns:
            DUT instance
        """
        dut_class = self.get_instance(dut_id)
        return dut_class(config=config)

    @classmethod
    def list_available(cls) -> list[str]:
        """List all registered DUTs (class method for backward compatibility).

        Returns:
            Sorted list of DUT IDs
        """
        return cls._get_default_instance().list_available_instance()

    def list_available_instance(self) -> list[str]:
        """List all registered DUTs in this registry instance.

        Returns:
            Sorted list of DUT IDs
        """
        with self._lock:
            return sorted(self._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear default registry (class method for backward compatibility).

        Warning: Not thread-safe with respect to imports.
        Only use in single-threaded test setup/teardown.
        """
        cls._get_default_instance().clear_instance()

    def clear_instance(self) -> None:
        """Clear this registry instance.

        Warning: Not thread-safe with respect to imports.
        Only use in single-threaded test setup/teardown.
        """
        with self._lock:
            self._registry.clear()

    @classmethod
    def set_audit_on_register(cls, enabled: bool) -> None:
        """Enable or disable automatic security auditing (class method).

        Args:
            enabled: Whether to audit DUTs when they are registered
        """
        cls._get_default_instance().set_audit_on_register_instance(enabled)

    def set_audit_on_register_instance(self, enabled: bool) -> None:
        """Enable or disable automatic security auditing on this instance.

        Args:
            enabled: Whether to audit DUTs when they are registered
        """
        with self._lock:
            self._audit_on_register = enabled

    @classmethod
    def audit_dut(cls, dut_id: str) -> Any:
        """Manually audit a registered DUT (class method).

        Args:
            dut_id: DUT identifier to audit

        Returns:
            AuditReport with findings

        Raises:
            DUTError: If DUT not found
        """
        return cls._get_default_instance().audit_dut_instance(dut_id)

    def audit_dut_instance(self, dut_id: str) -> Any:
        """Manually audit a registered DUT in this instance.

        Args:
            dut_id: DUT identifier to audit

        Returns:
            AuditReport with findings

        Raises:
            DUTError: If DUT not found
        """
        from codegen_bench.security.auditor import DUTAuditor

        dut_class = self.get_instance(dut_id)
        auditor = DUTAuditor()
        return auditor.audit_dut(dut_class)

    @classmethod
    @contextmanager
    def isolated(cls) -> Iterator["DUTRegistry"]:
        """Create an isolated registry instance for testing.

        This context manager provides a fresh registry that doesn't
        affect the global default instance, useful for parallel testing.

        Example:
            with DUTRegistry.isolated() as registry:
                registry.register_instance(MyDUT)
                # Test with isolated registry
                assert registry.list_available_instance() == ["my-dut"]
            # Registry is discarded after context exit

        Yields:
            Fresh DUTRegistry instance
        """
        registry = cls()
        yield registry
        # Registry is automatically discarded when context exits
