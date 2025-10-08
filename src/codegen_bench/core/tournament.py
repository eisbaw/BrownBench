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
from codegen_bench.core.arena import Arena
from codegen_bench.core.judgment import JudgmentResult
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.judge.orchestrator import JudgeOrchestrator
from codegen_bench.stats.ratings.bayesian_elo import BayesianELO

logger = structlog.get_logger()


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

    @property
    def duration_seconds(self) -> float:
        """Get tournament duration in seconds."""
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time

    def get_leaderboard(self) -> list[DUTRating]:
        """Get DUTs sorted by ELO rating."""
        return sorted(self.ratings.values(), key=lambda r: r.elo, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for YAML/JSON
        """
        return {
            "tournament_metadata": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
                "total_comparisons": self.total_comparisons,
                "total_cost_usd": self.total_cost_usd,
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
    ):
        """Initialize tournament runner.

        Args:
            duts: List of DUTs to compare
            tasks: List of tasks to evaluate on
            judges: Judge orchestrator for comparisons
            arenas: List of arenas (quality dimensions) to evaluate
            cache: Solution cache
            samples_per_pairing: Number of samples per (DUT, task) pair

        Raises:
            ValueError: If duts, tasks, or arenas lists are empty, or if samples_per_pairing < 1
        """
        # Validate inputs at construction time for fail-fast behavior
        if not duts:
            raise ValueError("Cannot create tournament with zero DUTs")
        if not tasks:
            raise ValueError("Cannot create tournament with zero tasks")
        if not arenas:
            raise ValueError("Cannot create tournament with zero arenas")
        if samples_per_pairing < 1:
            raise ValueError(f"samples_per_pairing must be >= 1, got {samples_per_pairing}")

        self.duts = duts
        self.tasks = tasks
        self.judges = judges
        self.arenas = arenas
        self.cache = cache
        self.samples_per_pairing = samples_per_pairing

        # Initialize ratings
        self.ratings: dict[str, DUTRating] = {}
        for dut in duts:
            dut_id = dut.get_metadata().id
            self.ratings[dut_id] = DUTRating(
                dut_id=dut_id,
                rating=BayesianELO(),
            )

    def generate_solutions(
        self,
    ) -> tuple[dict[tuple[str, str, int], Solution], dict[str, SolutionMetrics]]:
        """Generate all solutions for DUT-task-seed combinations.

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
                for i in range(self.samples_per_pairing):
                    seed = 42 + i  # Deterministic seeds
                    sol = self.cache.get(dut, task, seed)
                    if sol is None:
                        sol = dut.solve(task, seed)
                        self.cache.put(dut, task, seed, sol)

                    solutions[(dut_id, task.id, i)] = sol

                    # Collect metrics (no mutation of self.ratings)
                    metrics[dut_id].cost_usd += sol.cost_usd
                    metrics[dut_id].time_seconds += sol.generation_time_seconds
                    metrics[dut_id].tokens += sol.total_tokens

        logger.info("solutions_generated", total_solutions=len(solutions))
        return solutions, metrics

    def compare_solutions(
        self,
        solutions: dict[tuple[str, str, int], Solution],
        progress_callback: Callable[[int], None] | None = None,
    ) -> list[tuple[str, str, str, JudgmentResult]]:
        """Compare all solution pairs across arenas.

        Args:
            solutions: Dictionary mapping (dut_id, task_id, sample_index) to Solution
            progress_callback: Optional callback called with total comparison count.
                             Signature: callback(total_comparisons: int) -> None

        Returns:
            List of comparisons: (dut_a_id, dut_b_id, arena_name, judgment)
        """
        comparisons: list[tuple[str, str, str, JudgmentResult]] = []
        total_comparisons = 0

        for arena in self.arenas:
            for task in self.tasks:
                # Get all DUT pairs
                for dut_a, dut_b in itertools.combinations(self.duts, 2):
                    dut_a_id = dut_a.get_metadata().id
                    dut_b_id = dut_b.get_metadata().id

                    # Compare all sample pairs
                    for i in range(self.samples_per_pairing):
                        sol_a = solutions[(dut_a_id, task.id, i)]
                        sol_b = solutions[(dut_b_id, task.id, i)]

                        # Get judgment
                        judgment = self.judges.compare(sol_a, sol_b, arena, task)

                        # Record comparison
                        comparison = (dut_a_id, dut_b_id, arena.name, judgment)
                        comparisons.append(comparison)
                        total_comparisons += 1

                        if progress_callback:
                            progress_callback(total_comparisons)

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

    def run(
        self,
        progress_callback: Callable[[int], None] | None = None,
        output_dir: Path | None = None,
    ) -> TournamentResult:
        """Run full tournament.

        Tournament execution pipeline:
        1. Solution Generation: Call each DUT on each task (with samples_per_pairing iterations)
           - Uses cache to avoid regenerating identical solutions
           - Collects cost, time, and token metrics
        2. Pairwise Comparison: Compare all DUT pairs across all arenas
           - Judges evaluate solution pairs
           - Results in n*(n-1)/2 comparisons per task per arena
        3. Rating Update: Update Bayesian ELO ratings based on comparison results
           - Tracks win/loss/tie for each DUT
           - Maintains uncertainty estimates (mean and variance)
        4. Result Aggregation: Package all results into TournamentResult
        5. Optional: Save results to disk if output_dir is specified

        Args:
            progress_callback: Optional callback called with total comparison count.
                             Signature: callback(total_comparisons: int) -> None
            output_dir: Optional directory to save results. If provided, results will be
                       saved to {output_dir}/tournament-{timestamp}/tournament.yaml

        Returns:
            TournamentResult with all comparisons and ratings
        """
        logger.info(
            "tournament_start",
            num_duts=len(self.duts),
            num_tasks=len(self.tasks),
            num_arenas=len(self.arenas),
            samples_per_pairing=self.samples_per_pairing,
        )

        start_time = time.time()

        # Step 1: Generate all solutions and collect metrics
        solutions, metrics = self.generate_solutions()

        # Apply metrics to ratings
        for dut_id, m in metrics.items():
            self.ratings[dut_id].total_cost_usd += m.cost_usd
            self.ratings[dut_id].total_time_seconds += m.time_seconds
            self.ratings[dut_id].total_tokens += m.tokens

        # Step 2: Compare all solution pairs
        comparisons = self.compare_solutions(solutions, progress_callback)

        # Step 3: Update ratings
        self.update_ratings(comparisons)

        logger.info("tournament_complete", total_comparisons=len(comparisons))

        result = TournamentResult(
            ratings=self.ratings,
            comparisons=comparisons,
            tasks_evaluated=[t.id for t in self.tasks],
            arenas=[a.name for a in self.arenas],
            total_comparisons=len(comparisons),
            total_cost_usd=sum(r.total_cost_usd for r in self.ratings.values()),
            start_time=start_time,
            end_time=time.time(),
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
