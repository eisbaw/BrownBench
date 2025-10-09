"""Ground truth data format for judge calibration.

This module defines the format for storing human ground truth judgments
used to calibrate LLM judges.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

JudgmentDecision = Literal["A", "B", "TIE"]


@dataclass(frozen=True)
class ComparisonPair:
    """A single comparison between two solutions.

    Attributes:
        id: Unique identifier for this comparison
        task_id: ID of the task being compared
        arena: Arena used for judgment
        solution_a_id: ID of solution A
        solution_b_id: ID of solution B
        solution_a_text: Text of solution A (optional, for display)
        solution_b_text: Text of solution B (optional, for display)
        ground_truth: Human expert judgment (A, B, or TIE)
        notes: Optional notes about this comparison
    """

    id: str
    task_id: str
    arena: str
    solution_a_id: str
    solution_b_id: str
    ground_truth: JudgmentDecision
    solution_a_text: str | None = None
    solution_b_text: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class GroundTruthDataset:
    """Collection of ground truth comparisons.

    Attributes:
        name: Name of this dataset
        version: Version of the dataset
        description: Description of the dataset
        comparisons: List of comparison pairs
    """

    name: str
    version: str
    description: str
    comparisons: tuple[ComparisonPair, ...]

    @classmethod
    def from_yaml(cls, path: Path) -> "GroundTruthDataset":
        """Load ground truth dataset from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            GroundTruthDataset instance

        Raises:
            ValueError: If YAML format is invalid or missing required fields
            FileNotFoundError: If path does not exist

        Example YAML format:
            name: "calibration-set-v1"
            version: "1.0"
            description: "Initial calibration dataset"
            comparisons:
              - id: "comp001"
                task_id: "task_001"
                arena: "correctness"
                solution_a_id: "simple-chat_001_seed42"
                solution_b_id: "elaborate-prompt_001_seed42"
                ground_truth: "A"
                notes: "Solution A is clearly more correct"
              - id: "comp002"
                ...
        """
        # Load YAML
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {path}: {e}") from e

        # Validate top-level structure
        required_fields = ["name", "version", "description", "comparisons"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(
                f"Missing required fields in {path}: {', '.join(missing)}. "
                f"Expected: {', '.join(required_fields)}"
            )

        if not isinstance(data["comparisons"], list):
            raise ValueError(
                f"'comparisons' must be a list in {path}, got {type(data['comparisons']).__name__}"
            )

        if not data["comparisons"]:
            raise ValueError(f"Dataset {path} must contain at least one comparison")

        # Validate and parse each comparison
        comparisons = []
        required_comp_fields = [
            "id",
            "task_id",
            "arena",
            "solution_a_id",
            "solution_b_id",
            "ground_truth",
        ]

        for i, c in enumerate(data["comparisons"]):
            try:
                # Check required fields
                missing_comp = [f for f in required_comp_fields if f not in c]
                if missing_comp:
                    raise ValueError(f"Missing required fields: {', '.join(missing_comp)}")

                # Validate ground_truth value
                if c["ground_truth"] not in ["A", "B", "TIE"]:
                    raise ValueError(
                        f"Invalid ground_truth value: '{c['ground_truth']}'. Must be 'A', 'B', or 'TIE'"
                    )

                comparisons.append(
                    ComparisonPair(
                        id=c["id"],
                        task_id=c["task_id"],
                        arena=c["arena"],
                        solution_a_id=c["solution_a_id"],
                        solution_b_id=c["solution_b_id"],
                        ground_truth=c["ground_truth"],
                        solution_a_text=c.get("solution_a_text"),
                        solution_b_text=c.get("solution_b_text"),
                        notes=c.get("notes"),
                    )
                )
            except (KeyError, ValueError) as e:
                raise ValueError(f"Invalid comparison at index {i} in {path}: {e}") from e

        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            comparisons=tuple(comparisons),  # Use tuple for immutability
        )

    def to_yaml(self, path: Path) -> None:
        """Save ground truth dataset to YAML file.

        Args:
            path: Path to save YAML file
        """
        data = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "comparisons": [
                {
                    "id": c.id,
                    "task_id": c.task_id,
                    "arena": c.arena,
                    "solution_a_id": c.solution_a_id,
                    "solution_b_id": c.solution_b_id,
                    "ground_truth": c.ground_truth,
                    "solution_a_text": c.solution_a_text,
                    "solution_b_text": c.solution_b_text,
                    "notes": c.notes,
                }
                for c in self.comparisons
            ],
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
