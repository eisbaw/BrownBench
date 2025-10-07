"""Tests for JudgeOrchestrator."""

from pathlib import Path

import pytest

from codegen_bench.core.arena import Arena
from codegen_bench.core.judgment import JudgeVote
from codegen_bench.judge.orchestrator import JudgeOrchestrator
from tests.unit.test_judge_base import MockJudge


def test_orchestrator_init():
    """Test orchestrator initialization."""
    judges = [MockJudge(), MockJudge(), MockJudge()]
    orchestrator = JudgeOrchestrator(judges)

    assert len(orchestrator.judges) == 3


def test_orchestrator_compare_unanimous(sample_task, sample_solution):
    """Test orchestrator with unanimous vote."""
    judges = [MockJudge(vote="A", confidence=0.9) for _ in range(3)]
    orchestrator = JudgeOrchestrator(judges)

    arena = Arena(
        name="test",
        display_name="Test",
        description="Test",
        criteria=["Test"],
        prompt_template_path=Path("test.txt"),
    )

    result = orchestrator.compare(sample_solution, sample_solution, arena, sample_task)

    # Result should be A or B (might be swapped due to randomization)
    assert result.winner in ["A", "B"]
    assert result.agreement_rate == 1.0
    assert len(result.votes) == 3


def test_orchestrator_compare_majority(sample_task, sample_solution):
    """Test orchestrator with majority vote."""
    judges = [
        MockJudge(vote="A", confidence=0.9),
        MockJudge(vote="A", confidence=0.8),
        MockJudge(vote="B", confidence=0.7),
    ]
    orchestrator = JudgeOrchestrator(judges)

    arena = Arena(
        name="test",
        display_name="Test",
        description="Test",
        criteria=["Test"],
        prompt_template_path=Path("test.txt"),
    )

    result = orchestrator.compare(sample_solution, sample_solution, arena, sample_task)

    # Majority should win (might be swapped)
    assert result.winner in ["A", "B"]
    assert result.agreement_rate >= 0.66


def test_orchestrator_compare_tie(sample_task, sample_solution):
    """Test orchestrator with tie (no majority)."""
    judges = [
        MockJudge(vote="A", confidence=0.9),
        MockJudge(vote="B", confidence=0.8),
        MockJudge(vote="TIE", confidence=0.7),
    ]
    orchestrator = JudgeOrchestrator(judges)

    arena = Arena(
        name="test",
        display_name="Test",
        description="Test",
        criteria=["Test"],
        prompt_template_path=Path("test.txt"),
    )

    result = orchestrator.compare(sample_solution, sample_solution, arena, sample_task)

    # No clear majority, should result in TIE
    assert result.winner == "TIE"


def test_orchestrator_five_judges(sample_task, sample_solution):
    """Test orchestrator with 5 judges."""
    judges = [
        MockJudge(vote="A", confidence=0.9),
        MockJudge(vote="A", confidence=0.85),
        MockJudge(vote="A", confidence=0.8),
        MockJudge(vote="B", confidence=0.75),
        MockJudge(vote="B", confidence=0.7),
    ]
    orchestrator = JudgeOrchestrator(judges)

    arena = Arena(
        name="test",
        display_name="Test",
        description="Test",
        criteria=["Test"],
        prompt_template_path=Path("test.txt"),
    )

    result = orchestrator.compare(sample_solution, sample_solution, arena, sample_task)

    # 3/5 for A should win (or swapped to B)
    assert result.winner in ["A", "B"]
    assert len(result.votes) == 5


def test_compute_consensus_three_judges():
    """Test consensus computation with 3 judges."""
    judges = [MockJudge() for _ in range(3)]
    orchestrator = JudgeOrchestrator(judges)

    # 2/3 for A
    votes = [
        JudgeVote(vote="A", reasoning="test", confidence=0.9),
        JudgeVote(vote="A", reasoning="test", confidence=0.8),
        JudgeVote(vote="B", reasoning="test", confidence=0.7),
    ]

    consensus = orchestrator._compute_consensus(votes)
    assert consensus == "A"

    # All different = TIE
    votes = [
        JudgeVote(vote="A", reasoning="test", confidence=0.9),
        JudgeVote(vote="B", reasoning="test", confidence=0.8),
        JudgeVote(vote="TIE", reasoning="test", confidence=0.7),
    ]

    consensus = orchestrator._compute_consensus(votes)
    assert consensus == "TIE"


