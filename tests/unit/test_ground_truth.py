"""Tests for ground truth data format."""

from pathlib import Path

import pytest

from codegen_bench.stats.ground_truth import ComparisonPair, GroundTruthDataset


def test_comparison_pair_creation():
    """Test creating a comparison pair."""
    pair = ComparisonPair(
        id="comp001",
        task_id="task_001",
        arena="correctness",
        solution_a_id="dut1_001_seed42",
        solution_b_id="dut2_001_seed42",
        ground_truth="A",
        notes="Solution A is better",
    )

    assert pair.id == "comp001"
    assert pair.task_id == "task_001"
    assert pair.arena == "correctness"
    assert pair.ground_truth == "A"
    assert pair.notes == "Solution A is better"


def test_ground_truth_dataset_creation():
    """Test creating a ground truth dataset."""
    comparisons = [
        ComparisonPair(
            id="comp001",
            task_id="task_001",
            arena="correctness",
            solution_a_id="dut1_001",
            solution_b_id="dut2_001",
            ground_truth="A",
        ),
        ComparisonPair(
            id="comp002",
            task_id="task_002",
            arena="maintainability",
            solution_a_id="dut1_002",
            solution_b_id="dut2_002",
            ground_truth="B",
        ),
    ]

    dataset = GroundTruthDataset(
        name="test-dataset",
        version="1.0",
        description="Test dataset",
        comparisons=comparisons,
    )

    assert dataset.name == "test-dataset"
    assert dataset.version == "1.0"
    assert len(dataset.comparisons) == 2


def test_load_ground_truth_from_yaml():
    """Test loading ground truth from YAML file."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    yaml_path = fixtures_dir / "ground_truth_sample.yaml"

    dataset = GroundTruthDataset.from_yaml(yaml_path)

    assert dataset.name == "sample-calibration-set"
    assert dataset.version == "1.0"
    assert len(dataset.comparisons) == 5

    # Check first comparison
    first = dataset.comparisons[0]
    assert first.id == "comp001"
    assert first.task_id == "task_001"
    assert first.arena == "correctness"
    assert first.ground_truth == "A"
    assert first.notes == "Solution A is clearly more correct"


def test_save_and_load_ground_truth(tmp_path):
    """Test saving and loading ground truth dataset."""
    comparisons = [
        ComparisonPair(
            id="comp001",
            task_id="task_001",
            arena="correctness",
            solution_a_id="dut1_001",
            solution_b_id="dut2_001",
            ground_truth="A",
        ),
        ComparisonPair(
            id="comp002",
            task_id="task_002",
            arena="maintainability",
            solution_a_id="dut1_002",
            solution_b_id="dut2_002",
            ground_truth="TIE",
        ),
    ]

    dataset = GroundTruthDataset(
        name="test-dataset",
        version="1.0",
        description="Test dataset",
        comparisons=comparisons,
    )

    # Save to file
    yaml_path = tmp_path / "test_ground_truth.yaml"
    dataset.to_yaml(yaml_path)

    # Load from file
    loaded = GroundTruthDataset.from_yaml(yaml_path)

    assert loaded.name == dataset.name
    assert loaded.version == dataset.version
    assert len(loaded.comparisons) == len(dataset.comparisons)
    assert loaded.comparisons[0].id == "comp001"
    assert loaded.comparisons[1].ground_truth == "TIE"


def test_ground_truth_with_optional_fields():
    """Test ground truth with optional solution text fields."""
    pair = ComparisonPair(
        id="comp001",
        task_id="task_001",
        arena="correctness",
        solution_a_id="dut1_001",
        solution_b_id="dut2_001",
        ground_truth="A",
        solution_a_text="def foo(): return 42",
        solution_b_text="def foo(): return 0",
    )

    assert pair.solution_a_text == "def foo(): return 42"
    assert pair.solution_b_text == "def foo(): return 0"


def test_load_nonexistent_file_raises():
    """Test loading from non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        GroundTruthDataset.from_yaml(Path("/nonexistent/file.yaml"))


def test_ground_truth_decisions_extraction():
    """Test extracting just the ground truth decisions."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    yaml_path = fixtures_dir / "ground_truth_sample.yaml"

    dataset = GroundTruthDataset.from_yaml(yaml_path)
    decisions = [c.ground_truth for c in dataset.comparisons]

    assert len(decisions) == 5
    assert decisions == ["A", "B", "TIE", "B", "A"]
