"""Tournament runner for comparing multiple DUTs."""

import itertools
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from codegen_bench.cache.store import SolutionCache
from codegen_bench.checkpoint import CheckpointManager, CheckpointState
from codegen_bench.core.arena import Arena
from codegen_bench.core.config import TournamentConfig
from codegen_bench.core.judgment import JudgmentResult
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.exceptions import BrownBenchError
from codegen_bench.judge.orchestrator import JudgeOrchestrator
from codegen_bench.stats.ratings.bayesian_elo import BayesianELO
from codegen_bench.utils import ShutdownHandler

logger = structlog.get_logger()


@dataclass
class ErrorRecord:
    """Record of an error that occurred during tournament execution."""

    timestamp: str
    phase: str  # "solution_generation" or "comparison"
    dut_id: str | None = None
    task_id: str | None = None
    arena: str | None = None
    error_type: str = ""
    error_message: str = ""
    is_retryable: bool = False
    error_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "phase": self.phase,
            "dut_id": self.dut_id,
            "task_id": self.task_id,
            "arena": self.arena,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "is_retryable": self.is_retryable,
            "error_context": self.error_context,
        }


@dataclass
class SolutionMetrics:
    """Metrics collected during solution generation."""

    cost_usd: float = 0.0
    time_seconds: float = 0.0
    tokens: int = 0


@dataclass
class DUTRating:
    """Rating for a single DUT."""

    dut_id: str
    rating: BayesianELO
    total_cost_usd: float = 0.0
    total_time_seconds: float = 0.0
    total_tokens: int = 0
    _comparisons: list[tuple[str, str, str, JudgmentResult]] = field(
        default_factory=list, repr=False
    )

    @property
    def elo(self) -> float:
        """Get ELO rating (mean)."""
        return self.rating.mean

    @property
    def elo_std(self) -> float:
        """Get ELO standard deviation (uncertainty)."""
        return self.rating.std

    @property
    def elo_lower_bound(self) -> float:
        """Get 95% confidence lower bound."""
        return self.rating.mean - 2 * self.rating.std

    @property
    def elo_upper_bound(self) -> float:
        """Get 95% confidence upper bound."""
        return self.rating.mean + 2 * self.rating.std

    @property
    def wins(self) -> int:
        """Compute wins from comparison history."""
        count = 0
        for dut_a, dut_b, _, judgment in self._comparisons:
            if dut_a == self.dut_id and judgment.winner == "A":
                count += 1
            elif dut_b == self.dut_id and judgment.winner == "B":
                count += 1
        return count

    @property
    def losses(self) -> int:
        """Compute losses from comparison history."""
        count = 0
        for dut_a, dut_b, _, judgment in self._comparisons:
            if dut_a == self.dut_id and judgment.winner == "B":
                count += 1
            elif dut_b == self.dut_id and judgment.winner == "A":
                count += 1
        return count

    @property
    def ties(self) -> int:
        """Compute ties from comparison history."""
        count = 0
        for dut_a, dut_b, _, judgment in self._comparisons:
            if (dut_a == self.dut_id or dut_b == self.dut_id) and judgment.winner == "TIE":
                count += 1
        return count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "dut_id": self.dut_id,
            "elo": self.elo,
            "elo_std": self.elo_std,
            "elo_lower_bound": self.elo_lower_bound,
            "elo_upper_bound": self.elo_upper_bound,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "total_cost_usd": self.total_cost_usd,
            "total_time_seconds": self.total_time_seconds,
            "total_tokens": self.total_tokens,
        }

    def __repr__(self) -> str:
        """Readable string representation."""
        return (
            f"DUTRating(dut_id={self.dut_id!r}, elo={self.elo:.1f}±{self.elo_std:.1f}, "
            f"W/L/T={self.wins}/{self.losses}/{self.ties}, cost=${self.total_cost_usd:.4f})"
        )