def test_compute_consensus_five_judges():
    """Test consensus computation with 5 judges."""
    judges = [MockJudge() for _ in range(5)]
    orchestrator = JudgeOrchestrator(judges)

    # 3/5 for A
    votes = [
        JudgeVote(vote="A", reasoning="test", confidence=0.9),
        JudgeVote(vote="A", reasoning="test", confidence=0.85),
        JudgeVote(vote="A", reasoning="test", confidence=0.8),
        JudgeVote(vote="B", reasoning="test", confidence=0.75),
        JudgeVote(vote="B", reasoning="test", confidence=0.7),
    ]

    consensus = orchestrator._compute_consensus(votes)
    assert consensus == "A"

    # No 3+ majority = TIE
    votes = [
        JudgeVote(vote="A", reasoning="test", confidence=0.9),
        JudgeVote(vote="A", reasoning="test", confidence=0.8),
        JudgeVote(vote="B", reasoning="test", confidence=0.75),
        JudgeVote(vote="B", reasoning="test", confidence=0.7),
        JudgeVote(vote="TIE", reasoning="test", confidence=0.6),
    ]

    consensus = orchestrator._compute_consensus(votes)
    assert consensus == "TIE"


def test_agreement_rate():
    """Test agreement rate calculation."""
    judges = [MockJudge() for _ in range(3)]
    orchestrator = JudgeOrchestrator(judges)

    votes = [
        JudgeVote(vote="A", reasoning="test", confidence=0.9),
        JudgeVote(vote="A", reasoning="test", confidence=0.8),
        JudgeVote(vote="B", reasoning="test", confidence=0.7),
    ]

    rate = orchestrator._agreement_rate(votes, "A")
    assert rate == pytest.approx(2 / 3)

    rate = orchestrator._agreement_rate(votes, "B")
    assert rate == pytest.approx(1 / 3)


def test_compute_confidence():
    """Test confidence computation."""
    judges = [MockJudge() for _ in range(3)]
    orchestrator = JudgeOrchestrator(judges)

    votes = [
        JudgeVote(vote="A", reasoning="test", confidence=0.9),
        JudgeVote(vote="A", reasoning="test", confidence=0.8),
        JudgeVote(vote="B", reasoning="test", confidence=0.7),
    ]

    confidence = orchestrator._compute_confidence(votes)
    assert confidence == pytest.approx((0.9 + 0.8 + 0.7) / 3)


def test_vote_immutability():
    """Test that JudgeVote is immutable (frozen dataclass)."""
    vote = JudgeVote(vote="A", reasoning="test", confidence=0.9)

    # Attempting to modify should raise an error
    with pytest.raises(AttributeError):
        vote.vote = "B"  # type: ignore[misc]

    with pytest.raises(AttributeError):
        vote.confidence = 0.5  # type: ignore[misc]


def test_orchestrator_preserves_original_votes(sample_task, sample_solution):
    """Test that orchestrator doesn't mutate original votes when swapping positions."""
    judges = [MockJudge(vote="A", confidence=0.9) for _ in range(3)]
    orchestrator = JudgeOrchestrator(judges)

    arena = Arena(
        name="test",
        display_name="Test",
        description="Test",
        criteria=["Test"],
        prompt_template_path=Path("test.txt"),
    )

    # Run comparison multiple times to catch any swap-related mutations
    for _ in range(10):
        result = orchestrator.compare(sample_solution, sample_solution, arena, sample_task)
        # All returned votes should be valid (not mutated to invalid state)
        for vote in result.votes:
            assert vote.vote in ["A", "B", "TIE"]
            assert 0.0 <= vote.confidence <= 1.0
