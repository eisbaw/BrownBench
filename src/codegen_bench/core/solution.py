"""Solution dataclass."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Solution:
    """Output from a code generation approach."""

    # Identifiers
    approach_id: str
    task_id: str
    seed: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Outputs
    changed_files: dict[str, str] = field(default_factory=dict)  # path -> content
    new_files: dict[str, str] = field(default_factory=dict)
    deleted_files: list[str] = field(default_factory=list)
    tests: dict[str, str] | None = None
    documentation: str | None = None

    # Metrics
    generation_time_seconds: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_calls: int = 0
    cost_usd: float = 0.0

    # Intermediate state (for analysis)
    reasoning_trace: str | None = None
    iterations: int = 1

    # Validation results
    compiles: bool | None = None
    tests_pass: bool | None = None
    test_output: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "approach_id": self.approach_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "timestamp": self.timestamp.isoformat(),
            "changed_files": self.changed_files,
            "new_files": self.new_files,
            "deleted_files": self.deleted_files,
            "tests": self.tests,
            "documentation": self.documentation,
            "generation_time_seconds": self.generation_time_seconds,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "api_calls": self.api_calls,
            "cost_usd": self.cost_usd,
            "reasoning_trace": self.reasoning_trace,
            "iterations": self.iterations,
            "compiles": self.compiles,
            "tests_pass": self.tests_pass,
            "test_output": self.test_output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Solution":
        """Deserialize from dict.

        Args:
            data: Dictionary with solution data

        Returns:
            Solution instance

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ["approach_id", "task_id", "seed"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields in Solution.from_dict(): {missing_fields}")

        # Parse timestamp
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)
