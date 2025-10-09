"""OptimizedPromptDUT - Token-efficient prompting approach."""

from typing import Any

from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata
from codegen_bench.dut.simple_chat import SimpleChatDUT


class OptimizedPromptDUT(SimpleChatDUT):
    """Token-efficient DUT with optimized prompts.

    This DUT reduces token usage by:
    - Removing redundant instructions
    - Using concise language
    - Eliminating verbose examples
    - Focusing on essential information only

    Token reduction: ~40-50% compared to ElaboratePromptDUT
    """

    APPROACH_ID = "optimized-prompt"

    def _build_prompt(self, task: Task) -> str:
        """Build token-efficient prompt.

        Args:
            task: Task to solve

        Returns:
            Optimized prompt
        """
        # Concise system instructions (reduced from ~600 tokens to ~200)
        system = """BROWNFIELD CODE CHANGE

RULES:
1. Minimal change only - don't refactor unrelated code
2. Match existing style/patterns exactly
3. Keep backward compatibility
4. Preserve all tests

AVOID: Over-engineering, new patterns, breaking changes

OUTPUT: Complete files in markdown blocks with paths"""

        # Build compact task description
        constraints = "\n".join(f"- {c}" for c in task.constraints)

        # Key files only if specified
        files = f"\nFiles: {', '.join(task.key_files)}" if task.key_files else ""

        # Warnings only if present
        gotchas = ""
        if task.gotchas:
            gotchas = f"\nWarnings:\n" + "\n".join(f"- {g}" for g in task.gotchas)

        # Compact prompt structure
        prompt = f"""{system}

TASK: {task.name}
Project: {task.project} ({task.domain})
{files}

SPEC:
{task.specification}

CONSTRAINTS:
{constraints}{gotchas}

Implement now."""

        return prompt

    def get_metadata(self) -> ApproachMetadata:
        """Get DUT metadata.

        Returns:
            Metadata describing this approach
        """
        # Generate sample prompt for hash
        from pathlib import Path

        sample_task = Task(
            id="sample",
            name="sample",
            project="sample_project",
            domain="sample",
            difficulty="medium",
            codebase_path=Path("/tmp/sample"),
            specification="sample spec",
            constraints=["constraint1"],
            gotchas=["gotcha1"],
            key_files=["file.py"],
        )
        prompt = self._build_prompt(sample_task)

        return ApproachMetadata(
            id="optimized-prompt",
            name="Optimized Token-Efficient Prompt",
            description="Reduces token usage by 40-50% while maintaining effectiveness",
            version="1.0.0",
            model=self.model,
            provider="anthropic",
            config=self.config,
            prompt_hash=self._compute_prompt_hash(prompt),
        )
