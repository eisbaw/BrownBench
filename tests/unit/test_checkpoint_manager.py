"""Tests for checkpoint manager."""

import json
import time
from datetime import UTC, datetime

import pytest

from codegen_bench.checkpoint import CheckpointManager, CheckpointState


def test_checkpoint_state_creation():
    """Test creating checkpoint state."""
    state = CheckpointState(
        completed_comparisons=[("dut1", "dut2", "task1", "correctness")],
        ratings_snapshot={"dut1": {"mean": 1500.0, "std": 100.0}},
        dut_metrics={"dut1": {"cost": 5.0, "time": 30.0, "tokens": 1000}},
        total_cost_usd=10.0,
        total_time_seconds=60.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    assert len(state.completed_comparisons) == 1
    assert state.total_cost_usd == 10.0
    assert state.total_time_seconds == 60.0


def test_save_and_load_checkpoint(tmp_path):
    """Test saving and loading checkpoint."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    start_time = time.time()
    checkpoint_time = datetime.now(UTC).isoformat()

    state = CheckpointState(
        completed_comparisons=[
            ("dut1", "dut2", "task1", "correctness"),
            ("dut1", "dut3", "task2", "maintainability"),
        ],
        ratings_snapshot={
            "dut1": {"mean": 1500.0, "std": 100.0},
            "dut2": {"mean": 1450.0, "std": 110.0},
        },
        dut_metrics={
            "dut1": {"cost": 5.0, "time": 30.0, "tokens": 1000},
            "dut2": {"cost": 3.0, "time": 20.0, "tokens": 800},
        },
        total_cost_usd=15.0,
        total_time_seconds=120.0,
        checkpoint_time=checkpoint_time,
        tournament_start_time=start_time,
    )

    manager.save(state)

    # Load and verify
    loaded = manager.load()

    assert len(loaded.completed_comparisons) == 2
    assert loaded.completed_comparisons[0] == ("dut1", "dut2", "task1", "correctness")
    assert loaded.total_cost_usd == 15.0
    assert loaded.total_time_seconds == 120.0
    assert loaded.checkpoint_time == checkpoint_time
    assert loaded.tournament_start_time == start_time


def test_checkpoint_exists(tmp_path):
    """Test checking if checkpoint exists."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    assert not manager.checkpoint_exists()

    state = CheckpointState(
        completed_comparisons=[],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=0.0,
        total_time_seconds=0.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)

    assert manager.checkpoint_exists()


def test_load_nonexistent_checkpoint_raises(tmp_path):
    """Test loading non-existent checkpoint raises error."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    with pytest.raises(FileNotFoundError, match="No checkpoint found"):
        manager.load()


def test_delete_checkpoint(tmp_path):
    """Test deleting checkpoint."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    state = CheckpointState(
        completed_comparisons=[],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=0.0,
        total_time_seconds=0.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)
    assert manager.checkpoint_exists()

    manager.delete()
    assert not manager.checkpoint_exists()


def test_delete_nonexistent_checkpoint_succeeds(tmp_path):
    """Test deleting non-existent checkpoint doesn't raise error."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    # Should not raise
    manager.delete()


def test_is_comparison_completed(tmp_path):
    """Test checking if specific comparison is completed."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    state = CheckpointState(
        completed_comparisons=[
            ("dut1", "dut2", "task1", "correctness"),
            ("dut2", "dut3", "task1", "maintainability"),
        ],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=10.0,
        total_time_seconds=60.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)

    # Should find completed comparisons
    assert manager.is_comparison_completed("dut1", "dut2", "task1", "correctness")
    assert manager.is_comparison_completed("dut2", "dut3", "task1", "maintainability")

    # Should not find uncompleted comparison
    assert not manager.is_comparison_completed("dut1", "dut3", "task1", "correctness")
    assert not manager.is_comparison_completed("dut1", "dut2", "task2", "correctness")


def test_get_progress(tmp_path):
    """Test getting progress from checkpoint."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    # No checkpoint yet
    assert manager.get_progress() is None

    state = CheckpointState(
        completed_comparisons=[
            ("dut1", "dut2", "task1", "correctness"),
            ("dut1", "dut3", "task1", "correctness"),
            ("dut2", "dut3", "task1", "correctness"),
        ],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=25.5,
        total_time_seconds=180.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)

    completed, cost, elapsed_time = manager.get_progress()

    assert completed == 3
    assert cost == 25.5
    assert elapsed_time == 180.0


def test_get_checkpoint_age(tmp_path):
    """Test getting checkpoint age."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    # No checkpoint yet
    assert manager.get_checkpoint_age() is None

    # Create checkpoint with recent timestamp
    checkpoint_time = datetime.now(UTC)
    state = CheckpointState(
        completed_comparisons=[],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=0.0,
        total_time_seconds=0.0,
        checkpoint_time=checkpoint_time.isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)

    age = manager.get_checkpoint_age()
    assert age is not None
    assert age >= 0
    assert age < 5  # Should be very recent


def test_atomic_save(tmp_path):
    """Test that save is atomic (uses temp file)."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    state = CheckpointState(
        completed_comparisons=[],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=0.0,
        total_time_seconds=0.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)

    # Temp file should not exist after save
    temp_file = (tmp_path / "checkpoints" / "checkpoint.json.tmp")
    assert not temp_file.exists()

    # Final file should exist
    assert manager.checkpoint_exists()


def test_load_invalid_json_raises(tmp_path):
    """Test loading invalid JSON raises error."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    # Create directory and write invalid JSON
    (tmp_path / "checkpoints").mkdir(parents=True)
    checkpoint_file = tmp_path / "checkpoints" / "checkpoint.json"
    checkpoint_file.write_text("invalid json {")

    with pytest.raises(ValueError, match="Invalid checkpoint format"):
        manager.load()


