"""Base classes for DUT implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task


@dataclass
class ApproachMetadata:
    """Metadata about a code generation approach."""

    id: str
    name: str
    description: str
    version: str
    model: str | None = None
    provider: str | None = None
    config: dict[str, Any] | None = None


class CodeGenerationApproach(ABC):
    """Abstract base for all DUT implementations."""

    def __init__(self, config: dict[str, Any]):
        """Initialize approach with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config

    @abstractmethod
    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution for task.

        Args:
            task: Task specification
            seed: Random seed for reproducibility

        Returns:
            Solution with code, metrics, metadata
        """
        pass

    @abstractmethod
    def get_metadata(self) -> ApproachMetadata:
        """Return approach configuration.

        Returns:
            ApproachMetadata describing this approach
        """
        pass

    def __str__(self) -> str:
        """String representation."""
        metadata = self.get_metadata()
        return f"{metadata.name} (v{metadata.version})"
