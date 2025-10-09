#!/usr/bin/env python3
"""Run mini-tournament with 2 DUTs and 5 tasks for validation."""

import logging
import os
import sys
from pathlib import Path

import structlog

from codegen_bench.cache.store import SolutionCache
from codegen_bench.core.arena import MAINTAINABILITY
from codegen_bench.core.tournament import TournamentRunner
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.judge.claude_judge import ClaudeJudge
from codegen_bench.judge.orchestrator import JudgeOrchestrator
from codegen_bench.tasks.loader import TaskLoader

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = structlog.get_logger()


def main():
    """Run mini-tournament."""
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    logger.info("Starting mini-tournament")
    logger.info("DUTs: simple-chat, elaborate-prompt")
    logger.info("Tasks: task_006-010 (5 tasks)")
    logger.info("Arena: MAINTAINABILITY")
    logger.info("Samples per pairing: 1")

    # Create DUTs
    logger.info("Creating DUTs...")
    duts = [
        DUTRegistry.create("simple-chat", {"api_key": api_key}),
        DUTRegistry.create("elaborate-prompt", {"api_key": api_key}),
    ]
    logger.info(f"Created {len(duts)} DUTs")

    # Load tasks
    logger.info("Loading tasks...")
    task_loader = TaskLoader(Path("tasks"))
    all_tasks = task_loader.load_task_set("core")

    # Filter to tasks 006-010
    task_ids = [f"task_{i:03d}" for i in range(6, 11)]
    tasks = [t for t in all_tasks if t.id in task_ids]

    if len(tasks) != 5:
        logger.error(f"Expected 5 tasks, found {len(tasks)}")
        logger.error(f"Available tasks: {[t.id for t in all_tasks]}")
        sys.exit(1)

    logger.info(f"Loaded {len(tasks)} tasks: {[t.id for t in tasks]}")

    # Create judges
    logger.info("Creating judges...")
    judges = [
        ClaudeJudge(api_key=api_key, model="claude-sonnet-4-20250514"),
    ]
    judge_orchestrator = JudgeOrchestrator(judges)
    logger.info(f"Created {len(judges)} judge(s)")

    # Create cache
    cache_dir = Path.home() / ".cache" / "codegen-bench"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = SolutionCache(cache_dir)
    logger.info(f"Using cache directory: {cache_dir}")

    # Create tournament runner
    logger.info("Creating tournament runner...")
    runner = TournamentRunner(
        duts=duts,
        tasks=tasks,
        judges=judge_orchestrator,
        arenas=[MAINTAINABILITY],
        cache=cache,
        samples_per_pairing=1,  # Keep it fast for validation
    )

    # Progress callback
    def progress(total_comparisons: int):
        logger.info(f"Completed {total_comparisons} comparisons")

    # Run tournament
    logger.info("Running tournament...")
    output_dir = Path("tournament_results")
    results = runner.run(progress_callback=progress, output_dir=output_dir)

    # Display results
    logger.info("Tournament complete!")
    logger.info(f"Total comparisons: {results.total_comparisons}")
    logger.info(f"Total cost: ${results.total_cost_usd:.4f}")
    logger.info(f"Duration: {results.duration_seconds:.2f}s")

    # Show leaderboard
    logger.info("\n" + "=" * 60)
    logger.info("LEADERBOARD")
    logger.info("=" * 60)

    for i, rating in enumerate(results.get_leaderboard(), start=1):
        logger.info(
            f"{i}. {rating.dut_id:20s} | "
            f"ELO: {rating.elo:6.1f} ± {rating.elo_std:5.1f} | "
            f"W/L/T: {rating.wins}/{rating.losses}/{rating.ties} | "
            f"Cost: ${rating.total_cost_usd:.4f}"
        )

    logger.info("=" * 60)
    logger.info(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
