"""Tests for pre-registration system."""

from pathlib import Path

from codegen_bench.core.preregistration import (
    ExclusionCriteria,
    Hypothesis,
    OutcomeMeasure,
    PreregistrationPlan,
    StoppingRule,
)


def test_hypothesis_creation() -> None:
    """Test Hypothesis dataclass creation."""
    h = Hypothesis(
        id="H1",
        description="DUT1 performs better than baseline",
        direction="greater",
        variables={"treatment": "dut1", "control": "baseline"},
        primary=True,
    )

    assert h.id == "H1"
    assert h.description == "DUT1 performs better than baseline"
    assert h.direction == "greater"
    assert h.variables["treatment"] == "dut1"
    assert h.primary is True


def test_hypothesis_defaults() -> None:
    """Test Hypothesis defaults."""
    h = Hypothesis(
        id="H2",
        description="Test hypothesis",
        direction="two-sided",
    )

    assert h.variables == {}
    assert h.primary is False


def test_outcome_measure_creation() -> None:
    """Test OutcomeMeasure dataclass."""
    outcome = OutcomeMeasure(
        name="correctness",
        metric="test_pass_rate",
        primary=True,
        arena="maintainability",
    )

    assert outcome.name == "correctness"
    assert outcome.metric == "test_pass_rate"
    assert outcome.primary is True
    assert outcome.arena == "maintainability"


def test_outcome_measure_defaults() -> None:
    """Test OutcomeMeasure defaults."""
    outcome = OutcomeMeasure(
        name="efficiency",
        metric="time_seconds",
    )

    assert outcome.primary is False
    assert outcome.arena is None


def test_stopping_rule_creation() -> None:
    """Test StoppingRule dataclass."""
    rule = StoppingRule(
        rule_type="sequential",
        parameters={"num_looks": 3, "alpha": 0.05},
        description="O'Brien-Fleming boundaries with 3 looks",
    )

    assert rule.rule_type == "sequential"
    assert rule.parameters["num_looks"] == 3
    assert "O'Brien-Fleming" in rule.description


def test_stopping_rule_defaults() -> None:
    """Test StoppingRule defaults."""
    rule = StoppingRule(
        rule_type="budget",
    )

    assert rule.parameters == {}
    assert rule.description == ""


def test_exclusion_criteria_creation() -> None:
    """Test ExclusionCriteria dataclass."""
    criteria = ExclusionCriteria(
        criterion="timeout",
        description="Solutions exceeding 10 minutes",
        apply_before_unblinding=True,
    )

    assert criteria.criterion == "timeout"
    assert "10 minutes" in criteria.description
    assert criteria.apply_before_unblinding is True


def test_preregistration_plan_creation() -> None:
    """Test PreregistrationPlan creation."""
    h1 = Hypothesis(
        id="H1",
        description="DUT1 > baseline",
        direction="greater",
        primary=True,
    )

    primary_outcome = OutcomeMeasure(
        name="correctness",
        metric="test_pass_rate",
        primary=True,
    )

    secondary_outcome = OutcomeMeasure(
        name="efficiency",
        metric="cost_usd",
    )

    plan = PreregistrationPlan(
        title="Test Study",
        research_question="Which DUT is better?",
        hypotheses=[h1],
        primary_outcome=primary_outcome,
        secondary_outcomes=[secondary_outcome],
        sample_size=100,
        sample_size_justification="Power analysis for d=0.5",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
    )

    assert plan.title == "Test Study"
    assert len(plan.hypotheses) == 1
    assert plan.primary_outcome.name == "correctness"
    assert len(plan.secondary_outcomes) == 1
    assert plan.sample_size == 100
    assert plan.alpha == 0.05  # Default
    assert plan.power == 0.80  # Default
    assert plan.correction_method == "fdr_bh"  # Default
    assert plan.rating_system == "trueskill"  # Default


