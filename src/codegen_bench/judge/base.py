"""Base judge interface for solution comparison."""

from abc import ABC, abstractmethod
from typing import Literal

from codegen_bench.core.arena import Arena
from codegen_bench.core.judgment import JudgeVote
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task

Vote = Literal["A", "B", "TIE"]


class Judge(ABC):
    """Abstract base for AI judges that compare solutions."""

    def __init__(self, model: str, temperature: float = 0.3, variant: int = 0):
        """Initialize Judge.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-20250514")
            temperature: Sampling temperature for consistency
            variant: Prompt variant number for diversity
        """
        self.model = model
        self.temperature = temperature
        self.variant = variant

    @abstractmethod
    def evaluate(
        self, solution_a: Solution, solution_b: Solution, arena: Arena, task: Task
    ) -> JudgeVote:
        """Compare two solutions in a given arena.

        Args:
            solution_a: First solution to compare
            solution_b: Second solution to compare
            arena: Quality dimension to evaluate
            task: Task that solutions are solving

        Returns:
            JudgeVote with winner, reasoning, and confidence
        """
        pass

    def __str__(self) -> str:
        """String representation of judge."""
        return f"Judge({self.model}, variant={self.variant})"
