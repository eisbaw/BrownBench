"""Simple chat-based DUT implementation using Anthropic's Claude."""

import os
import time
from datetime import UTC, datetime
from typing import Any

import anthropic
import structlog
from anthropic.types import TextBlock

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach
from codegen_bench.exceptions import DUTError
from codegen_bench.parsing.extractor import CodeExtractor

logger = structlog.get_logger(__name__)

# Pricing for Claude Sonnet 4.5 (as of January 2025)
# Source: https://www.anthropic.com/pricing
CLAUDE_SONNET_4_5_INPUT_COST_PER_1K_TOKENS = 0.003  # $3.00 per million tokens
CLAUDE_SONNET_4_5_OUTPUT_COST_PER_1K_TOKENS = 0.015  # $15.00 per million tokens


class SimpleChatDUT(CodeGenerationApproach):
    """Single-turn chat with minimal prompting using Claude."""

    APPROACH_ID = "simple-chat"
    client: anthropic.Anthropic

    def __init__(self, config: dict[str, Any]):
        """Initialize SimpleChatDUT.

        Args:
            config: Configuration dict with keys:
                - model: Claude model to use (default: claude-sonnet-4-20250514)
                - api_key: Anthropic API key (optional, falls back to env var)
                - max_tokens: Max tokens for response (default: 8000)
                - temperature: Sampling temperature (default: 0.3)

        Raises:
            DUTError: If API key not found
        """
        super().__init__(config)
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise DUTError("ANTHROPIC_API_KEY not found in config or environment")
        self.client = anthropic.Anthropic(api_key=self.api_key)
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
        logger.info(
            "starting_solution_generation",
            dut=self.get_metadata().id,
            task_id=task.id,
            seed=seed,
            model=self.model,
        )

        try:
            start_time = time.time()

            # Build simple prompt
            prompt = self._build_prompt(task)
            logger.debug("prompt_built", task_id=task.id, prompt_length=len(prompt))

            # Single API call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            elapsed = time.time() - start_time

            # Parse response to extract code changes - extract text from first content block
            first_block = response.content[0]
            if isinstance(first_block, TextBlock):
                response_text = first_block.text
            else:
                raise DUTError(f"Unexpected response type: {type(first_block)}")

            changed_files = self._parse_code_changes(response_text)
            logger.debug(
                "code_extracted",
                task_id=task.id,
                num_files=len(changed_files),
                files=list(changed_files.keys()),
            )

            # Calculate cost
            cost = self._calculate_cost(response.usage.input_tokens, response.usage.output_tokens)

            logger.info(
                "solution_generated",
                dut=self.get_metadata().id,
                task_id=task.id,
                seed=seed,
                elapsed_seconds=elapsed,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cost_usd=cost,
                num_files=len(changed_files),
            )

            return Solution(
                approach_id=self.get_metadata().id,
                task_id=task.id,
                seed=seed,
                timestamp=datetime.now(UTC),
                changed_files=changed_files,
                generation_time_seconds=elapsed,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                api_calls=1,
                cost_usd=cost,
            )
        except anthropic.APIError as e:
            logger.error(
                "api_error",
                dut=self.get_metadata().id,
                task_id=task.id,
                seed=seed,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DUTError(f"API call failed for task {task.id}: {e}") from e
        except (KeyError, AttributeError, ValueError) as e:
            logger.error(
                "response_parsing_failed",
                dut=self.get_metadata().id,
                task_id=task.id,
                seed=seed,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DUTError(f"Failed to parse API response for task {task.id}: {e}") from e

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

        Uses CodeExtractor to support multiple formats.

        Args:
            response: LLM response text

        Returns:
            Dictionary mapping file paths to file contents
        """
        return CodeExtractor.extract_all(response)

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
        input_cost = (input_tokens / 1000) * CLAUDE_SONNET_4_5_INPUT_COST_PER_1K_TOKENS
        output_cost = (output_tokens / 1000) * CLAUDE_SONNET_4_5_OUTPUT_COST_PER_1K_TOKENS

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