def test_preregistration_plan_hash_generation() -> None:
    """Test that hash is auto-generated."""
    plan = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=50,
        sample_size_justification="50 is enough",
        duts=["dut1"],
        tasks="core",
        arenas=["maintainability"],
    )

    assert plan.plan_hash != ""
    assert len(plan.plan_hash) == 16  # First 16 chars of SHA-256


def test_preregistration_plan_hash_reproducible() -> None:
    """Test that identical plans have identical hashes."""
    plan1 = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=50,
        sample_size_justification="50 is enough",
        duts=["dut1"],
        tasks="core",
        arenas=["maintainability"],
    )

    plan2 = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=50,
        sample_size_justification="50 is enough",
        duts=["dut1"],
        tasks="core",
        arenas=["maintainability"],
    )

    # Hashes should match (timestamp excluded from hash)
    assert plan1._compute_hash() == plan2._compute_hash()


def test_preregistration_plan_hash_different_content() -> None:
    """Test that different plans have different hashes."""
    plan1 = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=50,
        sample_size_justification="50 is enough",
        duts=["dut1"],
        tasks="core",
        arenas=["maintainability"],
    )

    plan2 = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=100,  # Different sample size
        sample_size_justification="100 is enough",
        duts=["dut1"],
        tasks="core",
        arenas=["maintainability"],
    )

    assert plan1.plan_hash != plan2.plan_hash


def test_preregistration_to_yaml(tmp_path: Path) -> None:
    """Test saving plan to YAML."""
    plan = PreregistrationPlan(
        title="Test Study",
        research_question="Which DUT is better?",
        hypotheses=[
            Hypothesis(id="H1", description="DUT1 > baseline", direction="greater")
        ],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate", primary=True),
        secondary_outcomes=[OutcomeMeasure("efficiency", "cost_usd")],
        sample_size=100,
        sample_size_justification="Power analysis",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
    )

    yaml_path = tmp_path / "plan.yaml"
    plan.to_yaml(yaml_path)

    assert yaml_path.exists()

    # Check file contains key elements
    content = yaml_path.read_text()
    assert "title: Test Study" in content
    assert "research_question: Which DUT is better?" in content
    assert plan.plan_hash in content


def test_preregistration_from_yaml(tmp_path: Path) -> None:
    """Test loading plan from YAML."""
    original_plan = PreregistrationPlan(
        title="Test Study",
        research_question="Which DUT is better?",
        hypotheses=[
            Hypothesis(id="H1", description="DUT1 > baseline", direction="greater")
        ],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate", primary=True),
        secondary_outcomes=[OutcomeMeasure("efficiency", "cost_usd")],
        sample_size=100,
        sample_size_justification="Power analysis",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
        stopping_rules=[
            StoppingRule(
                rule_type="sequential",
                parameters={"num_looks": 3},
                description="Sequential design",
            )
        ],
        exclusion_criteria=[
            ExclusionCriteria(
                criterion="timeout",
                description="Timeout > 10 min",
            )
        ],
    )

    yaml_path = tmp_path / "plan.yaml"
    original_plan.to_yaml(yaml_path)

    # Load back
    loaded_plan = PreregistrationPlan.from_yaml(yaml_path)

    assert loaded_plan.title == original_plan.title
    assert loaded_plan.research_question == original_plan.research_question
    assert len(loaded_plan.hypotheses) == 1
    assert loaded_plan.hypotheses[0].id == "H1"
    assert loaded_plan.primary_outcome.name == "correctness"
    assert len(loaded_plan.secondary_outcomes) == 1
    assert loaded_plan.sample_size == 100
    assert len(loaded_plan.stopping_rules) == 1
    assert len(loaded_plan.exclusion_criteria) == 1


def test_preregistration_verify_hash() -> None:
    """Test hash verification."""
    plan = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=50,
        sample_size_justification="50 is enough",
        duts=["dut1"],
        tasks="core",
        arenas=["maintainability"],
    )

    # Should verify correctly
    assert plan.verify_hash(plan.plan_hash) is True

    # Should fail with wrong hash
    assert plan.verify_hash("wrong_hash") is False


