"""DUT registry for managing available approaches.

Note: DUT classes can be used directly without registration:
    dut = SimpleChatDUT(config={...})
    solution = dut.solve(task, seed=42)

The registry is an optional convenience for dynamic DUT loading and CLI usage.
"""

import threading
from typing import Any

from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.exceptions import DUTError


class DUTRegistry:
    """Thread-safe registry of available DUTs.

    This registry is an optional convenience for dynamic DUT discovery.
    All DUT classes can be instantiated and used directly without registration.

    Thread safety: All operations on the registry are protected by a lock
    to support concurrent registration and lookups.
    """

    _registry: dict[str, type[CodeGenerationApproach]] = {}
    _lock = threading.RLock()

    @classmethod
    def register(cls, dut_class: type[CodeGenerationApproach]) -> type[CodeGenerationApproach]:
        """Register a DUT implementation in a thread-safe manner.

        Args:
            dut_class: DUT class to register

        Returns:
            The same class (for use as decorator)

        Raises:
            DUTError: If DUT class doesn't define APPROACH_ID
        """
        # Get ID from class attribute (no instance needed)
        dut_id = dut_class.APPROACH_ID
        if not dut_id:
            raise DUTError(f"{dut_class.__name__} must define APPROACH_ID class attribute")

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
