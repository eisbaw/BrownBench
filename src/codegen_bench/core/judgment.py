"""Judge vote and judgment result."""

from dataclasses import dataclass
from typing import Literal

Vote = Literal["A", "B", "TIE"]


@dataclass
class JudgeVote:
    """A single judge's vote."""

    vote: Vote
    reasoning: str
    confidence: float  # 0-1


@dataclass
class JudgmentResult:
    """Consensus result from multiple judges."""

    winner: Vote
    votes: list[JudgeVote]
    agreement_rate: float
    confidence: float
