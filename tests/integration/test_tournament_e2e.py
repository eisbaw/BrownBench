"""End-to-end tournament integration test."""

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
REASONING: Solution {winner} is better because it has clearer code.
CONFIDENCE: 0.85"""

    return _response


@pytest.fixture
def mock_solution_response():
    """Mock LLM solution response."""
    return """```c:src/hello.c
#include "hello.h"
#include <stdio.h>

int hello_world() {
    printf("Hello, World!\\n");
    return 0;
}
```

```c:src/hello.h
#ifndef HELLO_H
#define HELLO_H

int hello_world(void);

#endif
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

        # First few calls are solution generation
        if call_count[0] <= 10:  # Enough for multiple solutions
            text_block = TextBlock(type="text", text=mock_solution_response)
            message.content = [text_block]
            message.usage = Mock(input_tokens=1000, output_tokens=500)
        else:
            # Later calls are judging
            # Alternate winners to create interesting ELO results
            winner = "A" if (call_count[0] % 3) == 0 else "B"
            text_block = TextBlock(type="text", text=mock_judge_response(winner))
            message.content = [text_block]
            message.usage = Mock(input_tokens=2000, output_tokens=200)

        return message

    client.messages.create = Mock(side_effect=create_message)
    return client


def test_tournament_end_to_end_mocked(mock_anthropic_client, tmp_path):
    """Test complete tournament flow with mocked API calls.

    This test verifies:
    1. Multiple DUTs can compete
    2. Solutions are generated for each task
    3. Judges compare solutions
    4. ELO ratings are calculated
    5. Leaderboard is generated
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

        # Load tasks (use only 2 for speed)
        task_loader = TaskLoader(Path("tasks"))
        all_tasks = task_loader.load_task_set("core")
        tasks = all_tasks[:2]

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
            samples_per_pairing=2,  # Low for speed
        )

        # Run tournament
        results = runner.run()

        # Verify results structure
        assert results is not None
        assert hasattr(results, "ratings")
        assert hasattr(results, "comparisons")
        assert hasattr(results, "tasks_evaluated")

        # Verify we have ratings for both DUTs
        ratings = results.ratings
        assert len(ratings) == 2
        assert "simple-chat" in ratings
        assert "elaborate-prompt" in ratings

        # Check each rating has ELO data
        for _, rating in ratings.items():
            assert hasattr(rating, "elo")
            assert hasattr(rating, "wins")
            assert hasattr(rating, "losses")
            assert hasattr(rating, "ties")

        # Verify comparisons exist
        comparisons = results.comparisons
        assert len(comparisons) > 0

        # Each comparison is a tuple: (dut_a, dut_b, arena, judgment_result)
        for comp in comparisons:
            assert len(comp) == 4
            dut_a, dut_b, arena, judgment = comp
            assert dut_a in ["simple-chat", "elaborate-prompt"]
            assert dut_b in ["simple-chat", "elaborate-prompt"]
            assert arena == MAINTAINABILITY.name
            assert judgment.winner in ["A", "B", "TIE"]

        # Verify tasks were evaluated
        assert len(results.tasks_evaluated) == 2


def test_tournament_dut_registry():
    """Test that both DUTs are registered."""
    available_duts = DUTRegistry.list_available()
    assert "simple-chat" in available_duts
    assert "elaborate-prompt" in available_duts


def test_tournament_can_create_duts():
    """Test that DUTs can be created from registry."""
    config = {"api_key": "test-key"}

    simple_dut = DUTRegistry.create("simple-chat", config)
    assert simple_dut.get_metadata().id == "simple-chat"

    elaborate_dut = DUTRegistry.create("elaborate-prompt", config)
    assert elaborate_dut.get_metadata().id == "elaborate-prompt"


def test_tournament_runner_initialization(tmp_path):
    """Test TournamentRunner can be initialized with both DUTs."""
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    # Create DUTs
    duts = [
        DUTRegistry.create("simple-chat", {"api_key": "test-key"}),
        DUTRegistry.create("elaborate-prompt", {"api_key": "test-key"}),
    ]

    # Load tasks
    task_loader = TaskLoader(Path("tasks"))
    tasks = task_loader.load_task_set("core")[:1]

    # Create judges
    judges = [ClaudeJudge(api_key="test-key", model="claude-test")]
    judge_orchestrator = JudgeOrchestrator(judges)

    # Create cache
    cache = SolutionCache(tmp_path / "cache")

    runner = TournamentRunner(
        duts=duts,
        tasks=tasks,
        judges=judge_orchestrator,
        arenas=[MAINTAINABILITY],
        cache=cache,
        samples_per_pairing=1,
    )

    assert len(runner.duts) == 2
    assert runner.duts[0].get_metadata().id in ["simple-chat", "elaborate-prompt"]
    assert runner.duts[1].get_metadata().id in ["simple-chat", "elaborate-prompt"]
    assert runner.tasks is not None
    assert len(runner.tasks) >= 1  # At least task_001 should exist


def test_tournament_with_persistent_api_failures(tmp_path):
    """Test tournament graceful degradation with DUT API failures.

    Verifies that when all API calls fail, the tournament runner uses graceful
    degradation: it logs errors, records them in the result, and continues with
    partial results rather than crashing entirely.
    """
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    # Create mock client that always fails
    mock_client = Mock()
    mock_client.messages.create = Mock(side_effect=RuntimeError("API connection failed"))

    with patch("anthropic.Anthropic", return_value=mock_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
        ]

        # Load minimal task set
        task_loader = TaskLoader(Path("tasks"))
        tasks = task_loader.load_task_set("core")[:1]

        # Create judges
        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
        judge_orchestrator = JudgeOrchestrator(judges)

        # Create cache
        cache = SolutionCache(tmp_path / "cache")

        # Create tournament runner
        runner = TournamentRunner(
            duts=duts,
            tasks=tasks,
            judges=judge_orchestrator,
            arenas=[MAINTAINABILITY],
            cache=cache,
            samples_per_pairing=1,
        )

        # Tournament should complete with graceful degradation
        # It will record errors but not crash
        result = runner.run()

        # Verify result structure exists even with all failures
        assert result is not None
        assert hasattr(result, "errors")
        assert len(result.errors) > 0

        # Verify error was recorded properly
        error = result.errors[0]
        assert error.phase == "solution_generation"
        assert error.dut_id == "simple-chat"
        assert error.task_id == "task_001"
        assert "DUTAPIError" in error.error_type
        assert "API call failed" in error.error_message

        # No comparisons should have been made (no solutions generated)
        assert len(result.comparisons) == 0