def test_preregistration_verify_adherence_match() -> None:
    """Test adherence verification when config matches."""
    plan = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=100,
        sample_size_justification="Power analysis",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
        alpha=0.05,
        correction_method="fdr_bh",
    )

    tournament_config = {
        "duts": ["dut1", "baseline"],
        "sample_size": 100,
        "alpha": 0.05,
        "correction_method": "fdr_bh",
        "arenas": ["maintainability"],
    }

    result = plan.verify_adherence(tournament_config)

    assert result["adheres"] is True
    assert len(result["deviations"]) == 0
    assert result["major_deviations"] == 0
    assert result["minor_deviations"] == 0


def test_preregistration_verify_adherence_major_deviation() -> None:
    """Test adherence with major deviations."""
    plan = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=100,
        sample_size_justification="Power analysis",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
        alpha=0.05,
    )

    # Different DUTs (major deviation)
    tournament_config = {
        "duts": ["dut2", "baseline"],  # Changed dut1 to dut2
        "sample_size": 100,
        "alpha": 0.05,
        "correction_method": "fdr_bh",
        "arenas": ["maintainability"],
    }

    result = plan.verify_adherence(tournament_config)

    assert result["adheres"] is False
    assert result["major_deviations"] > 0


def test_preregistration_verify_adherence_sample_size() -> None:
    """Test adherence with insufficient sample size."""
    plan = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=100,
        sample_size_justification="Power analysis",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
    )

    # Smaller sample size
    tournament_config = {
        "duts": ["dut1", "baseline"],
        "sample_size": 50,  # Less than planned
        "alpha": 0.05,
        "correction_method": "fdr_bh",
        "arenas": ["maintainability"],
    }

    result = plan.verify_adherence(tournament_config)

    assert result["adheres"] is False
    assert result["major_deviations"] == 1


def test_preregistration_verify_adherence_minor_deviation() -> None:
    """Test adherence with minor deviations."""
    plan = PreregistrationPlan(
        title="Test",
        research_question="Q?",
        hypotheses=[],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate"),
        secondary_outcomes=[],
        sample_size=100,
        sample_size_justification="Power analysis",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
        correction_method="fdr_bh",
    )

    # Different correction method (minor deviation)
    tournament_config = {
        "duts": ["dut1", "baseline"],
        "sample_size": 100,
        "alpha": 0.05,
        "correction_method": "holm",  # Changed from fdr_bh
        "arenas": ["maintainability"],
    }

    result = plan.verify_adherence(tournament_config)

    assert result["adheres"] is False
    assert result["major_deviations"] == 0
    assert result["minor_deviations"] > 0


def test_preregistration_generate_report() -> None:
    """Test report generation."""
    plan = PreregistrationPlan(
        title="Test Study",
        research_question="Which DUT performs better?",
        hypotheses=[
            Hypothesis(
                id="H1",
                description="DUT1 > baseline in maintainability",
                direction="greater",
                primary=True,
            )
        ],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate", primary=True),
        secondary_outcomes=[OutcomeMeasure("efficiency", "cost_usd")],
        sample_size=100,
        sample_size_justification="Power = 0.80 for d=0.5",
        duts=["dut1", "baseline"],
        tasks="core",
        arenas=["maintainability"],
        alpha=0.05,
        correction_method="fdr_bh",
        notes="This is a test study",
    )

    report = plan.generate_report()

    assert "PRE-REGISTRATION PLAN" in report
    assert "Test Study" in report
    assert "Which DUT performs better?" in report
    assert "H1" in report
    assert "DUT1 > baseline" in report
    assert "correctness" in report
    assert "Sample size: 100" in report
    assert "Alpha: 0.05" in report
    assert "This is a test study" in report


