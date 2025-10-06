"""Tests for judgment dataclasses."""

from codegen_bench.core.judgment import JudgeVote, JudgmentResult


def test_judge_vote_creation() -> None:
    """Test basic judge vote creation."""
    vote = JudgeVote(
        vote="A",
        reasoning="Solution A is clearer",
        confidence=0.85,
    )
    assert vote.vote == "A"
    assert vote.reasoning == "Solution A is clearer"
    assert vote.confidence == 0.85


def test_judgment_result_creation() -> None:
    """Test judgment result with multiple votes."""
    votes = [
        JudgeVote(vote="A", reasoning="Reason 1", confidence=0.8),
        JudgeVote(vote="A", reasoning="Reason 2", confidence=0.9),
        JudgeVote(vote="B", reasoning="Reason 3", confidence=0.7),
    ]
    result = JudgmentResult(
        winner="A",
        votes=votes,
        agreement_rate=0.67,
        confidence=0.8,
    )
    assert result.winner == "A"
    assert len(result.votes) == 3
    assert result.agreement_rate == 0.67


def test_vote_types() -> None:
    """Test all vote types are valid."""
    for vote_type in ["A", "B", "TIE"]:
        vote = JudgeVote(vote=vote_type, reasoning="test", confidence=0.5)  # type: ignore
        assert vote.vote == vote_type
