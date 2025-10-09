"""Mini-tournament test with 5 tasks for Phase 1 validation."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from anthropic.types import TextBlock

from codegen_bench.core.arena import MAINTAINABILITY
from codegen_bench.core.tournament import TournamentRunner
from codegen_bench.dut.registry import DUTRegistry


@pytest.fixture
def mock_judge_response():
    """Mock judge response."""

    def _response(winner="A"):
        return f"""WINNER: {winner}
REASONING: Solution {winner} demonstrates better code quality.
CONFIDENCE: 0.88"""

    return _response


@pytest.fixture
def mock_solution_response():
    """Mock LLM solution response."""
    return """```python:src/main.py
def example():
    '''Example implementation.'''
    return 42
```"""


@pytest.fixture
def mock_anthropic_client(mock_solution_response, mock_judge_response):
    """Mock Anthropic client for both generation and judging."""
    client = Mock()

    # Track call count to alternate between generation and judging
    call_count = [0]

    def create_message(**kwargs):
        call_count[0] += 1
        message = Mock()

        # First many calls are solution generation (2 DUTs x 5 tasks x 1 sample = 10)
        if call_count[0] <= 10:
            text_block = TextBlock(type="text", text=mock_solution_response)
            message.content = [text_block]
            message.usage = Mock(input_tokens=1500, output_tokens=600)
        else:
            # Later calls are judging
            # Vary winners to create diverse results
            winner = ["A", "B", "TIE"][call_count[0] % 3]
            text_block = TextBlock(type="text", text=mock_judge_response(winner))
            message.content = [text_block]
            message.usage = Mock(input_tokens=2500, output_tokens=250)

        return message

    client.messages.create = Mock(side_effect=create_message)
    return client


def test_mini_tournament_5_tasks(mock_anthropic_client, tmp_path):
    """Test mini-tournament with 2 DUTs and 5 tasks.

    This test validates Phase 1 requirements:
    - 2 DUTs: simple-chat and elaborate-prompt
    - 5 tasks: task_006 through task_010
    - 1 arena: MAINTAINABILITY
    - Verifies tournament runs to completion
    - Validates result structure and content
    """
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    # Create temporary cache directory
    cache_dir = tmp_path / "cache"

    # Patch Anthropic client in both DUTs and judges
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
            DUTRegistry.create("elaborate-prompt", {"api_key": "mock-key"}),
        ]
        assert len(duts) == 2

        # Load tasks 006-010
        task_loader = TaskLoader(Path("tasks"))
        all_tasks = task_loader.load_task_set("core")

        task_ids = [f"task_{i:03d}" for i in range(6, 11)]
        tasks = [t for t in all_tasks if t.id in task_ids]

        # Verify we have exactly 5 tasks
        assert len(tasks) == 5, f"Expected 5 tasks, got {len(tasks)}: {[t.id for t in tasks]}"
        assert all(t.id in task_ids for t in tasks)

        # Create judges
        judges = [
            ClaudeJudge(api_key="mock-key", model="claude-test"),
        ]
        judge_orchestrator = JudgeOrchestrator(judges)

        # Create cache
        cache = SolutionCache(cache_dir)

        # Create tournament runner
        runner = TournamentRunner(
            duts=duts,
            tasks=tasks,
            judges=judge_orchestrator,
            arenas=[MAINTAINABILITY],
            cache=cache,
            samples_per_pairing=1,
        )

        # Run tournament
        results = runner.run()

        # Validate results structure
        assert results is not None
        assert results.ratings is not None
        assert results.comparisons is not None
        assert results.tasks_evaluated is not None

        # Verify we have ratings for both DUTs
        assert len(results.ratings) == 2
        assert "simple-chat" in results.ratings
        assert "elaborate-prompt" in results.ratings

        # Check each DUT has complete rating data
        for dut_id, rating in results.ratings.items():
            assert rating.dut_id == dut_id
            assert hasattr(rating, "elo")
            assert hasattr(rating, "elo_std")
            assert hasattr(rating, "wins")
            assert hasattr(rating, "losses")
            assert hasattr(rating, "ties")
            assert rating.wins + rating.losses + rating.ties > 0

        # Verify comparisons
        # Expected: 1 comparison per (task x dut_pair x arena x sample)
        # = 5 tasks x 1 dut_pair x 1 arena x 1 sample = 5 comparisons
        assert len(results.comparisons) == 5

        for comp in results.comparisons:
            dut_a, dut_b, arena, judgment = comp
            assert dut_a in ["simple-chat", "elaborate-prompt"]
            assert dut_b in ["simple-chat", "elaborate-prompt"]
            assert dut_a != dut_b
            assert arena == MAINTAINABILITY.name
            assert judgment.winner in ["A", "B", "TIE"]

        # Verify all 5 tasks were evaluated
        assert len(results.tasks_evaluated) == 5
        for task_id in task_ids:
            assert task_id in results.tasks_evaluated

        # Verify tournament metadata
        assert results.total_comparisons == 5
        assert results.total_cost_usd >= 0
        assert results.duration_seconds >= 0

        # Verify leaderboard can be generated
        leaderboard = results.get_leaderboard()
        assert len(leaderboard) == 2
        # Leaderboard should be sorted by ELO descending
        assert leaderboard[0].elo >= leaderboard[1].elo

        # Test serialization
        result_dict = results.to_dict()
        assert "ratings" in result_dict
        assert "comparisons" in result_dict
        assert "leaderboard" in result_dict
        assert "tournament_metadata" in result_dict

        # Test saving
        output_file = results.save(tmp_path / "results")
        assert output_file.exists()
        assert output_file.name == "tournament.yaml"


def test_mini_tournament_solution_caching(mock_anthropic_client, tmp_path):
    """Test that solutions are properly cached during tournament."""
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    cache_dir = tmp_path / "cache"

    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
        ]

        task_loader = TaskLoader(Path("tasks"))
        all_tasks = task_loader.load_task_set("core")
        tasks = [t for t in all_tasks if t.id == "task_006"]

        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
        judge_orchestrator = JudgeOrchestrator(judges)

        cache = SolutionCache(cache_dir)

        runner = TournamentRunner(
            duts=duts,
            tasks=tasks,
            judges=judge_orchestrator,
            arenas=[MAINTAINABILITY],
            cache=cache,
            samples_per_pairing=2,
        )

        # Run tournament - should generate solutions
        runner.run()

        # Verify solutions were cached
        dut = duts[0]
        task = tasks[0]

        # Check both samples are cached
        cached_1 = cache.get(dut, task, 42)
        cached_2 = cache.get(dut, task, 43)

        assert cached_1 is not None
        assert cached_2 is not None
        assert cached_1.task_id == task.id
        assert cached_2.task_id == task.id
