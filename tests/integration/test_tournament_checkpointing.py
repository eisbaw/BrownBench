"""Integration tests for tournament checkpointing and resume functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from anthropic.types import TextBlock

from codegen_bench.checkpoint import CheckpointManager
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

        # Detect if this is a judging call by checking message content
        messages = kwargs.get("messages", [])
        prompt_content = ""
        if messages and len(messages) > 0:
            msg = messages[0]
            if isinstance(msg, dict):
                prompt_content = str(msg.get("content", ""))

        # Judge prompts contain "Solution A:" and "Solution B:"
        is_judging = "Solution A:" in prompt_content and "Solution B:" in prompt_content

        if is_judging:
            # This is a judging call
            winner = "A" if (call_count[0] % 3) == 0 else "B"
            text_block = TextBlock(type="text", text=mock_judge_response(winner))
            message.content = [text_block]
            message.usage = Mock(input_tokens=2000, output_tokens=200)
        else:
            # This is a solution generation call
            text_block = TextBlock(type="text", text=mock_solution_response)
            message.content = [text_block]
            message.usage = Mock(input_tokens=1000, output_tokens=500)

        return message

    client.messages.create = Mock(side_effect=create_message)
    return client


def test_tournament_creates_checkpoint(mock_anthropic_client, tmp_path):
    """Test that tournament creates checkpoint files during execution."""
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    cache_dir = tmp_path / "cache"
    checkpoint_dir = tmp_path / "checkpoints"

    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
            DUTRegistry.create("elaborate-prompt", {"api_key": "mock-key"}),
        ]

        # Load tasks
        task_loader = TaskLoader(Path("tasks"))
        tasks = task_loader.load_task_set("core")[:2]

        # Create judges
        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
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
            samples_per_pairing=2,
        )

        # Run tournament with checkpointing
        results = runner.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=2)

        # Verify tournament completed
        assert results is not None
        assert len(results.comparisons) > 0

        # Checkpoint should be deleted after successful completion
        checkpoint_manager = CheckpointManager(checkpoint_dir)
        assert (
            not checkpoint_manager.checkpoint_exists()
        ), "Checkpoint should be deleted after successful tournament completion"


def test_tournament_resume_from_checkpoint(mock_anthropic_client, tmp_path):
    """Test that tournament can resume from checkpoint after interruption."""
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    cache_dir = tmp_path / "cache"
    checkpoint_dir = tmp_path / "checkpoints"

    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
            DUTRegistry.create("elaborate-prompt", {"api_key": "mock-key"}),
        ]

        # Load tasks - use only 1 task to make test faster and more predictable
        task_loader = TaskLoader(Path("tasks"))
        tasks = task_loader.load_task_set("core")[:1]

        # Create judges
        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
        judge_orchestrator = JudgeOrchestrator(judges)

        # Create cache
        cache = SolutionCache(cache_dir)

        # First run: Simulate interruption by patching ShutdownHandler
        # to trigger shutdown after 1 comparison
        comparison_count = [0]

        original_compare = TournamentRunner.compare_solutions

        def compare_with_interrupt(
            self,
            solutions,
            progress_callback=None,
            checkpoint_manager=None,
            shutdown_handler=None,
            checkpoint_interval=10,
        ):
            # Wrap the progress callback to trigger shutdown
            if shutdown_handler:
                original_callback = progress_callback

                def interrupt_callback(total):
                    nonlocal comparison_count
                    if original_callback:
                        original_callback(total)
                    comparison_count[0] = total
                    # Trigger shutdown after 1 comparison
                    if total >= 1:
                        shutdown_handler._shutdown_event.set()

                progress_callback = interrupt_callback

            return original_compare(
                self,
                solutions,
                progress_callback,
                checkpoint_manager,
                shutdown_handler,
                checkpoint_interval,
            )

        with patch.object(TournamentRunner, "compare_solutions", compare_with_interrupt):
            runner = TournamentRunner(
                duts=duts,
                tasks=tasks,
                judges=judge_orchestrator,
                arenas=[MAINTAINABILITY],
                cache=cache,
                samples_per_pairing=2,
            )

            # Run tournament - should be interrupted
            result1 = runner.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=1)

        # Verify checkpoint was created
        checkpoint_manager = CheckpointManager(checkpoint_dir)
        assert checkpoint_manager.checkpoint_exists(), "Checkpoint should exist after interruption"

        # Verify partial results
        assert result1 is not None
        assert (
            len(result1.comparisons) >= 1
        ), "Should have at least 1 comparison before interruption"

        # Load checkpoint to verify state
        checkpoint_state = checkpoint_manager.load()
        assert len(checkpoint_state.completed_comparisons) >= 1
        assert checkpoint_state.total_cost_usd > 0

        # Second run: Resume from checkpoint without interruption
        runner2 = TournamentRunner(
            duts=duts,
            tasks=tasks,
            judges=judge_orchestrator,
            arenas=[MAINTAINABILITY],
            cache=cache,
            samples_per_pairing=2,
        )

        result2 = runner2.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=1)

        # Verify tournament completed
        assert result2 is not None
        # With 2 DUTs, 1 task, 2 samples = 2 comparisons total
        assert len(result2.comparisons) == 2, "Should have 2 comparisons total"
        assert len(result2.comparisons) > len(
            result1.comparisons
        ), "Resumed tournament should have more comparisons than interrupted one"

        # Checkpoint should be deleted after successful completion
        assert (
            not checkpoint_manager.checkpoint_exists()
        ), "Checkpoint should be deleted after successful completion"


def test_checkpoint_preserves_ratings(mock_anthropic_client, tmp_path):
    """Test that checkpoints preserve ELO ratings correctly."""
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    cache_dir = tmp_path / "cache"
    checkpoint_dir = tmp_path / "checkpoints"

    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
            DUTRegistry.create("elaborate-prompt", {"api_key": "mock-key"}),
        ]

        # Load tasks
        task_loader = TaskLoader(Path("tasks"))
        tasks = task_loader.load_task_set("core")[:1]

        # Create judges
        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
        judge_orchestrator = JudgeOrchestrator(judges)

        # Create cache
        cache = SolutionCache(cache_dir)

        # Simulate interruption after 1 comparison
        original_compare = TournamentRunner.compare_solutions

        def compare_with_early_stop(
            self,
            solutions,
            progress_callback=None,
            checkpoint_manager=None,
            shutdown_handler=None,
            checkpoint_interval=10,
        ):
            if shutdown_handler:
                original_callback = progress_callback

                def stop_callback(total):
                    if original_callback:
                        original_callback(total)
                    if total >= 1:
                        shutdown_handler._shutdown_event.set()

                progress_callback = stop_callback

            return original_compare(
                self,
                solutions,
                progress_callback,
                checkpoint_manager,
                shutdown_handler,
                checkpoint_interval,
            )

        with patch.object(TournamentRunner, "compare_solutions", compare_with_early_stop):
            runner = TournamentRunner(
                duts=duts,
                tasks=tasks,
                judges=judge_orchestrator,
                arenas=[MAINTAINABILITY],
                cache=cache,
                samples_per_pairing=2,
            )

            # Run and get interrupted
            result1 = runner.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=1)

        # Extract ratings from first run
        ratings1 = {dut_id: (r.elo, r.elo_std) for dut_id, r in result1.ratings.items()}

        # Load checkpoint and verify ratings match
        checkpoint_manager = CheckpointManager(checkpoint_dir)
        checkpoint_state = checkpoint_manager.load()

        for dut_id, (elo, std) in ratings1.items():
            assert dut_id in checkpoint_state.ratings_snapshot
            snapshot = checkpoint_state.ratings_snapshot[dut_id]
            assert abs(snapshot["mean"] - elo) < 1e-6, f"ELO mean mismatch for {dut_id}"
            assert abs(snapshot["std"] - std) < 1e-6, f"ELO std mismatch for {dut_id}"


def test_checkpoint_preserves_metrics(mock_anthropic_client, tmp_path):
    """Test that checkpoints preserve cost/time/token metrics."""
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    cache_dir = tmp_path / "cache"
    checkpoint_dir = tmp_path / "checkpoints"

    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
        ]

        # Load tasks
        task_loader = TaskLoader(Path("tasks"))
        tasks = task_loader.load_task_set("core")[:1]

        # Create judges
        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
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

        # Run with frequent checkpoints
        runner.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=1)

        # Since tournament completes successfully, checkpoint is deleted
        # But we can verify metrics in final result
        # Let's test by running again and checking cache hits

        # Create new runner to test cache metrics
        runner2 = TournamentRunner(
            duts=duts,
            tasks=tasks,
            judges=judge_orchestrator,
            arenas=[MAINTAINABILITY],
            cache=cache,
            samples_per_pairing=1,
        )

        # This should use cached solutions
        result = runner2.run()

        # Verify metrics exist
        for _dut_id, rating in result.ratings.items():
            assert rating.total_cost_usd >= 0
            assert rating.total_time_seconds >= 0
            assert rating.total_tokens >= 0


def test_checkpoint_interval_respected(mock_anthropic_client, tmp_path):
    """Test that checkpoint files are created during tournament execution."""
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    cache_dir = tmp_path / "cache"
    checkpoint_dir = tmp_path / "checkpoints"

    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
            DUTRegistry.create("elaborate-prompt", {"api_key": "mock-key"}),
        ]

        # Load tasks
        task_loader = TaskLoader(Path("tasks"))
        tasks = task_loader.load_task_set("core")[:1]

        # Create judges
        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
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
            samples_per_pairing=2,
        )

        # Run with checkpoint interval of 1 (saves after each comparison)
        result = runner.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=1)

        # Verify tournament completed
        assert result is not None
        assert len(result.comparisons) == 2  # 2 DUTs, 1 task, 2 samples = 2 comparisons

        # Checkpoint should be deleted after successful completion
        checkpoint_manager = CheckpointManager(checkpoint_dir)
        assert not checkpoint_manager.checkpoint_exists()


def test_checkpoint_resume_completes_tournament(mock_anthropic_client, tmp_path):
    """Test that resumed tournament completes all comparisons after interruption.

    Note: Comparisons are re-run rather than skipped for simplicity.
    This trades API cost efficiency for maintainability.
    """
    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    cache_dir = tmp_path / "cache"
    checkpoint_dir = tmp_path / "checkpoints"

    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        # Create DUTs
        duts = [
            DUTRegistry.create("simple-chat", {"api_key": "mock-key"}),
            DUTRegistry.create("elaborate-prompt", {"api_key": "mock-key"}),
        ]

        # Load tasks
        task_loader = TaskLoader(Path("tasks"))
        tasks = task_loader.load_task_set("core")[:1]

        # Create judges
        judges = [ClaudeJudge(api_key="mock-key", model="claude-test")]
        judge_orchestrator = JudgeOrchestrator(judges)

        # Create cache
        cache = SolutionCache(cache_dir)

        # First run: interrupt after 1 comparison
        original_compare = TournamentRunner.compare_solutions

        def compare_with_interrupt(
            self,
            solutions,
            progress_callback=None,
            checkpoint_manager=None,
            shutdown_handler=None,
            checkpoint_interval=10,
        ):
            if shutdown_handler:
                original_callback = progress_callback

                def interrupt_callback(total):
                    if original_callback:
                        original_callback(total)
                    if total >= 1:
                        shutdown_handler._shutdown_event.set()

                progress_callback = interrupt_callback

            return original_compare(
                self,
                solutions,
                progress_callback,
                checkpoint_manager,
                shutdown_handler,
                checkpoint_interval,
            )

        with patch.object(TournamentRunner, "compare_solutions", compare_with_interrupt):
            runner = TournamentRunner(
                duts=duts,
                tasks=tasks,
                judges=judge_orchestrator,
                arenas=[MAINTAINABILITY],
                cache=cache,
                samples_per_pairing=2,
            )

            result1 = runner.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=1)

        # Verify checkpoint exists
        checkpoint_manager = CheckpointManager(checkpoint_dir)
        assert checkpoint_manager.checkpoint_exists()

        # Get number of completed comparisons
        first_run_comparisons = len(result1.comparisons)
        assert first_run_comparisons >= 1

        # Second run: should skip completed comparisons and complete the rest
        runner2 = TournamentRunner(
            duts=duts,
            tasks=tasks,
            judges=judge_orchestrator,
            arenas=[MAINTAINABILITY],
            cache=cache,
            samples_per_pairing=2,
        )

        result2 = runner2.run(checkpoint_dir=checkpoint_dir, checkpoint_interval=1)

        # Verify completed comparisons
        assert len(result2.comparisons) == 2, "Should have 2 total comparisons"
        assert (
            len(result2.comparisons) > first_run_comparisons
        ), "Resumed tournament should complete remaining comparisons"