@dataclass
class TournamentResult:
    """Results from a tournament."""

    ratings: dict[str, DUTRating]
    comparisons: list[tuple[str, str, str, JudgmentResult]]  # dut_a, dut_b, arena, result
    tasks_evaluated: list[str]
    arenas: list[str]
    total_comparisons: int = 0
    total_cost_usd: float = 0.0
    start_time: float = 0.0  # Set explicitly when tournament starts
    end_time: float = 0.0
    errors: list[ErrorRecord] = field(default_factory=list)  # Error records for degraded execution

    @property
    def duration_seconds(self) -> float:
        """Get tournament duration in seconds.

        Returns 0.0 if start_time is not set (e.g., for deserialized results).
        Returns elapsed time if end_time is not set (tournament in progress).
        """
        if not self.start_time:
            return 0.0
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time

    def get_leaderboard(self) -> list[DUTRating]:
        """Get DUTs sorted by ELO rating."""
        return sorted(self.ratings.values(), key=lambda r: r.elo, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for YAML/JSON
        """
        result = {
            "tournament_metadata": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
                "total_comparisons": self.total_comparisons,
                "total_cost_usd": self.total_cost_usd,
                "total_errors": len(self.errors),
            },
            "tasks_evaluated": self.tasks_evaluated,
            "arenas": self.arenas,
            "ratings": {dut_id: rating.to_dict() for dut_id, rating in self.ratings.items()},
            "leaderboard": [rating.to_dict() for rating in self.get_leaderboard()],
            "comparisons": [
                {
                    "dut_a": dut_a,
                    "dut_b": dut_b,
                    "arena": arena,
                    "winner": judgment.winner,
                    "agreement_rate": judgment.agreement_rate,
                    "confidence": judgment.confidence,
                }
                for dut_a, dut_b, arena, judgment in self.comparisons
            ],
        }
        # Only include errors if there are any
        if self.errors:
            result["errors"] = [error.to_dict() for error in self.errors]
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TournamentResult":
        """Load tournament result from dictionary.

        Args:
            data: Dictionary representation from to_dict()

        Returns:
            TournamentResult instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Extract metadata
        try:
            metadata = data["tournament_metadata"]
            tasks_evaluated = data["tasks_evaluated"]
            arenas = data["arenas"]
            ratings_data = data["ratings"]
            comparisons_data = data["comparisons"]
        except KeyError as e:
            raise ValueError(f"Missing required field in tournament data: {e}") from e

        # Reconstruct ratings (without comparisons initially)
        ratings: dict[str, DUTRating] = {}
        for dut_id, rating_dict in ratings_data.items():
            # Reconstruct BayesianELO from elo and elo_std
            rating = BayesianELO()
            rating.mean = rating_dict["elo"]
            rating.std = rating_dict["elo_std"]

            ratings[dut_id] = DUTRating(
                dut_id=dut_id,
                rating=rating,
                total_cost_usd=rating_dict.get("total_cost_usd", 0.0),
                total_time_seconds=rating_dict.get("total_time_seconds", 0.0),
                total_tokens=rating_dict.get("total_tokens", 0),
            )

        # Reconstruct comparisons
        comparisons: list[tuple[str, str, str, JudgmentResult]] = []
        for comp in comparisons_data:
            # Create minimal JudgmentResult (we don't have votes saved)
            judgment = JudgmentResult(
                winner=comp["winner"],
                votes=[],  # Votes not serialized, so we can't reconstruct them
                agreement_rate=comp.get("agreement_rate", 1.0),
                confidence=comp.get("confidence", 1.0),
            )
            comparisons.append((comp["dut_a"], comp["dut_b"], comp["arena"], judgment))

        # Add comparisons to ratings for win/loss/tie calculation
        for comparison in comparisons:
            dut_a, dut_b, _, _ = comparison
            if dut_a in ratings:
                ratings[dut_a]._comparisons.append(comparison)
            if dut_b in ratings:
                ratings[dut_b]._comparisons.append(comparison)

        # Reconstruct errors if present
        errors: list[ErrorRecord] = []
        if "errors" in data:
            for error_dict in data["errors"]:
                errors.append(
                    ErrorRecord(
                        timestamp=error_dict["timestamp"],
                        phase=error_dict["phase"],
                        dut_id=error_dict.get("dut_id"),
                        task_id=error_dict.get("task_id"),
                        arena=error_dict.get("arena"),
                        error_type=error_dict.get("error_type", ""),
                        error_message=error_dict.get("error_message", ""),
                        is_retryable=error_dict.get("is_retryable", False),
                        error_context=error_dict.get("error_context", {}),
                    )
                )

        return cls(
            ratings=ratings,
            comparisons=comparisons,
            tasks_evaluated=tasks_evaluated,
            arenas=arenas,
            total_comparisons=metadata.get("total_comparisons", len(comparisons)),
            total_cost_usd=metadata.get("total_cost_usd", 0.0),
            start_time=metadata.get("start_time", 0.0),
            end_time=metadata.get("end_time", 0.0),
            errors=errors,
        )

    def save(self, output_dir: Path) -> Path:
        """Save tournament results to YAML file.

        Args:
            output_dir: Directory to save results (will be created if needed)

        Returns:
            Path to the saved tournament.yaml file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "tournament.yaml"

        with open(output_file, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

        logger.info("tournament_results_saved", output_file=str(output_file))
        return output_file


class TournamentRunner:
    """Run tournaments comparing multiple DUTs."""

    def __init__(
        self,
        duts: list[CodeGenerationApproach],
        tasks: list[Task],
        judges: JudgeOrchestrator,
        arenas: list[Arena],
        cache: SolutionCache,
        samples_per_pairing: int = 3,
        config: TournamentConfig | None = None,
    ):
        """Initialize tournament runner.

        Args:
            duts: List of DUTs to compare
            tasks: List of tasks to evaluate on
            judges: Judge orchestrator for comparisons
            arenas: List of arenas (quality dimensions) to evaluate
            cache: Solution cache
            samples_per_pairing: Number of samples per (DUT, task) pair (deprecated,
                                use config.samples_per_pairing instead)
            config: Tournament configuration. If None, uses default TournamentConfig.
                   If both config and samples_per_pairing are provided, config takes
                   precedence.

        Raises:
            ValueError: If duts, tasks, or arenas lists are empty
        """
        # Validate inputs at construction time for fail-fast behavior
        if not duts:
            raise ValueError("Cannot create tournament with zero DUTs")
        if not tasks:
            raise ValueError("Cannot create tournament with zero tasks")
        if not arenas:
            raise ValueError("Cannot create tournament with zero arenas")

        # Fail fast if both config and samples_per_pairing are provided
        if config is not None and samples_per_pairing != 3:
            raise ValueError(
                "Cannot specify both 'config' and non-default 'samples_per_pairing'. "
                "Use TournamentConfig(samples_per_pairing=N) instead. "
                "The samples_per_pairing parameter is deprecated in favor of config."
            )

        self.duts = duts
        self.tasks = tasks
        self.judges = judges
        self.arenas = arenas
        self.cache = cache

        # Use config if provided, otherwise create default with samples_per_pairing
        if config is not None:
            self.config = config
        else:
            # Support legacy samples_per_pairing parameter for backward compatibility
            self.config = TournamentConfig(samples_per_pairing=samples_per_pairing)

        # Initialize ratings
        self.ratings: dict[str, DUTRating] = {}
        for dut in duts:
            dut_id = dut.get_metadata().id
            self.ratings[dut_id] = DUTRating(
                dut_id=dut_id,
                rating=BayesianELO(),
            )

        # Track errors for graceful degradation
        self.errors: list[ErrorRecord] = []

    @property
    def samples_per_pairing(self) -> int:
        """Get samples_per_pairing from config (backward compatibility property).

        This property maintains backward compatibility with code that directly
        accesses runner.samples_per_pairing instead of runner.config.samples_per_pairing.

        Returns:
            Number of samples per (DUT, task) pairing from config
        """
        return self.config.samples_per_pairing

    def generate_solutions(
        self,
    ) -> tuple[dict[tuple[str, str, int], Solution], dict[str, SolutionMetrics]]:
        """Generate all solutions for DUT-task-seed combinations.

        Implements graceful degradation: if a DUT fails to generate a solution for a task,
        the error is logged and recorded, but the tournament continues with other DUTs/tasks.

        Returns:
            Tuple of (solutions dict, metrics dict) where:
            - solutions: mapping (dut_id, task_id, sample_index) to Solution
            - metrics: mapping dut_id to aggregated SolutionMetrics
        """
        solutions: dict[tuple[str, str, int], Solution] = {}
        metrics: dict[str, SolutionMetrics] = {}

        for dut in self.duts:
            dut_id = dut.get_metadata().id
            metrics[dut_id] = SolutionMetrics()

            for task in self.tasks:
                for i in range(self.config.samples_per_pairing):
                    seed = self.config.base_seed + i  # Deterministic seeds

                    try:
                        sol = self.cache.get(dut, task, seed)
                        if sol is None:
                            sol = dut.solve(task, seed)
                            self.cache.put(dut, task, seed, sol)

                        solutions[(dut_id, task.id, i)] = sol

                        # Collect metrics (no mutation of self.ratings)
                        metrics[dut_id].cost_usd += sol.cost_usd
                        metrics[dut_id].time_seconds += sol.generation_time_seconds
                        metrics[dut_id].tokens += sol.total_tokens

                    except Exception as e:
                        # Graceful degradation: log error and continue
                        error_context = {}
                        is_retryable = False

                        if isinstance(e, BrownBenchError):
                            error_context = e.context.to_dict()
                            is_retryable = e.context.is_retryable

                        error_record = ErrorRecord(
                            timestamp=datetime.now(UTC).isoformat(),
                            phase="solution_generation",
                            dut_id=dut_id,
                            task_id=task.id,
                            error_type=type(e).__name__,
                            error_message=str(e),
                            is_retryable=is_retryable,
                            error_context=error_context,
                        )
                        self.errors.append(error_record)

                        logger.error(
                            "solution_generation_failed",
                            dut_id=dut_id,
                            task_id=task.id,
                            seed=seed,
                            error_type=type(e).__name__,
                            error_message=str(e),
                            is_retryable=is_retryable,
                        )
                        # Continue to next task/sample

        logger.info(
            "solutions_generated",
            total_solutions=len(solutions),
            total_errors=len([e for e in self.errors if e.phase == "solution_generation"]),
        )
        return solutions, metrics

    def compare_solutions(
        self,
        solutions: dict[tuple[str, str, int], Solution],
        progress_callback: Callable[[int], None] | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        shutdown_handler: ShutdownHandler | None = None,
        checkpoint_interval: int = 10,
    ) -> list[tuple[str, str, str, JudgmentResult]]:
        """Compare all solution pairs across arenas.

        When resuming from checkpoint, all comparisons are re-run (not skipped).
        This sacrifices API cost efficiency for simpler, more maintainable code.
        The checkpoint preserves ratings and metrics but not individual comparisons.
        This design assumes comparisons are relatively cheap compared to solution
        generation, which is cached.

        Args:
            solutions: Dictionary mapping (dut_id, task_id, sample_index) to Solution
            progress_callback: Optional callback called with total comparison count.
                             Signature: callback(total_comparisons: int) -> None
            checkpoint_manager: Optional checkpoint manager for saving progress
            shutdown_handler: Optional shutdown handler to check for interruption
            checkpoint_interval: Save checkpoint every N comparisons (default: 10)

        Returns:
            List of comparisons: (dut_a_id, dut_b_id, arena_name, judgment)
        """
        comparisons: list[tuple[str, str, str, JudgmentResult]] = []
        completed_for_checkpoint: list[
            tuple[str, str, str, str]
        ] = []  # (dut_a, dut_b, task_id, arena)
        total_comparisons = 0
        comparisons_since_checkpoint = 0

        for arena in self.arenas:
            for task in self.tasks:
                # Get all DUT pairs
                for dut_a, dut_b in itertools.combinations(self.duts, 2):
                    dut_a_id = dut_a.get_metadata().id
                    dut_b_id = dut_b.get_metadata().id

                    # Compare all sample pairs
                    for i in range(self.config.samples_per_pairing):
                        # Check for shutdown request
                        if shutdown_handler and shutdown_handler.shutdown_requested:
                            logger.info(
                                "shutdown_requested",
                                completed_comparisons=total_comparisons,
                                message="Saving checkpoint before shutdown",
                            )
                            if checkpoint_manager:
                                self._save_checkpoint(
                                    checkpoint_manager,
                                    comparisons,
                                    completed_for_checkpoint,
                                    solutions,
                                    total_comparisons,
                                )
                            return comparisons

                        # Check if both solutions exist (graceful degradation)
                        sol_a_key = (dut_a_id, task.id, i)
                        sol_b_key = (dut_b_id, task.id, i)

                        if sol_a_key not in solutions:
                            logger.warning(
                                "solution_missing_for_comparison",
                                dut_id=dut_a_id,
                                task_id=task.id,
                                sample_index=i,
                                arena=arena.name,
                                reason="Solution generation failed earlier",
                            )
                            continue

                        if sol_b_key not in solutions:
                            logger.warning(
                                "solution_missing_for_comparison",
                                dut_id=dut_b_id,
                                task_id=task.id,
                                sample_index=i,
                                arena=arena.name,
                                reason="Solution generation failed earlier",
                            )
                            continue

                        sol_a = solutions[sol_a_key]
                        sol_b = solutions[sol_b_key]

                        try:
                            # Get judgment
                            judgment = self.judges.compare(sol_a, sol_b, arena, task)

                            # Record comparison
                            comparison = (dut_a_id, dut_b_id, arena.name, judgment)
                            comparisons.append(comparison)
                            completed_for_checkpoint.append(
                                (dut_a_id, dut_b_id, task.id, arena.name)
                            )
                            total_comparisons += 1
                            comparisons_since_checkpoint += 1

                            if progress_callback:
                                progress_callback(total_comparisons)

                        except Exception as e:
                            # Graceful degradation: log judge error and continue
                            error_context = {}
                            is_retryable = False

                            if isinstance(e, BrownBenchError):
                                error_context = e.context.to_dict()
                                is_retryable = e.context.is_retryable

                            error_record = ErrorRecord(
                                timestamp=datetime.now(UTC).isoformat(),
                                phase="comparison",
                                dut_id=f"{dut_a_id} vs {dut_b_id}",
                                task_id=task.id,
                                arena=arena.name,
                                error_type=type(e).__name__,
                                error_message=str(e),
                                is_retryable=is_retryable,
                                error_context=error_context,
                            )
                            self.errors.append(error_record)

                            logger.error(
                                "comparison_failed",
                                dut_a_id=dut_a_id,
                                dut_b_id=dut_b_id,
                                task_id=task.id,
                                arena=arena.name,
                                error_type=type(e).__name__,
                                error_message=str(e),
                                is_retryable=is_retryable,
                            )
                            # Continue to next comparison

                        # Save checkpoint periodically
                        if (
                            checkpoint_manager
                            and comparisons_since_checkpoint >= checkpoint_interval
                        ):
                            self._save_checkpoint(
                                checkpoint_manager,
                                comparisons,
                                completed_for_checkpoint,
                                solutions,
                                total_comparisons,
                            )
                            comparisons_since_checkpoint = 0

        # Final checkpoint save
        if checkpoint_manager:
            self._save_checkpoint(
                checkpoint_manager,
                comparisons,
                completed_for_checkpoint,
                solutions,
                total_comparisons,
            )

        logger.info("comparisons_complete", total_comparisons=total_comparisons)
        return comparisons

    def update_ratings(
        self,
        comparisons: list[tuple[str, str, str, JudgmentResult]],
    ) -> None:
        """Update ratings based on all comparisons.

        Args:
            comparisons: List of (dut_a_id, dut_b_id, arena_name, judgment) tuples
        """
        for comparison in comparisons:
            dut_a_id, dut_b_id, _, judgment = comparison
            self._update_ratings(dut_a_id, dut_b_id, judgment.winner, comparison)

    def _save_checkpoint(
        self,
        checkpoint_manager: CheckpointManager,
        comparisons: list[tuple[str, str, str, JudgmentResult]],
        completed_for_checkpoint: list[tuple[str, str, str, str]],
        solutions: dict[tuple[str, str, int], Solution],
        total_comparisons: int,
    ) -> None:
        """Save tournament checkpoint.

        Args:
            checkpoint_manager: Checkpoint manager to save to
            comparisons: List of completed comparisons (for ratings)
            completed_for_checkpoint: List of (dut_a, dut_b, task_id, arena) tuples for resume tracking
            solutions: Dictionary of all solutions (for metrics)
            total_comparisons: Total number of comparisons completed
        """
        # Extract ratings snapshot
        ratings_snapshot = {
            dut_id: {"mean": rating.rating.mean, "std": rating.rating.std}
            for dut_id, rating in self.ratings.items()
        }

        # Extract DUT metrics
        dut_metrics = {
            dut_id: {
                "cost": rating.total_cost_usd,
                "time": rating.total_time_seconds,
                "tokens": rating.total_tokens,
            }
            for dut_id, rating in self.ratings.items()
        }

        # Calculate totals
        total_cost = sum(r.total_cost_usd for r in self.ratings.values())
        total_time = sum(r.total_time_seconds for r in self.ratings.values())

        # Create checkpoint state
        state = CheckpointState(
            completed_comparisons=tuple(completed_for_checkpoint),
            ratings_snapshot=ratings_snapshot,
            dut_metrics=dut_metrics,
            total_cost_usd=total_cost,
            total_time_seconds=total_time,
            checkpoint_time=datetime.now(UTC).isoformat(),
            tournament_start_time=self._tournament_start_time,
        )

        try:
            checkpoint_manager.save(state)
            logger.info(
                "checkpoint_saved",
                completed_comparisons=len(comparisons),
                total_cost_usd=total_cost,
            )
        except Exception as e:
            logger.error(
                "checkpoint_save_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't fail the tournament if checkpoint save fails
            # Just log the error and continue

    def run(
        self,
        progress_callback: Callable[[int], None] | None = None,
        output_dir: Path | None = None,
        checkpoint_dir: Path | None = None,
        checkpoint_interval: int | None = None,
    ) -> TournamentResult:
        """Run full tournament with optional checkpointing and resume support.

        Tournament execution pipeline:
        1. Solution Generation: Call each DUT on each task (with samples_per_pairing iterations)
           - Uses cache to avoid regenerating identical solutions
           - Collects cost, time, and token metrics
        2. Pairwise Comparison: Compare all DUT pairs across all arenas
           - Judges evaluate solution pairs
           - Results in n*(n-1)/2 comparisons per task per arena
           - Saves checkpoints periodically for resumability
           - Respects shutdown signals (SIGINT/SIGTERM) for graceful termination
        3. Rating Update: Update Bayesian ELO ratings based on comparison results
           - Tracks win/loss/tie for each DUT
           - Maintains uncertainty estimates (mean and variance)
        4. Result Aggregation: Package all results into TournamentResult
        5. Optional: Save results to disk if output_dir is specified

        Checkpointing:
        - If checkpoint_dir is provided, tournament can be resumed after interruption
        - Checkpoints are saved every checkpoint_interval comparisons
        - On SIGINT/SIGTERM, saves checkpoint before exiting
        - Completed comparisons are skipped when resuming

        Args:
            progress_callback: Optional callback called with total comparison count.
                             Signature: callback(total_comparisons: int) -> None
            output_dir: Optional directory to save results. If provided, results will be
                       saved to {output_dir}/tournament-{timestamp}/tournament.yaml
            checkpoint_dir: Optional directory for saving checkpoints. Enables resume
                          functionality if tournament is interrupted.
            checkpoint_interval: Optional override for checkpoint interval. If not provided,
                               uses config.checkpoint_interval. Determines how often
                               checkpoints are saved (every N comparisons).

        Returns:
            TournamentResult with all comparisons and ratings

        Raises:
            ValueError: If checkpoint_dir exists but checkpoint is invalid
        """
        # Setup checkpoint manager and shutdown handler
        checkpoint_manager = CheckpointManager(checkpoint_dir) if checkpoint_dir else None
        shutdown_handler = ShutdownHandler() if checkpoint_dir else None

        # Determine checkpoint interval (parameter overrides config)
        effective_checkpoint_interval = (
            checkpoint_interval if checkpoint_interval is not None else self.config.checkpoint_interval
        )

        # Load checkpoint if resuming
        if checkpoint_manager and checkpoint_manager.checkpoint_exists():
            try:
                checkpoint_state = checkpoint_manager.load()
                logger.info(
                    "resuming_from_checkpoint",
                    completed_comparisons=len(checkpoint_state.completed_comparisons),
                    total_cost_usd=checkpoint_state.total_cost_usd,
                    checkpoint_age_seconds=checkpoint_manager.get_checkpoint_age(),
                )
                self._tournament_start_time = checkpoint_state.tournament_start_time

                # Restore ratings from checkpoint
                for dut_id, rating_data in checkpoint_state.ratings_snapshot.items():
                    if dut_id in self.ratings:
                        self.ratings[dut_id].rating.mean = rating_data["mean"]
                        self.ratings[dut_id].rating.std = rating_data["std"]

                # Restore metrics from checkpoint
                for dut_id, metrics_data in checkpoint_state.dut_metrics.items():
                    if dut_id in self.ratings:
                        self.ratings[dut_id].total_cost_usd = metrics_data["cost"]
                        self.ratings[dut_id].total_time_seconds = metrics_data["time"]
                        self.ratings[dut_id].total_tokens = int(metrics_data["tokens"])

            except Exception as e:
                logger.error(
                    "checkpoint_load_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise ValueError(f"Failed to load checkpoint: {e}") from e
        else:
            self._tournament_start_time = time.time()
            logger.info(
                "tournament_start",
                num_duts=len(self.duts),
                num_tasks=len(self.tasks),
                num_arenas=len(self.arenas),
                samples_per_pairing=self.config.samples_per_pairing,
            )

        # Register shutdown handler if checkpointing enabled
        if shutdown_handler:
            shutdown_handler.register()

        try:
            # Step 1: Generate all solutions and collect metrics
            solutions, metrics = self.generate_solutions()

            # Apply metrics to ratings
            for dut_id, m in metrics.items():
                self.ratings[dut_id].total_cost_usd += m.cost_usd
                self.ratings[dut_id].total_time_seconds += m.time_seconds
                self.ratings[dut_id].total_tokens += m.tokens

            # Step 2: Compare all solution pairs
            comparisons = self.compare_solutions(
                solutions,
                progress_callback,
                checkpoint_manager,
                shutdown_handler,
                effective_checkpoint_interval,
            )

            # Check if shutdown was requested
            if shutdown_handler and shutdown_handler.shutdown_requested:
                logger.warning(
                    "tournament_interrupted",
                    completed_comparisons=len(comparisons),
                    total_errors=len(self.errors),
                    message="Tournament interrupted by shutdown signal, checkpoint saved",
                )
                # Return partial result
                return TournamentResult(
                    ratings=self.ratings,
                    comparisons=comparisons,
                    tasks_evaluated=[t.id for t in self.tasks],
                    arenas=[a.name for a in self.arenas],
                    total_comparisons=len(comparisons),
                    total_cost_usd=sum(r.total_cost_usd for r in self.ratings.values()),
                    start_time=self._tournament_start_time,
                    end_time=time.time(),
                    errors=self.errors,
                )

            # Step 3: Update ratings
            self.update_ratings(comparisons)

        finally:
            # Always unregister shutdown handler
            if shutdown_handler:
                shutdown_handler.unregister()

        logger.info(
            "tournament_complete",
            total_comparisons=len(comparisons),
            total_errors=len(self.errors),
        )

        result = TournamentResult(
            ratings=self.ratings,
            comparisons=comparisons,
            tasks_evaluated=[t.id for t in self.tasks],
            arenas=[a.name for a in self.arenas],
            total_comparisons=len(comparisons),
            total_cost_usd=sum(r.total_cost_usd for r in self.ratings.values()),
            start_time=self._tournament_start_time,
            end_time=time.time(),
            errors=self.errors,
        )

        # Delete checkpoint after successful completion
        if checkpoint_manager:
            try:
                checkpoint_manager.delete()
                logger.info("checkpoint_deleted", message="Tournament completed successfully")
            except Exception as e:
                logger.warning(
                    "checkpoint_delete_failed",
                    error=str(e),
                    message="Failed to delete checkpoint, but tournament completed",
                )

        # Save results if output directory provided
        if output_dir is not None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            result_dir = output_dir / f"tournament-{timestamp}"
            try:
                result.save(result_dir)
            except Exception as e:
                logger.error(
                    "failed_to_save_results",
                    error=str(e),
                    error_type=type(e).__name__,
                    result_dir=str(result_dir),
                )
                # Re-raise if output_dir was explicitly specified by user
                # This is a user expectation - they want results saved
                raise

        return result

    def _update_ratings(
        self,
        dut_a_id: str,
        dut_b_id: str,
        winner: str,
        comparison: tuple[str, str, str, JudgmentResult],
    ) -> None:
        """Update ELO ratings based on comparison result.

        Args:
            dut_a_id: ID of first DUT
            dut_b_id: ID of second DUT
            winner: 'A', 'B', or 'TIE'
            comparison: The full comparison tuple to add to history
        """
        rating_a = self.ratings[dut_a_id].rating
        rating_b = self.ratings[dut_b_id].rating

        # Update ELO ratings
        if winner == "A":
            rating_a.update(rating_b, "win")
        elif winner == "B":
            rating_a.update(rating_b, "loss")
        else:  # TIE
            rating_a.update(rating_b, "tie")

        # Add comparison to both DUT histories
        self.ratings[dut_a_id]._comparisons.append(comparison)
        self.ratings[dut_b_id]._comparisons.append(comparison)
