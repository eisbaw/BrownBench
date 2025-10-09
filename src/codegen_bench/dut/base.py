"""Base classes for DUT implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.utils.hashing import compute_prompt_hash


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
    prompt_hash: str | None = None  # SHA-256 hash of prompt template


class CodeGenerationApproach(ABC):
    """Abstract base for all DUT implementations."""

    # Subclasses should define this class attribute
    APPROACH_ID: str = ""

    # Default timeout for solve() method in seconds
    DEFAULT_TIMEOUT_SECONDS: int = 300  # 5 minutes

    def __init__(self, config: dict[str, Any]):
        """Initialize approach with configuration.

        Args:
            config: Configuration dictionary with optional keys:
                - timeout_seconds: Timeout for solve() in seconds (default: 300)
        """
        self.config = config
        self.timeout_seconds = config.get("timeout_seconds", self.DEFAULT_TIMEOUT_SECONDS)
        if not isinstance(self.timeout_seconds, int) or self.timeout_seconds <= 0:
            from codegen_bench.exceptions import DUTConfigError

            raise DUTConfigError(
                f"timeout_seconds must be a positive integer, got {self.timeout_seconds}"
            )

    def _compute_prompt_hash(self, prompt: str) -> str:
        """Compute SHA-256 hash of prompt.

        Args:
            prompt: The prompt content

        Returns:
            SHA-256 hash as hexadecimal string (first 16 chars for brevity)
        """
        return compute_prompt_hash(prompt)

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
