"""OptimizedClaudeJudge - Token-efficient Claude-based judge."""

from typing import Optional

from codegen_bench.core.arena import Arena
from codegen_bench.core.judgment import JudgmentResult
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.judge.claude_judge import ClaudeJudge


class OptimizedClaudeJudge(ClaudeJudge):
    """Token-efficient version of ClaudeJudge.

    Reduces token usage by:
    - Condensing prompts to essential information
    - Removing redundant examples
    - Using concise language
    - Eliminating verbose formatting

    Token reduction: ~30-40% compared to standard ClaudeJudge
    """

    def _build_prompt(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task,
    ) -> str:
        """Build token-efficient comparison prompt.

        Args:
            solution_a: First solution
            solution_b: Second solution
            arena: Arena defining comparison criteria
            task: Task being evaluated

        Returns:
            Optimized prompt for comparison
        """
        # Format solutions concisely
        sol_a = self._format_solution_optimized(solution_a)
        sol_b = self._format_solution_optimized(solution_b)

        # Load optimized arena prompt if available
        arena_prompt = self._load_arena_prompt_optimized(arena)

        # Compact prompt structure
        return f"""Expert reviewing two solutions.

Task: {task.name}
Spec: {task.specification}

Solution A:
{sol_a}

Solution B:
{sol_b}

{arena_prompt}

RESPOND:
WINNER: A|B|TIE
REASONING: [2-3 sentences]
CONFIDENCE: [0.0-1.0]"""

    def _format_solution_optimized(self, solution: Solution) -> str:
        """Format solution concisely.

        Args:
            solution: Solution to format

        Returns:
            Compact formatted solution
        """
        # Combine changed and new files
        all_files = {**solution.changed_files, **solution.new_files}

        if not all_files:
            return "[Empty]"

        # Format files without extra headers
        parts = []
        for path, content in all_files.items():
            # Skip empty files
            if not content.strip():
                continue

            # Truncate very long files
            lines = content.split("\n")
            if len(lines) > 100:
                content = "\n".join(lines[:100]) + f"\n[...{len(lines)-100} lines truncated]"

            parts.append(f"```{path}\n{content}\n```")

        return "\n".join(parts) if parts else "[No content]"

    def _load_arena_prompt_optimized(self, arena: Arena) -> str:
        """Load optimized arena-specific prompt.

        Args:
            arena: Arena to get prompt for

        Returns:
            Optimized arena prompt
        """
        # Map of arena IDs to concise evaluation criteria
        optimized_prompts = {
            "maintainability": """Evaluate: clarity, documentation, conventions, error handling, simplicity, modifiability.
Pick more maintainable solution.""",
            "surgical_precision": """Evaluate: minimal changes, targeted fix, no unrelated modifications.
Pick more surgical solution.""",
            "architecture": """Evaluate: patterns, separation, dependencies, extensibility.
Pick better architecture.""",
            "testability": """Evaluate: isolation, mockability, clear boundaries, determinism.
Pick more testable solution.""",
            "safety": """Evaluate: error handling, input validation, security, edge cases.
Pick safer solution.""",
            "performance": """Evaluate: efficiency, scalability, resource usage, algorithmic complexity.
Pick more performant solution.""",
        }

        # Use optimized prompt if available, otherwise fall back to default
        return optimized_prompts.get(
            arena.name,
            f"Evaluate based on {arena.name} criteria. Pick better solution.",
        )
