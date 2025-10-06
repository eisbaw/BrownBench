"""DUT registry for managing available approaches."""

from typing import Any

from codegen_bench.dut.base import CodeGenerationApproach


class DUTRegistry:
    """Registry of available DUTs."""

    _registry: dict[str, type[CodeGenerationApproach]] = {}

    @classmethod
    def register(cls, dut_class: type[CodeGenerationApproach]) -> type[CodeGenerationApproach]:
        """Register a DUT implementation.

        Args:
            dut_class: DUT class to register

        Returns:
            The same class (for use as decorator)
        """
        # Get ID from metadata (need dummy instance)
        dummy = dut_class(config={})
        dut_id = dummy.get_metadata().id
        cls._registry[dut_id] = dut_class
        return dut_class

    @classmethod
    def get(cls, dut_id: str) -> type[CodeGenerationApproach]:
        """Get DUT class by ID.

        Args:
            dut_id: DUT identifier

        Returns:
            DUT class

        Raises:
            ValueError: If DUT not found
        """
        if dut_id not in cls._registry:
            raise ValueError(f"Unknown DUT: {dut_id}")
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
        """List all registered DUTs.

        Returns:
            List of DUT IDs
        """
        return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear registry (for testing)."""
        cls._registry.clear()
