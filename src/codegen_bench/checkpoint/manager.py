"""Checkpoint manager for resumable tournament execution.

This module provides checkpointing functionality to save and restore tournament
state, enabling:
- Resume after interruption (SIGINT, crashes, etc.)
- Incremental progress tracking
- Cost tracking across sessions
- Partial result preservation
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class CheckpointState:
    """State captured in a checkpoint.

    Immutable to prevent accidental modification after creation.

    Attributes:
        completed_comparisons: Tuple of completed (dut_a, dut_b, task_id, arena) tuples
        ratings_snapshot: Current ELO ratings for each DUT
        dut_metrics: Metrics for each DUT (cost, time, tokens)
        total_cost_usd: Cumulative cost so far
        total_time_seconds: Cumulative time so far
        checkpoint_time: When this checkpoint was created (ISO format)
        tournament_start_time: When the tournament originally started (unix timestamp)
    """

    completed_comparisons: tuple[tuple[str, str, str, str], ...]
    ratings_snapshot: dict[str, dict[str, float]]  # dut_id -> {mean, std}
    dut_metrics: dict[str, dict[str, float]]  # dut_id -> {cost, time, tokens}
    total_cost_usd: float
    total_time_seconds: float
    checkpoint_time: str
    tournament_start_time: float

    def __post_init__(self) -> None:
        """Validate checkpoint state on creation."""
        if self.total_cost_usd < 0:
            raise ValueError(f"total_cost_usd must be non-negative, got {self.total_cost_usd}")

        if self.total_time_seconds < 0:
            raise ValueError(f"total_time_seconds must be non-negative, got {self.total_time_seconds}")

        # Validate ISO format timestamp
        try:
            datetime.fromisoformat(self.checkpoint_time)
        except ValueError as e:
            raise ValueError(f"checkpoint_time must be valid ISO format: {e}") from e


class CheckpointManager:
    """Manages tournament checkpoints for resumability.

    This class handles saving and loading tournament state to enable
    resuming long-running tournaments after interruption.

    Example:
        >>> manager = CheckpointManager(Path("checkpoints/tournament_001"))
        >>>
        >>> # Save checkpoint during tournament
        >>> state = CheckpointState(
        ...     completed_comparisons=[("dut1", "dut2", "task1", "correctness")],
        ...     ratings_snapshot={"dut1": {"mean": 1500, "std": 100}},
        ...     dut_metrics={"dut1": {"cost": 5.0, "time": 30.0, "tokens": 1000}},
        ...     total_cost_usd=10.0,
        ...     total_time_seconds=60.0,
        ...     checkpoint_time=datetime.now(UTC).isoformat(),
        ...     tournament_start_time=time.time()
        ... )
        >>> manager.save(state)
        >>>
        >>> # Resume later
        >>> if manager.checkpoint_exists():
        ...     state = manager.load()
        ...     print(f"Resuming from {len(state.completed_comparisons)} comparisons")
    """

    def __init__(self, checkpoint_dir: Path) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self._checkpoint_dir = checkpoint_dir
        self._checkpoint_file = checkpoint_dir / "checkpoint.json"

    def save(self, state: CheckpointState) -> None:
        """Save checkpoint to disk.

        Args:
            state: Checkpoint state to save

        Raises:
            OSError: If checkpoint cannot be written
        """
        # Create checkpoint directory if needed
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        data = {
            "completed_comparisons": [
                {"dut_a": a, "dut_b": b, "task_id": t, "arena": ar}
                for a, b, t, ar in state.completed_comparisons
            ],
            "ratings_snapshot": state.ratings_snapshot,
            "dut_metrics": state.dut_metrics,
            "total_cost_usd": state.total_cost_usd,
            "total_time_seconds": state.total_time_seconds,
            "checkpoint_time": state.checkpoint_time,
            "tournament_start_time": state.tournament_start_time,
        }

        # Write atomically: write to temp file, then rename
        temp_file = self._checkpoint_file.with_suffix(".json.tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            # Atomic rename (on POSIX systems)
            temp_file.replace(self._checkpoint_file)
        except Exception as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    # Cleanup failed, but don't mask original error
                    # In production, this should be logged
                    pass
            raise OSError(f"Failed to save checkpoint: {e}") from e

    def load(self) -> CheckpointState:
        """Load checkpoint from disk.

        Returns:
            CheckpointState loaded from disk

        Raises:
            FileNotFoundError: If no checkpoint exists
            ValueError: If checkpoint data is invalid
        """
        if not self._checkpoint_file.exists():
            raise FileNotFoundError(f"No checkpoint found at {self._checkpoint_file}")

        try:
            with open(self._checkpoint_file) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid checkpoint format: {e}") from e

        # Validate required fields
        required_fields = [
            "completed_comparisons",
            "ratings_snapshot",
            "dut_metrics",
            "total_cost_usd",
            "total_time_seconds",
            "checkpoint_time",
            "tournament_start_time",
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Checkpoint missing required fields: {', '.join(missing)}")

        # Convert back to tuples
        completed_comparisons = tuple(
            (c["dut_a"], c["dut_b"], c["task_id"], c["arena"]) for c in data["completed_comparisons"]
        )

        return CheckpointState(
            completed_comparisons=completed_comparisons,
            ratings_snapshot=data["ratings_snapshot"],
            dut_metrics=data["dut_metrics"],
            total_cost_usd=data["total_cost_usd"],
            total_time_seconds=data["total_time_seconds"],
            checkpoint_time=data["checkpoint_time"],
            tournament_start_time=data["tournament_start_time"],
        )

    def checkpoint_exists(self) -> bool:
        """Check if a checkpoint file exists.

        Returns:
            True if checkpoint exists, False otherwise
        """
        return self._checkpoint_file.exists()

    def delete(self) -> None:
        """Delete checkpoint file if it exists.

        Useful for cleaning up after successful tournament completion.
        """
        if self._checkpoint_file.exists():
            self._checkpoint_file.unlink()

    def get_checkpoint_age(self) -> float | None:
        """Get age of checkpoint in seconds.

        Returns:
            Seconds since checkpoint was created, or None if no checkpoint exists
        """
        if not self.checkpoint_exists():
            return None

        state = self.load()
        checkpoint_dt = datetime.fromisoformat(state.checkpoint_time)
        now = datetime.now(UTC)
        return (now - checkpoint_dt).total_seconds()

    def is_comparison_completed(self, dut_a: str, dut_b: str, task_id: str, arena: str) -> bool:
        """Check if a comparison has been completed.

        Args:
            dut_a: First DUT ID
            dut_b: Second DUT ID
            task_id: Task ID
            arena: Arena name

        Returns:
            True if this comparison was already completed, False otherwise
        """
        if not self.checkpoint_exists():
            return False

        state = self.load()
        comparison = (dut_a, dut_b, task_id, arena)
        return comparison in state.completed_comparisons

    def get_progress(self) -> tuple[int, float, float] | None:
        """Get current progress from checkpoint.

        Returns:
            Tuple of (completed_comparisons, total_cost, total_time) or None if no checkpoint
        """
        if not self.checkpoint_exists():
            return None

        state = self.load()
        return (
            len(state.completed_comparisons),
            state.total_cost_usd,
            state.total_time_seconds,
        )
