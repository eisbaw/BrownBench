#!/usr/bin/env python3
"""Template for creating custom DUT implementations.

This template provides a starting point for implementing your own
Device Under Test (DUT) for code generation benchmarking.

See docs/ADDING_DUTS.md for comprehensive documentation.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach
from codegen_bench.exceptions import DUTAPIError, DUTConfigError, DUTParsingError

logger = structlog.get_logger(__name__)


class CustomDUT(CodeGenerationApproach):
    """Custom code generation approach.

    TODO: Replace with your approach description.

    This DUT demonstrates:
    - Basic configuration handling
    - Solution generation workflow
    - Error handling patterns
    - Metadata computation
    """

    # Unique identifier for this approach
    APPROACH_ID = "custom-dut"

    def __init__(self, config: dict[str, Any]):
        """Initialize custom DUT.

        Args:
            config: Configuration dictionary with your custom parameters.
                   Example:
                   {
                       "model": "your-model-id",
                       "api_key": "your-api-key",
                       "temperature": 0.7,
                       # Add your custom config here
                   }

        Raises:
            DUTConfigError: If configuration is invalid
        """
        super().__init__(config)

        # TODO: Extract and validate your configuration
        self.model = config.get("model", "default-model")
        self.api_key = config.get("api_key")

        if not self.api_key:
            raise DUTConfigError("API key is required")

        # TODO: Initialize your API client, tools, etc.
        # self.client = YourAPIClient(api_key=self.api_key)

        logger.info(
            "custom_dut_initialized",
            model=self.model,
            approach_id=self.APPROACH_ID,
        )

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution for given task.

        This is the main method that implements your code generation logic.

        Args:
            task: Task to solve
            seed: Random seed for reproducibility

        Returns:
            Solution containing generated code

        Raises:
            DUTAPIError: If API calls fail
            DUTParsingError: If response parsing fails
        """
        logger.info(
            "starting_solution_generation",
            dut=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
        )

        try:
            # TODO: Implement your solution generation logic
            #
            # Typical workflow:
            # 1. Build prompt(s) from task specification
            # 2. Call your AI model / code generation system
            # 3. Extract code changes from response
            # 4. Calculate costs and metrics
            #
            # Example:
            import time
            start_time = time.time()

            # Step 1: Build prompt
            prompt = self._build_prompt(task)
            logger.debug("prompt_built", task_id=task.id, prompt_length=len(prompt))

            # Step 2: Call your code generation system
            response = self._generate_code(prompt, seed)

            # Step 3: Extract code changes
            changed_files = self._parse_response(response)
            logger.debug(
                "code_extracted",
                task_id=task.id,
                num_files=len(changed_files),
            )

            # Step 4: Calculate metrics
            elapsed = time.time() - start_time
            cost = self._calculate_cost(response)

            logger.info(
                "solution_generated",
                dut=self.APPROACH_ID,
                task_id=task.id,
                elapsed_seconds=elapsed,
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
                total_tokens=response.get("total_tokens", 0),
                prompt_tokens=response.get("prompt_tokens", 0),
                completion_tokens=response.get("completion_tokens", 0),
                api_calls=response.get("api_calls", 1),
                cost_usd=cost,
            )

        except Exception as e:
            logger.error(
                "solution_generation_failed",
                dut=self.APPROACH_ID,
                task_id=task.id,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Re-raise with appropriate error type
            if "API" in str(type(e)):
                raise DUTAPIError(f"API error for task {task.id}: {e}") from e
            elif "parse" in str(e).lower():
                raise DUTParsingError(f"Parsing error for task {task.id}: {e}") from e
            else:
                raise

    def _build_prompt(self, task: Task) -> str:
        """Build prompt from task specification.

        TODO: Implement your prompt building logic.

        Args:
            task: Task to build prompt for

        Returns:
            Formatted prompt string
        """
        # Example minimal prompt
        return f"""Task: {task.name}

Specification:
{task.specification}

Constraints:
{chr(10).join(f'- {c}' for c in task.constraints)}

Provide the modified code for files: {', '.join(task.key_files)}
"""

    def _generate_code(self, prompt: str, seed: int) -> dict[str, Any]:
        """Call your code generation system.

        TODO: Implement your API call / code generation logic.

        Args:
            prompt: Formatted prompt
            seed: Random seed

        Returns:
            Response dictionary with code and metrics
        """
        # Example placeholder
        return {
            "generated_code": "// Your generated code here",
            "total_tokens": 1000,
            "prompt_tokens": 500,
            "completion_tokens": 500,
            "api_calls": 1,
        }

    def _parse_response(self, response: dict[str, Any]) -> dict[str, str]:
        """Parse code changes from response.

        TODO: Implement response parsing logic.

        Args:
            response: API response

        Returns:
            Dictionary mapping file paths to file contents
        """
        # Example: extract code from markdown blocks
        from codegen_bench.parsing.extractor import CodeExtractor

        generated_code = response.get("generated_code", "")
        return CodeExtractor.extract_all(generated_code)

    def _calculate_cost(self, response: dict[str, Any]) -> float:
        """Calculate cost of generation.

        TODO: Implement cost calculation based on your pricing.

        Args:
            response: Response with token counts

        Returns:
            Cost in USD
        """
        # Example: $0.01 per 1K tokens
        total_tokens = response.get("total_tokens", 0)
        return (total_tokens / 1000) * 0.01

    def get_metadata(self) -> ApproachMetadata:
        """Get DUT metadata.

        This identifies your approach and is used for caching.

        Returns:
            Metadata describing this approach
        """
        # Compute a hash of your prompt for cache invalidation
        # When you change prompts, hash changes, cache invalidates
        sample_task = Task(
            id="sample",
            name="Sample Task",
            project="sample_project",
            domain="sample",
            difficulty="medium",
            codebase_path=Path("/tmp/sample"),
            specification="Sample specification",
            constraints=["Sample constraint"],
            key_files=["sample.py"],
        )

        sample_prompt = self._build_prompt(sample_task)

        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="Custom DUT Name",
            description="Brief description of your approach",
            version="1.0.0",  # Update when you change prompts or logic
            model=self.model,
            provider="your-provider",
            config=self.config,
            prompt_hash=self._compute_prompt_hash(sample_prompt),
        )


# ============================================================================
# Example Usage
# ============================================================================

def main():
    """Example of using CustomDUT."""
    # Configuration
    config = {
        "model": "your-model-id",
        "api_key": "your-api-key",
        "temperature": 0.7,
    }

    # Create DUT
    dut = CustomDUT(config)

    # Load task
    task = Task.from_yaml_file("tasks/core/task_006.yaml")

    # Generate solution
    solution = dut.solve(task, seed=42)

    print(f"Generated {len(solution.changed_files)} files")
    print(f"Cost: ${solution.cost_usd:.4f}")
    print(f"Time: {solution.generation_time_seconds:.1f}s")


if __name__ == "__main__":
    main()
