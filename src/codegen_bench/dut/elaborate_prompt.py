"""ElaboratePromptDUT - Enhanced prompting with best practices."""

from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata
from codegen_bench.dut.simple_chat import SimpleChatDUT


class ElaboratePromptDUT(SimpleChatDUT):
    """Code generation with enhanced system prompt and best practices."""

    APPROACH_ID = "elaborate-prompt"

    def _build_prompt(self, task: Task) -> str:
        """Build elaborate prompt with architectural analysis.

        Args:
            task: Task to solve

        Returns:
            Detailed prompt with context and best practices
        """
        system_prompt = """You are an expert software engineer with 15+ years of experience.
You are working on production code that will be maintained for years.

CRITICAL PRINCIPLES:
1. MAINTAINABILITY: Code must be crystal clear and well-documented
2. CORRECTNESS: All requirements and constraints must be satisfied
3. ROBUSTNESS: Handle edge cases and errors gracefully
4. INTEGRATION: Match existing patterns and conventions exactly

WORKFLOW:
1. Read and understand the specification completely
2. Identify all constraints and gotchas
3. Plan minimal changes that satisfy requirements
4. Write production-ready code with proper error handling
5. Ensure all tests will pass

OUTPUT FORMAT:
Provide code in markdown blocks with file paths:
```language:path/to/file.ext
code content here
```

Your solution must be complete, tested, and production-ready."""

        # Build comprehensive task description
        constraints_text = "\n".join(f"  - {c}" for c in task.constraints)
        gotchas_text = "\n".join(f"  - {g}" for g in task.gotchas) if task.gotchas else "  - None"
        key_files_text = ", ".join(task.key_files) if task.key_files else "None specified"

        prompt = f"""{system_prompt}

## TASK: {task.name}

### Specification
{task.specification}

### Constraints (MUST satisfy)
{constraints_text}

### Key Files to Modify
{key_files_text}

### Known Gotchas
{gotchas_text}

### Expected Approach
- Analyze the requirement carefully
- Check existing code patterns (if any)
- Implement the minimal change that satisfies all constraints
- Ensure edge cases are handled
- Make sure tests will pass

Provide your complete implementation now.
"""
        return prompt

    def get_metadata(self) -> ApproachMetadata:
        """Get DUT metadata.

        Returns:
            Metadata describing this approach
        """
        return ApproachMetadata(
            id="elaborate-prompt",
            name="Elaborate Prompt",
            description="Enhanced system prompt with best practices and context",
            version="1.0.0",
            model=self.model,
            provider="anthropic",
            config=self.config,
        )
