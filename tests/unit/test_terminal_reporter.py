"""Tests for terminal reporter."""

import io

from rich.console import Console

from codegen_bench.core.tournament import DUTRating, TournamentResult
from codegen_bench.reporting.terminal import TerminalReporter
from codegen_bench.stats.ratings.bayesian_elo import BayesianELO


def test_terminal_reporter_initialization():
    """Test terminal reporter initialization."""
    reporter = TerminalReporter()
    assert reporter.console is not None

    # Test with custom console
    console = Console()
    reporter2 = TerminalReporter(console)
    assert reporter2.console == console


def test_terminal_reporter_display():
    """Test terminal reporter display."""
    from codegen_bench.core.judgment import JudgeVote, JudgmentResult

    # Create mock tournament result
    dut1_rating = DUTRating(
        dut_id="dut1",
        rating=BayesianELO(prior_mean=1600, prior_std=100),
        total_cost_usd=1.5,
        total_time_seconds=30.0,
        total_tokens=1000,
    )
    dut2_rating = DUTRating(
        dut_id="dut2",
        rating=BayesianELO(prior_mean=1500, prior_std=150),
        total_cost_usd=0.8,
        total_time_seconds=20.0,
        total_tokens=600,
    )

    # Add comparison history to match 10/2/1 and 5/8/2 win/loss/tie
    # dut1: 10 wins, 2 losses, 1 tie
    for _ in range(10):
        comp = (
            "dut1",
            "dut2",
            "test",
            JudgmentResult(
                winner="A",
                votes=[JudgeVote(vote="A", reasoning="test", confidence=0.9)],
                agreement_rate=1.0,
                confidence=0.9,
            ),
        )
        dut1_rating._comparisons.append(comp)
        dut2_rating._comparisons.append(comp)

    for _ in range(2):
        comp = (
            "dut1",
            "dut2",
            "test",
            JudgmentResult(
                winner="B",
                votes=[JudgeVote(vote="B", reasoning="test", confidence=0.9)],
                agreement_rate=1.0,
                confidence=0.9,
            ),
        )
        dut1_rating._comparisons.append(comp)
        dut2_rating._comparisons.append(comp)

    for _ in range(1):
        comp = (
            "dut1",
            "dut2",
            "test",
            JudgmentResult(
                winner="TIE",
                votes=[JudgeVote(vote="TIE", reasoning="test", confidence=0.9)],
                agreement_rate=1.0,
                confidence=0.9,
            ),
        )
        dut1_rating._comparisons.append(comp)
        dut2_rating._comparisons.append(comp)

    ratings = {
        "dut1": dut1_rating,
        "dut2": dut2_rating,
    }

    result = TournamentResult(
        ratings=ratings,
        comparisons=[
            (
                "dut1",
                "dut2",
                "test",
                JudgmentResult(
                    winner="A",
                    votes=[
                        JudgeVote(vote="A", reasoning="test", confidence=0.9),
                        JudgeVote(vote="A", reasoning="test", confidence=0.9),
                    ],
                    agreement_rate=1.0,
                    confidence=0.9,
                ),
            )
        ],
        tasks_evaluated=["task1", "task2"],
        arenas=["arena1", "arena2"],
        total_comparisons=2,
        total_cost_usd=2.3,
        start_time=0.0,
        end_time=10.0,
    )

    # Capture output
    output = io.StringIO()
    console = Console(file=output, width=120, force_terminal=True)
    reporter = TerminalReporter(console)

    reporter.display(result)

    output_str = output.getvalue()

    # Verify key information is present
    assert "TOURNAMENT RESULTS" in output_str
    assert "ELO LEADERBOARD" in output_str
    assert "COST SUMMARY" in output_str
    assert "STATISTICS" in output_str

    # Verify DUT names
    assert "dut1" in output_str
    assert "dut2" in output_str

    # Verify tasks and arenas
    assert "task1" in output_str or "task2" in output_str
    assert "arena1" in output_str or "arena2" in output_str

    # Verify metrics
    assert "10/2/1" in output_str or "5/8/2" in output_str  # W/L/T


def test_leaderboard_sorting():
    """Test that leaderboard is sorted by ELO."""
    from codegen_bench.core.judgment import JudgeVote, JudgmentResult

    # Create ratings without wins/losses/ties (computed on-demand)
    low_rating = DUTRating(
        dut_id="low",
        rating=BayesianELO(prior_mean=1400, prior_std=100),
    )
    high_rating = DUTRating(
        dut_id="high",
        rating=BayesianELO(prior_mean=1700, prior_std=100),
    )
    mid_rating = DUTRating(
        dut_id="mid",
        rating=BayesianELO(prior_mean=1500, prior_std=100),
    )

    # Add comparison history
    # Low: 0 wins, 5 losses
    for _ in range(5):
        comp = (
            "low",
            "high",
            "test",
            JudgmentResult(
                winner="B",
                votes=[JudgeVote(vote="B", reasoning="test", confidence=0.9)],
                agreement_rate=1.0,
                confidence=0.9,
            ),
        )
        low_rating._comparisons.append(comp)

    # High: 5 wins, 0 losses
    for _ in range(5):
        comp = (
            "high",
            "low",
            "test",
            JudgmentResult(
                winner="A",
                votes=[JudgeVote(vote="A", reasoning="test", confidence=0.9)],
                agreement_rate=1.0,
                confidence=0.9,
            ),
        )
        high_rating._comparisons.append(comp)

    # Mid: 2 wins, 2 losses, 1 tie
    for _ in range(2):
        comp = (
            "mid",
            "low",
            "test",
            JudgmentResult(
                winner="A",
                votes=[JudgeVote(vote="A", reasoning="test", confidence=0.9)],
                agreement_rate=1.0,
                confidence=0.9,
            ),
        )
        mid_rating._comparisons.append(comp)

    for _ in range(2):
        comp = (
            "mid",
            "high",
            "test",
            JudgmentResult(
                winner="B",
                votes=[JudgeVote(vote="B", reasoning="test", confidence=0.9)],
                agreement_rate=1.0,
                confidence=0.9,
            ),
        )
        mid_rating._comparisons.append(comp)

    comp = (
        "mid",
        "low",
        "test",
        JudgmentResult(
            winner="TIE",
            votes=[JudgeVote(vote="TIE", reasoning="test", confidence=0.9)],
            agreement_rate=1.0,
            confidence=0.9,
        ),
    )
    mid_rating._comparisons.append(comp)

    ratings = {
        "low": low_rating,
        "high": high_rating,
        "mid": mid_rating,
    }

    result = TournamentResult(
        ratings=ratings,
        comparisons=[],
        tasks_evaluated=["task1"],
        arenas=["arena1"],
        total_comparisons=0,
        total_cost_usd=0.0,
        start_time=0.0,
        end_time=1.0,
    )

    leaderboard = result.get_leaderboard()

    # Should be sorted high -> mid -> low
    assert leaderboard[0].dut_id == "high"
    assert leaderboard[1].dut_id == "mid"
    assert leaderboard[2].dut_id == "low"
