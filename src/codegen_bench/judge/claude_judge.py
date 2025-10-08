"""Claude-based judge implementation."""

import os
import re

import anthropic
from anthropic.types import TextBlock
from tenacity import retry, stop_after_attempt, wait_exponential

from codegen_bench.core.arena import Arena
from codegen_bench.core.judgment import JudgeVote, Vote
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.exceptions import JudgeError
from codegen_bench.judge.base import Judge
from codegen_bench.utils.rate_limiter import RateLimiter


class ClaudeJudge(Judge):
    """Claude-based judge for comparing solutions."""

    client: anthropic.Anthropic
    rate_limiter: RateLimiter

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.3,
        variant: int = 0,
        max_requests_per_minute: int = 50,
    ):
        """Initialize ClaudeJudge.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            temperature: Sampling temperature
            variant: Prompt variant for diversity
            max_requests_per_minute: Rate limit for API calls

        Raises:
            JudgeError: If API key not found
        """
        super().__init__(model, temperature, variant)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise JudgeError("ANTHROPIC_API_KEY not found in environment or config")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.rate_limiter = RateLimiter(max_requests_per_minute=max_requests_per_minute)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def evaluate(
        self, solution_a: Solution, solution_b: Solution, arena: Arena, task: Task
    ) -> JudgeVote:
        """Evaluate two solutions using Claude.

        Args:
            solution_a: First solution
            solution_b: Second solution
            arena: Arena to evaluate in
            task: Task being solved

        Returns:
            JudgeVote with winner, reasoning, and confidence
        """
        # Build prompt
        prompt = self._build_prompt(solution_a, solution_b, arena, task)

        # Apply rate limiting before API call
        self.rate_limiter.acquire()

        # Call API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response - extract text from first content block
        first_block = response.content[0]
        if isinstance(first_block, TextBlock):
            response_text = first_block.text
        else:
            raise JudgeError(f"Unexpected response type: {type(first_block)}")

        return self._parse_vote(response_text)

    def _build_prompt(
        self, solution_a: Solution, solution_b: Solution, arena: Arena, task: Task
    ) -> str:
        """Build evaluation prompt.

        Args:
            solution_a: First solution
            solution_b: Second solution
            arena: Arena to evaluate in
            task: Task being solved

        Returns:
            Formatted prompt string
        """
        # Load arena-specific prompt template
        arena_criteria = "\n".join(f"- {c}" for c in arena.criteria)

        solution_a_text = self._format_solution(solution_a)
        solution_b_text = self._format_solution(solution_b)

        return f"""You are an expert code reviewer evaluating two solutions to a programming task.

Task: {task.name}

Specification:
{task.specification}

Constraints:
{chr(10).join(f"- {c}" for c in task.constraints)}

Evaluation Criteria ({arena.display_name}):
{arena.description}

{arena_criteria}

Solution A:
{solution_a_text}

Solution B:
{solution_b_text}

Compare these two solutions based on the criteria above. Which solution is better?

Respond in the following format:
WINNER: A|B|TIE
REASONING: <2-3 sentences explaining your decision>
CONFIDENCE: <0.0-1.0, where 1.0 is completely certain>

Be objective and focus on the quality dimensions specified in the criteria.
"""

    def _format_solution(self, solution: Solution) -> str:
        """Format solution for display in prompt.

        Args:
            solution: Solution to format

        Returns:
            Formatted string showing file changes
        """
        if not solution.changed_files:
            return "(No files changed)"

        parts = []
        for path, content in solution.changed_files.items():
            parts.append(f"File: {path}")
            parts.append("```")
            parts.append(content)
            parts.append("```")
            parts.append("")

        return "\n".join(parts)

    def _parse_vote(self, response: str) -> JudgeVote:
        """Parse judge response into JudgeVote.

        Args:
            response: Raw judge response

        Returns:
            Parsed JudgeVote

        Raises:
            ValueError: If response format is invalid
        """
        # Extract WINNER
        winner_match = re.search(r"WINNER:\s*(A|B|TIE)", response, re.IGNORECASE)
        if not winner_match:
            raise JudgeError(f"Could not parse WINNER from response: {response}")
        winner_str = winner_match.group(1).upper()

        # Extract REASONING
        reasoning_match = re.search(
            r"REASONING:\s*(.+?)(?=CONFIDENCE:|$)", response, re.IGNORECASE | re.DOTALL
        )
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        # Extract CONFIDENCE
        confidence_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", response, re.IGNORECASE)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5

        # Validate winner and cast to Vote type (type narrowing for mypy)
        winner: Vote
        if winner_str == "A":
            winner = "A"
        elif winner_str == "B":
            winner = "B"
        elif winner_str == "TIE":
            winner = "TIE"
        else:
            raise JudgeError(f"Invalid winner: {winner_str}")

        return JudgeVote(vote=winner, reasoning=reasoning, confidence=confidence)
