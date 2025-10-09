"""ElaboratePromptDUT - Enhanced prompting with best practices."""

from pathlib import Path
from typing import Any

from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata
from codegen_bench.dut.simple_chat import SimpleChatDUT


class ElaboratePromptDUT(SimpleChatDUT):
    """Code generation with enhanced system prompt and best practices.

    This DUT extends SimpleChatDUT with:
    - Enhanced system prompt focused on brownfield refactoring
    - Codebase context analysis (reads relevant files)
    - Architectural guidance for production code
    """

    APPROACH_ID = "elaborate-prompt"

    def __init__(self, config: dict[str, Any]):
        """Initialize ElaboratePromptDUT.

        Args:
            config: Configuration dictionary with optional keys:
                - include_codebase_context: Whether to read existing files (default: True)
                - max_context_files: Maximum files to include in context (default: 5)
                - timeout_seconds: Timeout for solve() in seconds (default: 300)
                - All SimpleChatDUT config options (model, api_key, max_tokens, etc.)
        """
        super().__init__(config)
        self.include_codebase_context = config.get("include_codebase_context", True)
        self.max_context_files = config.get("max_context_files", 5)

    def _read_file_safely(self, file_path: Path, max_lines: int = 200) -> str:
        """Read file content safely with error handling.

        Args:
            file_path: Path to file to read
            max_lines: Maximum lines to read

        Returns:
            File content or error message
        """
        try:
            if not file_path.exists():
                return f"[File not found: {file_path}]"

            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[:max_lines]
                content = "".join(lines)

            if len(lines) == max_lines:
                content += f"\n... (truncated, showing first {max_lines} lines)"

            return content
        except Exception as e:
            return f"[Error reading {file_path}: {e}]"

    def _get_codebase_context(self, task: Task) -> str:
        """Get relevant codebase context by reading key files.

        Args:
            task: Task with key_files to analyze

        Returns:
            Formatted codebase context or empty string
        """
        if not self.include_codebase_context or not task.key_files:
            return ""

        context_parts = ["\n## CODEBASE CONTEXT\n"]
        context_parts.append(
            "Here are the current versions of the key files you'll be modifying:\n"
        )

        files_to_read = task.key_files[: self.max_context_files]

        for file_path_str in files_to_read:
            file_path = task.codebase_path / file_path_str
            content = self._read_file_safely(file_path)

            context_parts.append(f"\n### {file_path_str}\n")
            context_parts.append(f"```\n{content}\n```\n")

        if len(task.key_files) > self.max_context_files:
            remaining = len(task.key_files) - self.max_context_files
            context_parts.append(
                f"\n(Plus {remaining} more files not shown - focus on the above)\n"
            )

        return "".join(context_parts)

    def _build_prompt(self, task: Task) -> str:
        """Build elaborate prompt with architectural analysis.

        Args:
            task: Task to solve

        Returns:
            Detailed prompt with context and best practices
        """
        system_prompt = """You are a senior software engineer working on a BROWNFIELD codebase.
This is production code that has been running for years and is maintained by a team.

CONTEXT: You're making a surgical change to existing code - not building from scratch.
Your change will be reviewed and must meet high standards for integration with existing patterns.

CRITICAL PRINCIPLES FOR BROWNFIELD DEVELOPMENT:
1. **SURGICAL PRECISION**: Make the MINIMUM change needed - don't refactor unrelated code
2. **PATTERN MATCHING**: Follow existing conventions exactly (naming, style, error handling)
3. **BACKWARD COMPATIBILITY**: Don't break existing APIs or behavior
4. **TEST PRESERVATION**: All existing tests must continue to pass
5. **INTEGRATION**: Your code should look like it was written by the original authors

ANTI-PATTERNS TO AVOID:
- Over-engineering or adding unnecessary abstractions
- Changing unrelated code "while you're there"
- Introducing new patterns inconsistent with the codebase
- Breaking backward compatibility for convenience
- Ignoring existing error handling patterns

WORKFLOW:
1. **Analyze existing code**: Study patterns, naming, structure
2. **Understand the change**: What's the minimal diff needed?
3. **Match the style**: Use same patterns, naming conventions, error handling
4. **Preserve tests**: Ensure all tests pass with your change
5. **Review constraints**: Double-check all requirements are met

OUTPUT FORMAT:
Provide complete file contents in markdown blocks with file paths:
```language:path/to/file.ext
complete file content here
```

Your change should be indistinguishable from code written by the original developers."""

        # Build comprehensive task description
        constraints_text = "\n".join(f"  - {c}" for c in task.constraints)
        gotchas_text = "\n".join(f"  - {g}" for g in task.gotchas) if task.gotchas else "  - None"
        key_files_text = ", ".join(task.key_files) if task.key_files else "None specified"

        # Get codebase context if enabled
        codebase_context = self._get_codebase_context(task)

        prompt = f"""{system_prompt}

## TASK: {task.name}

### Project Context
- **Project**: {task.project}
- **Domain**: {task.domain}
- **Difficulty**: {task.difficulty}
- **Codebase**: {task.codebase_path}

### Specification
{task.specification}

### Constraints (MUST satisfy)
{constraints_text}

### Key Files to Modify
{key_files_text}

### Known Gotchas & Warnings
{gotchas_text}
{codebase_context}

### Your Task
1. Study the existing code above to understand patterns and conventions
2. Implement the specification with MINIMAL changes
3. Match existing style, naming, error handling exactly
4. Ensure all existing tests continue to pass
5. Provide complete file contents for each modified file

Provide your complete implementation now.
"""
        return prompt

    def get_metadata(self) -> ApproachMetadata:
        """Get DUT metadata.

        Returns:
            Metadata describing this approach
        """
        # Compute prompt hash from template
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
            id="elaborate-prompt",
            name="Elaborate Prompt with Codebase Context",
            description="Enhanced system prompt focused on brownfield refactoring with codebase analysis",
            version="2.0.0",
            model=self.model,
            provider="anthropic",
            config=self.config,
            prompt_hash=self._compute_prompt_hash(prompt),
        )
