"""Simple chat-based DUT implementation using Anthropic's Claude."""

import os
import time
from datetime import datetime, timezone

import anthropic

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach


class SimpleChatDUT(CodeGenerationApproach):
    """Single-turn chat with minimal prompting using Claude."""

    def __init__(self, config: dict):
        """Initialize SimpleChatDUT.

        Args:
            config: Configuration dict with keys:
                - model: Claude model to use (default: claude-sonnet-4-20250514)
                - api_key: Anthropic API key (optional, falls back to env var)
                - max_tokens: Max tokens for response (default: 8000)
                - temperature: Sampling temperature (default: 0.3)
        """
        super().__init__(config)
        self.model = config.get("model", "claude-sonnet-4-20250514")
        api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in config or environment")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.max_tokens = config.get("max_tokens", 8000)
        self.temperature = config.get("temperature", 0.3)

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution with simple prompt.

        Args:
            task: Task to solve
            seed: Random seed (note: Claude API may not be fully deterministic)

        Returns:
            Solution with generated code
        """
        start_time = time.time()

        # Build simple prompt
        prompt = self._build_prompt(task)

        # Single API call
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        elapsed = time.time() - start_time

        # Parse response to extract code changes
        changed_files = self._parse_code_changes(response.content[0].text)

        # Calculate cost
        cost = self._calculate_cost(
            response.usage.input_tokens, response.usage.output_tokens
        )

        return Solution(
            approach_id=self.get_metadata().id,
            task_id=task.id,
            seed=seed,
            timestamp=datetime.now(timezone.utc),
            changed_files=changed_files,
            generation_time_seconds=elapsed,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            api_calls=1,
            cost_usd=cost,
        )

    def _build_prompt(self, task: Task) -> str:
        """Build minimal prompt for task.

        Args:
            task: Task to build prompt for

        Returns:
            Formatted prompt string
        """
        constraints_text = "\n".join(f"- {c}" for c in task.constraints)

        return f"""You are a software engineer. Implement the following change:

Task: {task.name}

Specification:
{task.specification}

Constraints:
{constraints_text}

Key files to modify: {', '.join(task.key_files)}

Provide the modified code for each file that needs to change.
Format your response with code blocks like:

```language:path/to/file.ext
code content here
```

For example:
```c:src/main.c
int main() {{
    return 0;
}}
```
"""

    def _parse_code_changes(self, response: str) -> dict[str, str]:
        """Extract file changes from response.

        Parses code blocks in the format:
        ```language:path/to/file.ext
        code content
        ```

        Args:
            response: LLM response text

        Returns:
            Dictionary mapping file paths to file contents
        """
        changed_files = {}
        lines = response.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            # Look for code block start with file path
            if line.startswith("```") and ":" in line:
                # Extract language and path
                parts = line[3:].split(":", 1)
                if len(parts) == 2:
                    path = parts[1].strip()
                    # Collect code until closing ```
                    code_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith("```"):
                        code_lines.append(lines[i])
                        i += 1
                    changed_files[path] = "\n".join(code_lines)
            i += 1

        return changed_files

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost based on token usage.

        Uses pricing as of October 2025:
        - Claude Sonnet 4.5: $3/M input, $15/M output

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        # Default pricing for Claude Sonnet 4.5
        input_cost_per_1k = 0.003
        output_cost_per_1k = 0.015

        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k

        return input_cost + output_cost

    def get_metadata(self) -> ApproachMetadata:
        """Return approach metadata.

        Returns:
            ApproachMetadata for this DUT
        """
        return ApproachMetadata(
            id="simple-chat",
            name="Simple Chat",
            description="Single-turn chat with minimal prompting",
            version="1.0.0",
            model=self.model,
            provider="anthropic",
            config=self.config,
        )
