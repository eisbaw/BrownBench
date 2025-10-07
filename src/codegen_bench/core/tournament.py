"""Tournament runner for comparing multiple DUTs."""

import itertools
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

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
class DUTRating:
    """Rating for a single DUT."""

    dut_id: str
    rating: BayesianELO
    total_cost_usd: float = 0.0
    total_time_seconds: float = 0.0
    total_tokens: int = 0
    _comparisons: list[tuple[str, str, str, JudgmentResult]] = field(default_factory=list, repr=False)

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


@dataclass
class TournamentResult:
    """Results from a tournament."""

    ratings: dict[str, DUTRating]
    comparisons: list[tuple[str, str, str, JudgmentResult]]  # dut_a, dut_b, arena, result
    tasks_evaluated: list[str]
    arenas: list[str]
    total_comparisons: int = 0
    total_cost_usd: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0

    @property
    def duration_seconds(self) -> float:
        """Get tournament duration in seconds."""
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time

    def get_leaderboard(self) -> list[DUTRating]:
        """Get DUTs sorted by ELO rating."""
        return sorted(self.ratings.values(), key=lambda r: r.elo, reverse=True)


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
        """
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

    def run(self, progress_callback: Any = None) -> TournamentResult:
        """Run full tournament.

        Args:
            progress_callback: Optional callback for progress updates

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

        comparisons: list[tuple[str, str, str, JudgmentResult]] = []
        start_time = time.time()

        # Generate all solutions first
        solutions: dict[tuple[str, str, int], Solution] = {}
        for dut in self.duts:
            for task in self.tasks:
                for i in range(self.samples_per_pairing):
                    seed = 42 + i  # Deterministic seeds
                    sol = self.cache.get(dut, task, seed)
                    if sol is None:
                        sol = dut.solve(task, seed)
                        self.cache.put(dut, task, seed, sol)

                    solutions[(dut.get_metadata().id, task.id, i)] = sol

                    # Update cost metrics
                    dut_id = dut.get_metadata().id
                    self.ratings[dut_id].total_cost_usd += sol.cost_usd
                    self.ratings[dut_id].total_time_seconds += sol.generation_time_seconds
                    self.ratings[dut_id].total_tokens += sol.total_tokens

        logger.info("solutions_generated", total_solutions=len(solutions))

        # Compare all pairs
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

                        # Update ratings and add to comparison history
                        self._update_ratings(dut_a_id, dut_b_id, judgment.winner, comparison)
                        total_comparisons += 1

                        if progress_callback:
                            progress_callback(total_comparisons)

        logger.info("tournament_complete", total_comparisons=total_comparisons)

        return TournamentResult(
            ratings=self.ratings,
            comparisons=comparisons,
            tasks_evaluated=[t.id for t in self.tasks],
            arenas=[a.name for a in self.arenas],
            total_comparisons=total_comparisons,
            total_cost_usd=sum(r.total_cost_usd for r in self.ratings.values()),
            start_time=start_time,
            end_time=time.time(),
        )

    def _update_ratings(
        self, dut_a_id: str, dut_b_id: str, winner: str, comparison: tuple[str, str, str, JudgmentResult]
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
