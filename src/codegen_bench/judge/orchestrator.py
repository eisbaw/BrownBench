"""Judge orchestrator for coordinating multiple judges."""

from __future__ import annotations

import random
from collections import Counter
from typing import TYPE_CHECKING

from codegen_bench.core.arena import Arena
from codegen_bench.core.judgment import JudgeVote, JudgmentResult
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.judge.base import Judge

if TYPE_CHECKING:
    from codegen_bench.judge.base import Vote


class JudgeOrchestrator:
    """Coordinate multiple judges to reach consensus."""

    def __init__(self, judges: list[Judge]):
        """Initialize orchestrator.

        Args:
            judges: List of judge instances
        """
        self.judges = judges

    def compare(
        self, solution_a: Solution, solution_b: Solution, arena: Arena, task: Task
    ) -> JudgmentResult:
        """Get consensus judgment from multiple judges.

        Args:
            solution_a: First solution
            solution_b: Second solution
            arena: Arena to evaluate in
            task: Task being solved

        Returns:
            JudgmentResult with consensus winner and metadata
        """
        # Randomize position to avoid position bias
        swap = random.random() < 0.5
        if swap:
            solution_a, solution_b = solution_b, solution_a

        # Collect votes from all judges
        votes: list[JudgeVote] = []
        for judge in self.judges:
            vote = judge.evaluate(solution_a, solution_b, arena, task)
            votes.append(vote)

        # Compute consensus
        consensus_vote = self._compute_consensus(votes)

        # Swap back if needed
        if swap and consensus_vote != "TIE":
            consensus_vote = "B" if consensus_vote == "A" else "A"
            # Also swap votes
            for vote in votes:
                if vote.vote != "TIE":
                    vote.vote = "B" if vote.vote == "A" else "A"

        # Calculate agreement and confidence
        agreement = self._agreement_rate(votes, consensus_vote)
        confidence = self._compute_confidence(votes)

        return JudgmentResult(
            winner=consensus_vote,
            votes=votes,
            agreement_rate=agreement,
            confidence=confidence,
        )

    def _compute_consensus(self, votes: list[JudgeVote]) -> Vote:
        """Compute consensus from votes using majority rule.

        Args:
            votes: List of judge votes

        Returns:
            Consensus vote (A, B, or TIE)
        """
        vote_counts = Counter(v.vote for v in votes)

        # For 3 judges: need 2+ agreement
        if len(self.judges) == 3:
            if vote_counts.most_common(1)[0][1] >= 2:
                return vote_counts.most_common(1)[0][0]
            return "TIE"

        # For 5 judges: need 3+ agreement
        if len(self.judges) == 5:
            if vote_counts.most_common(1)[0][1] >= 3:
                return vote_counts.most_common(1)[0][0]
            return "TIE"

        # Default: most common vote
        return vote_counts.most_common(1)[0][0]

    def _agreement_rate(self, votes: list[JudgeVote], consensus: Vote) -> float:
        """Calculate fraction of judges agreeing with consensus.

        Args:
            votes: List of judge votes
            consensus: Consensus vote

        Returns:
            Agreement rate (0.0 to 1.0)
        """
        agrees = sum(1 for v in votes if v.vote == consensus)
        return agrees / len(votes)

    def _compute_confidence(self, votes: list[JudgeVote]) -> float:
        """Compute average confidence across judges.

        Args:
            votes: List of judge votes

        Returns:
            Average confidence (0.0 to 1.0)
        """
        return sum(v.confidence for v in votes) / len(votes)