def test_load_missing_fields_raises(tmp_path):
    """Test loading checkpoint with missing fields raises error."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    # Create checkpoint with missing fields
    (tmp_path / "checkpoints").mkdir(parents=True)
    checkpoint_file = tmp_path / "checkpoints" / "checkpoint.json"

    incomplete_data = {
        "completed_comparisons": [],
        "ratings_snapshot": {},
        # Missing other required fields
    }

    with open(checkpoint_file, "w") as f:
        json.dump(incomplete_data, f)

    with pytest.raises(ValueError, match="missing required fields"):
        manager.load()


def test_multiple_saves_overwrite(tmp_path):
    """Test that multiple saves overwrite previous checkpoint."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    # Save first checkpoint
    state1 = CheckpointState(
        completed_comparisons=[("dut1", "dut2", "task1", "correctness")],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=5.0,
        total_time_seconds=30.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )
    manager.save(state1)

    # Save second checkpoint
    state2 = CheckpointState(
        completed_comparisons=[
            ("dut1", "dut2", "task1", "correctness"),
            ("dut1", "dut3", "task1", "correctness"),
        ],
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=10.0,
        total_time_seconds=60.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )
    manager.save(state2)

    # Load should return second state
    loaded = manager.load()
    assert len(loaded.completed_comparisons) == 2
    assert loaded.total_cost_usd == 10.0


def test_checkpoint_with_empty_comparisons(tmp_path):
    """Test checkpoint with no completed comparisons."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    state = CheckpointState(
        completed_comparisons=[],
        ratings_snapshot={"dut1": {"mean": 1500.0, "std": 100.0}},
        dut_metrics={"dut1": {"cost": 0.0, "time": 0.0, "tokens": 0}},
        total_cost_usd=0.0,
        total_time_seconds=0.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)
    loaded = manager.load()

    assert len(loaded.completed_comparisons) == 0
    assert loaded.total_cost_usd == 0.0


def test_checkpoint_with_complex_ratings(tmp_path):
    """Test checkpoint preserves complex rating data."""
    manager = CheckpointManager(tmp_path / "checkpoints")

    ratings = {
        "dut1": {"mean": 1523.45, "std": 98.76},
        "dut2": {"mean": 1487.23, "std": 105.43},
        "dut3": {"mean": 1556.78, "std": 89.12},
    }

    metrics = {
        "dut1": {"cost": 12.34, "time": 156.78, "tokens": 5432},
        "dut2": {"cost": 8.76, "time": 98.45, "tokens": 3210},
        "dut3": {"cost": 15.67, "time": 234.56, "tokens": 7890},
    }

    state = CheckpointState(
        completed_comparisons=(),
        ratings_snapshot=ratings,
        dut_metrics=metrics,
        total_cost_usd=36.77,
        total_time_seconds=489.79,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    manager.save(state)
    loaded = manager.load()

    assert loaded.ratings_snapshot == ratings
    assert loaded.dut_metrics == metrics
    assert loaded.total_cost_usd == 36.77


def test_checkpoint_state_is_immutable():
    """Test that CheckpointState cannot be modified after creation."""
    state = CheckpointState(
        completed_comparisons=(("dut1", "dut2", "task1", "correctness"),),
        ratings_snapshot={},
        dut_metrics={},
        total_cost_usd=10.0,
        total_time_seconds=60.0,
        checkpoint_time=datetime.now(UTC).isoformat(),
        tournament_start_time=time.time(),
    )

    # Cannot modify scalar fields
    with pytest.raises(AttributeError):
        state.total_cost_usd = 999.0  # type: ignore[misc]

    # Cannot modify nested fields
    with pytest.raises(AttributeError):
        state.ratings_snapshot = {}  # type: ignore[misc]


def test_checkpoint_state_validates_negative_cost():
    """Test that negative cost is rejected."""
    with pytest.raises(ValueError, match="total_cost_usd must be non-negative"):
        CheckpointState(
            completed_comparisons=(),
            ratings_snapshot={},
            dut_metrics={},
            total_cost_usd=-10.0,
            total_time_seconds=60.0,
            checkpoint_time=datetime.now(UTC).isoformat(),
            tournament_start_time=time.time(),
        )


def test_checkpoint_state_validates_negative_time():
    """Test that negative time is rejected."""
    with pytest.raises(ValueError, match="total_time_seconds must be non-negative"):
        CheckpointState(
            completed_comparisons=(),
            ratings_snapshot={},
            dut_metrics={},
            total_cost_usd=10.0,
            total_time_seconds=-60.0,
            checkpoint_time=datetime.now(UTC).isoformat(),
            tournament_start_time=time.time(),
        )


def test_checkpoint_state_validates_timestamp_format():
    """Test that invalid timestamp format is rejected."""
    with pytest.raises(ValueError, match="checkpoint_time must be valid ISO format"):
        CheckpointState(
            completed_comparisons=(),
            ratings_snapshot={},
            dut_metrics={},
            total_cost_usd=10.0,
            total_time_seconds=60.0,
            checkpoint_time="not a valid timestamp",
            tournament_start_time=time.time(),
        )
