"""Pre-registration system for analysis plans.

Pre-registration prevents p-hacking and HARKing (Hypothesizing After Results Known)
by documenting hypotheses, methods, and stopping rules before data collection.

This follows Open Science Framework (OSF) standards and best practices from
clinical trial pre-registration.

References:
- Nosek et al. (2018): "The preregistration revolution"
- ClinicalTrials.gov registration standards
- AsPredicted.org templates
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass
class Hypothesis:
    """A testable hypothesis.

    Attributes:
        id: Unique identifier (e.g., "H1", "H2")
        description: Natural language description
        direction: Directional expectation ('greater', 'less', 'two-sided')
        variables: Variables involved (e.g., {"treatment": "dut1", "control": "baseline"})
        primary: Whether this is a primary hypothesis
    """

    id: str
    description: str
    direction: Literal["greater", "less", "two-sided"]
    variables: dict[str, str] = field(default_factory=dict)
    primary: bool = False


@dataclass
class OutcomeMeasure:
    """An outcome measure to be analyzed.

    Attributes:
        name: Measure name (e.g., "correctness", "maintainability")
        metric: How it's measured (e.g., "test_pass_rate", "elo_rating")
        primary: Whether this is the primary outcome
        arena: Which arena this belongs to (optional)
    """

    name: str
    metric: str
    primary: bool = False
    arena: str | None = None


@dataclass
class StoppingRule:
    """Early stopping criteria.

    Attributes:
        rule_type: Type of stopping rule ('sequential', 'futility', 'efficacy', 'budget')
        parameters: Rule-specific parameters
        description: Natural language description
    """

    rule_type: Literal["sequential", "futility", "efficacy", "budget", "custom"]
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ExclusionCriteria:
    """Data exclusion criteria.

    Attributes:
        criterion: Type of exclusion ('timeout', 'compilation_failure', 'api_error', 'custom')
        description: Natural language description
        apply_before_unblinding: Whether to apply before seeing results
    """

    criterion: str
    description: str
    apply_before_unblinding: bool = True


@dataclass
class PreregistrationPlan:
    """Complete pre-registration plan.

    Attributes:
        title: Study title
        research_question: Main research question
        hypotheses: List of hypotheses
        primary_outcome: Primary outcome measure
        secondary_outcomes: Secondary outcome measures
        sample_size: Planned sample size
        sample_size_justification: Power analysis or other justification
        duts: List of DUT IDs to compare
        tasks: Task set to use
        arenas: Arenas to evaluate
        alpha: Significance level
        power: Target statistical power
        correction_method: Multiple testing correction method
        rating_system: Rating system to use
        stopping_rules: Early stopping rules
        exclusion_criteria: Data exclusion criteria
        timestamp: When plan was created (auto-generated)
        plan_hash: SHA-256 hash for verification (auto-generated)
        osf_url: Optional OSF pre-registration URL
        notes: Additional notes
    """

    title: str
    research_question: str
    hypotheses: list[Hypothesis]
    primary_outcome: OutcomeMeasure
    secondary_outcomes: list[OutcomeMeasure]
    sample_size: int
    sample_size_justification: str
    duts: list[str]
    tasks: str
    arenas: list[str]
    alpha: float = 0.05
    power: float = 0.80
    correction_method: str = "fdr_bh"
    rating_system: str = "trueskill"
    stopping_rules: list[StoppingRule] = field(default_factory=list)
    exclusion_criteria: list[ExclusionCriteria] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    plan_hash: str = field(default="", init=False)
    osf_url: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        """Generate hash after initialization."""
        self.plan_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of plan content for verification."""
        # Serialize to dict, excluding hash and timestamp for reproducibility
        plan_dict = asdict(self)
        plan_dict.pop("plan_hash", None)
        plan_dict.pop("timestamp", None)

        # Sort keys for deterministic hashing
        plan_json = json.dumps(plan_dict, sort_keys=True)
        hash_digest = hashlib.sha256(plan_json.encode()).hexdigest()

        return hash_digest[:16]  # First 16 chars for readability

    def to_yaml(self, path: Path) -> None:
        """Save plan to YAML file.

        Args:
            path: Output path for YAML file
        """
        plan_dict = asdict(self)

        # Add header comment
        header = f"""# Pre-registration Plan
# Generated: {self.timestamp}
# Hash: {self.plan_hash}
# DO NOT MODIFY - Any changes invalidate the hash

"""

        with open(path, "w") as f:
            f.write(header)
            yaml.dump(plan_dict, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, path: Path) -> "PreregistrationPlan":
        """Load plan from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            PreregistrationPlan instance

        Raises:
            ValueError: If file format is invalid
        """
        with open(path) as f:
            # Skip comment lines
            lines = [line for line in f if not line.strip().startswith("#")]
            yaml_content = "".join(lines)

        data = yaml.safe_load(yaml_content)

        # Reconstruct nested dataclasses
        hypotheses = [Hypothesis(**h) for h in data.get("hypotheses", [])]

        primary_outcome_data = data.get("primary_outcome", {})
        primary_outcome = OutcomeMeasure(**primary_outcome_data)

        secondary_outcomes = [OutcomeMeasure(**s) for s in data.get("secondary_outcomes", [])]

        stopping_rules = [StoppingRule(**r) for r in data.get("stopping_rules", [])]

        exclusion_criteria = [ExclusionCriteria(**e) for e in data.get("exclusion_criteria", [])]

        # Create plan
        plan = cls(
            title=data["title"],
            research_question=data["research_question"],
            hypotheses=hypotheses,
            primary_outcome=primary_outcome,
            secondary_outcomes=secondary_outcomes,
            sample_size=data["sample_size"],
            sample_size_justification=data["sample_size_justification"],
            duts=data["duts"],
            tasks=data["tasks"],
            arenas=data["arenas"],
            alpha=data.get("alpha", 0.05),
            power=data.get("power", 0.80),
            correction_method=data.get("correction_method", "fdr_bh"),
            rating_system=data.get("rating_system", "trueskill"),
            stopping_rules=stopping_rules,
            exclusion_criteria=exclusion_criteria,
            timestamp=data.get("timestamp", ""),
            osf_url=data.get("osf_url"),
            notes=data.get("notes", ""),
        )

        return plan

    def verify_hash(self, expected_hash: str) -> bool:
        """Verify plan hash matches expected value.

        Args:
            expected_hash: Expected hash value

        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = self._compute_hash()
        return actual_hash == expected_hash

    def verify_adherence(self, tournament_config: dict[str, Any]) -> dict[str, Any]:
        """Verify tournament configuration adheres to pre-registered plan.

        Args:
            tournament_config: Actual tournament configuration

        Returns:
            Dictionary with verification results and any deviations
        """
        deviations = []

        # Check DUTs
        planned_duts = set(self.duts)
        actual_duts = set(tournament_config.get("duts", []))
        if planned_duts != actual_duts:
            deviations.append(
                {
                    "field": "duts",
                    "planned": list(planned_duts),
                    "actual": list(actual_duts),
                    "severity": "major",
                }
            )

        # Check sample size
        actual_sample_size = tournament_config.get("sample_size", 0)
        if actual_sample_size < self.sample_size:
            deviations.append(
                {
                    "field": "sample_size",
                    "planned": [self.sample_size],
                    "actual": [actual_sample_size],
                    "severity": "major",
                }
            )

        # Check alpha
        actual_alpha = tournament_config.get("alpha", 0.05)
        if actual_alpha != self.alpha:
            deviations.append(
                {
                    "field": "alpha",
                    "planned": [self.alpha],
                    "actual": [actual_alpha],
                    "severity": "major",
                }
            )

        # Check correction method
        actual_correction = tournament_config.get("correction_method", "")
        if actual_correction != self.correction_method:
            deviations.append(
                {
                    "field": "correction_method",
                    "planned": self.correction_method,
                    "actual": actual_correction,
                    "severity": "minor",
                }
            )

        # Check arenas
        planned_arenas = set(self.arenas)
        actual_arenas = set(tournament_config.get("arenas", []))
        if planned_arenas != actual_arenas:
            deviations.append(
                {
                    "field": "arenas",
                    "planned": list(planned_arenas),
                    "actual": list(actual_arenas),
                    "severity": "minor",
                }
            )

        return {
            "adheres": len(deviations) == 0,
            "deviations": deviations,
            "major_deviations": sum(1 for d in deviations if d["severity"] == "major"),
            "minor_deviations": sum(1 for d in deviations if d["severity"] == "minor"),
        }

    def generate_report(self) -> str:
        """Generate human-readable report of pre-registration plan.

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 80,
            "PRE-REGISTRATION PLAN",
            "=" * 80,
            "",
            f"Title: {self.title}",
            f"Timestamp: {self.timestamp}",
            f"Hash: {self.plan_hash}",
            "",
            "RESEARCH QUESTION",
            "-" * 80,
            self.research_question,
            "",
            "HYPOTHESES",
            "-" * 80,
        ]

        for h in self.hypotheses:
            primary_marker = " [PRIMARY]" if h.primary else ""
            lines.append(f"{h.id}{primary_marker}: {h.description}")
            lines.append(f"  Direction: {h.direction}")
            if h.variables:
                lines.append(f"  Variables: {h.variables}")
            lines.append("")

        lines.extend(
            [
                "OUTCOMES",
                "-" * 80,
                f"Primary: {self.primary_outcome.name} ({self.primary_outcome.metric})",
                "",
                "Secondary:",
            ]
        )

        for outcome in self.secondary_outcomes:
            lines.append(f"  - {outcome.name} ({outcome.metric})")

        lines.extend(
            [
                "",
                "DESIGN",
                "-" * 80,
                f"DUTs: {', '.join(self.duts)}",
                f"Tasks: {self.tasks}",
                f"Arenas: {', '.join(self.arenas)}",
                f"Sample size: {self.sample_size}",
                f"Justification: {self.sample_size_justification}",
                "",
                "STATISTICAL PLAN",
                "-" * 80,
                f"Alpha: {self.alpha}",
                f"Power: {self.power}",
                f"Correction: {self.correction_method}",
                f"Rating system: {self.rating_system}",
                "",
            ]
        )

        if self.stopping_rules:
            lines.extend(["STOPPING RULES", "-" * 80])
            for rule in self.stopping_rules:
                lines.append(f"  - {rule.rule_type}: {rule.description}")
            lines.append("")

        if self.exclusion_criteria:
            lines.extend(["EXCLUSION CRITERIA", "-" * 80])
            for criteria in self.exclusion_criteria:
                lines.append(f"  - {criteria.criterion}: {criteria.description}")
            lines.append("")

        if self.osf_url:
            lines.extend(
                [
                    "REGISTRATION",
                    "-" * 80,
                    f"OSF URL: {self.osf_url}",
                    "",
                ]
            )

        if self.notes:
            lines.extend(
                [
                    "NOTES",
                    "-" * 80,
                    self.notes,
                    "",
                ]
            )

        lines.append("=" * 80)

        return "\n".join(lines)