def test_preregistration_roundtrip(tmp_path: Path) -> None:
    """Test save/load roundtrip preserves data."""
    original = PreregistrationPlan(
        title="Roundtrip Test",
        research_question="Does roundtrip work?",
        hypotheses=[
            Hypothesis(id="H1", description="Yes", direction="greater", primary=True),
            Hypothesis(id="H2", description="Maybe", direction="two-sided"),
        ],
        primary_outcome=OutcomeMeasure("correctness", "test_pass_rate", primary=True),
        secondary_outcomes=[
            OutcomeMeasure("efficiency", "cost_usd"),
            OutcomeMeasure("speed", "time_seconds"),
        ],
        sample_size=200,
        sample_size_justification="Computed via power analysis",
        duts=["dut1", "dut2", "baseline"],
        tasks="core",
        arenas=["maintainability", "architecture"],
        alpha=0.01,
        power=0.90,
        correction_method="holm",
        rating_system="bayesian_elo",
        stopping_rules=[
            StoppingRule(rule_type="sequential", parameters={"num_looks": 3}),
            StoppingRule(rule_type="budget", parameters={"max_cost": 1000}),
        ],
        exclusion_criteria=[
            ExclusionCriteria(criterion="timeout", description="Timeout > 10 min"),
            ExclusionCriteria(criterion="api_error", description="API failures"),
        ],
        notes="Important notes here",
    )

    yaml_path = tmp_path / "roundtrip.yaml"
    original.to_yaml(yaml_path)
    loaded = PreregistrationPlan.from_yaml(yaml_path)

    # Check all fields
    assert loaded.title == original.title
    assert loaded.research_question == original.research_question
    assert len(loaded.hypotheses) == 2
    assert loaded.hypotheses[0].id == "H1"
    assert loaded.hypotheses[1].id == "H2"
    assert loaded.primary_outcome.name == original.primary_outcome.name
    assert len(loaded.secondary_outcomes) == 2
    assert loaded.sample_size == 200
    assert loaded.alpha == 0.01
    assert loaded.power == 0.90
    assert loaded.correction_method == "holm"
    assert loaded.rating_system == "bayesian_elo"
    assert len(loaded.stopping_rules) == 2
    assert len(loaded.exclusion_criteria) == 2
    assert loaded.notes == original.notes


def test_preregistration_from_yaml_missing_required_field(tmp_path: Path) -> None:
    """Test that missing required fields raise appropriate errors."""
    import pytest
    import yaml

    # YAML with missing title (required field)
    malformed_yaml = tmp_path / "malformed.yaml"
    with open(malformed_yaml, "w") as f:
        yaml.dump(
            {
                "research_question": "Which DUT is best?",
                "hypotheses": [{"id": "H1", "description": "Test", "direction": "greater"}],
                "sample_size": 100,
            },
            f,
        )

    with pytest.raises((KeyError, TypeError, ValueError)):
        PreregistrationPlan.from_yaml(malformed_yaml)


def test_preregistration_from_yaml_nonexistent_file() -> None:
    """Test that loading from nonexistent file raises error."""
    import pytest

    nonexistent = Path("/tmp/does_not_exist_preregistration.yaml")

    with pytest.raises(FileNotFoundError):
        PreregistrationPlan.from_yaml(nonexistent)


def test_preregistration_from_yaml_corrupted_yaml(tmp_path: Path) -> None:
    """Test that corrupted YAML content raises error."""
    import pytest

    corrupted_yaml = tmp_path / "corrupted.yaml"
    with open(corrupted_yaml, "w") as f:
        f.write("this is not valid YAML: {{{]]]")

    with pytest.raises(Exception):  # yaml.YAMLError or similar
        PreregistrationPlan.from_yaml(corrupted_yaml)


def test_preregistration_from_yaml_empty_file(tmp_path: Path) -> None:
    """Test that empty YAML file raises error."""
    import pytest

    empty_yaml = tmp_path / "empty.yaml"
    empty_yaml.touch()

    with pytest.raises((ValueError, TypeError, AttributeError)):
        PreregistrationPlan.from_yaml(empty_yaml)
