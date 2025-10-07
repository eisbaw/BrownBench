"""Task dataclass with validation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass
class Task:
    """A single benchmark task."""

    id: str
    name: str
    project: str
    domain: str
    difficulty: Literal["easy", "medium", "hard"]

    # Context
    codebase_path: Path
    specification: str
    constraints: list[str] = field(default_factory=list)

    # Validation
    test_suite_path: Path | None = None
    # SECURITY NOTE: Commands are parsed with shlex.split() and executed with shell=False
    # to prevent shell injection. Use simple command syntax: "make test" or "pytest tests/"
    # Shell features like pipes (|), redirects (>), or command chaining (&&) are NOT supported.
    compile_command: str | None = None
    test_command: str | None = None

    # Metadata
    expected_human_time_minutes: int = 0
    key_files: list[str] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)

    # Reference solution (for metrics)
    reference_solution_path: Path | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> "Task":
        """Load task from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        # Convert path strings to Path objects
        if "codebase_path" in data:
            data["codebase_path"] = Path(data["codebase_path"])
        if "test_suite_path" in data:
            data["test_suite_path"] = Path(data["test_suite_path"])
        if "reference_solution_path" in data:
            data["reference_solution_path"] = Path(data["reference_solution_path"])

        return cls(**data)

    def validate(self) -> bool:
        """Validate task structure."""
        # Check required fields
        if not self.id or not self.name:
            return False

        # Check codebase path exists
        if not self.codebase_path.exists():
            return False

        # Check test suite if specified
        if self.test_suite_path and not self.test_suite_path.exists():
            return False

        # Check reference solution if specified
        if self.reference_solution_path and not self.reference_solution_path.exists():
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "name": self.name,
            "project": self.project,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "codebase_path": str(self.codebase_path),
            "specification": self.specification,
            "constraints": self.constraints,
            "test_suite_path": str(self.test_suite_path) if self.test_suite_path else None,
            "compile_command": self.compile_command,
            "test_command": self.test_command,
            "expected_human_time_minutes": self.expected_human_time_minutes,
            "key_files": self.key_files,
            "gotchas": self.gotchas,
            "reference_solution_path": (
                str(self.reference_solution_path) if self.reference_solution_path else None
            ),
        }
