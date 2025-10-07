"""Arena (quality dimension) for evaluation."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Arena:
    """A quality dimension for evaluation."""

    name: str
    display_name: str
    description: str
    criteria: list[str]
    prompt_template_path: Path

    def load_prompt(self, **kwargs: str) -> str:
        """Load and format prompt template.

        Loads the prompt template from the package resources,
        resolving the path relative to the codegen_bench package.
        """
        # Convert relative path to absolute by resolving from package
        if not self.prompt_template_path.is_absolute():
            import codegen_bench
            pkg_dir = Path(codegen_bench.__file__).parent
            template_path = pkg_dir / self.prompt_template_path
        else:
            template_path = self.prompt_template_path

        with open(template_path) as f:
            template = f.read()
        return template.format(**kwargs)


# Built-in arenas (will be defined with actual prompts later)
MAINTAINABILITY = Arena(
    name="maintainability",
    display_name="Maintainability",
    description="Code clarity, documentation, conventions",
    criteria=[
        "Code is easy to read and understand",
        "Documentation is clear and helpful",
        "Follows existing conventions",
        "Error handling is robust",
    ],
    prompt_template_path=Path("judge/prompts/maintainability.txt"),
)

ARCHITECTURAL_INTEGRITY = Arena(
    name="architecture",
    display_name="Architectural Integrity",
    description="Respects existing patterns and abstractions",
    criteria=[
        "Respects existing architectural patterns",
        "Minimizes coupling",
        "Preserves abstractions",
        "Fits the mental model",
    ],
    prompt_template_path=Path("judge/prompts/architecture.txt"),
)

SURGICAL_PRECISION = Arena(
    name="surgical",
    display_name="Surgical Precision",
    description="Minimal blast radius",
    criteria=[
        "Only changes what's needed",
        "Avoids unnecessary refactoring",
        "Low side effects",
        "Minimal blast radius",
    ],
    prompt_template_path=Path("judge/prompts/surgical_precision.txt"),
)

TESTABILITY = Arena(
    name="testability",
    display_name="Testability",
    description="Test coverage and quality",
    criteria=[
        "Test coverage is adequate",
        "Tests are non-brittle",
        "Edge cases covered",
        "Meaningful assertions",
    ],
    prompt_template_path=Path("judge/prompts/testability.txt"),
)

PERFORMANCE = Arena(
    name="performance",
    display_name="Performance Awareness",
    description="Hot path and algorithmic considerations",
    criteria=[
        "Hot path considerations",
        "Algorithmic complexity",
        "Memory efficiency",
        "Cache-friendliness",
    ],
    prompt_template_path=Path("judge/prompts/performance.txt"),
)

SAFETY = Arena(
    name="safety",
    display_name="Safety & Correctness",
    description="Error handling and resource management",
    criteria=[
        "Error handling completeness",
        "Resource cleanup",
        "Thread safety",
        "Undefined behavior risks",
    ],
    prompt_template_path=Path("judge/prompts/safety.txt"),
)

ALL_ARENAS = [
    MAINTAINABILITY,
    ARCHITECTURAL_INTEGRITY,
    SURGICAL_PRECISION,
    TESTABILITY,
    PERFORMANCE,
    SAFETY,
]
