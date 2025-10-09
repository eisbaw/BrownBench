#!/usr/bin/env python3
"""Default tournament configuration - balanced settings for general use.

This configuration is suitable for:
- Initial exploration of the benchmark
- Comparing 2-4 DUTs
- Getting reliable results with moderate cost
- Tasks from multiple domains
"""

from pathlib import Path

from codegen_bench.cache.store import SolutionCache
from codegen_bench.core.arena import Arena
from codegen_bench.core.task import Task
from codegen_bench.core.tournament import TournamentRunner
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.judge.orchestrator import JudgeOrchestrator

# ============================================================================
# Configuration Parameters
# ============================================================================

# DUTs to evaluate
DUTS = [
    "simple_chat_claude",  # SimpleChatDUT with Claude 3.5 Sonnet
    "simple_chat_gpt4o",   # SimpleChatDUT with GPT-4o
]

# Tasks to evaluate (mix of difficulties and domains)
TASK_IDS = [
    "task_006",  # zstd - refactor (medium, C)
    "task_007",  # ripgrep - bugfix (medium, Rust)
    "task_008",  # jq - feature (medium, C)
    "task_014",  # openssh - security (medium, C)
    "task_015",  # containerd - feature (medium, Go)
]

# Arenas (quality dimensions to evaluate)
ARENA_NAMES = [
    "correctness",      # Does the code work?
    "maintainability",  # Is it clean and readable?
]

# Sampling configuration
SAMPLES_PER_PAIRING = 3  # Number of solutions generated per (DUT, task) pair

# Output configuration
OUTPUT_DIR = Path("./results")
CACHE_DIR = Path(".cache/solutions")
CHECKPOINT_DIR = Path(".checkpoints")
CHECKPOINT_INTERVAL = 10  # Save checkpoint every N comparisons

# ============================================================================
# Setup
# ============================================================================

def create_tournament() -> TournamentRunner:
    """Create tournament with default configuration.

    Returns:
        Configured TournamentRunner instance
    """
    # Load DUTs
    registry = DUTRegistry()
    duts = [registry.get(dut_id) for dut_id in DUTS]

    # Load tasks
    tasks_dir = Path("tasks/core")
    tasks = []
    for task_id in TASK_IDS:
        task_file = tasks_dir / f"{task_id}.yaml"
        if task_file.exists():
            task = Task.from_yaml_file(task_file)
            tasks.append(task)
        else:
            raise FileNotFoundError(f"Task file not found: {task_file}")

    # Create arenas
    arenas = [Arena(name=name) for name in ARENA_NAMES]

    # Initialize judge orchestrator
    # NOTE: Requires ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable
    judges = JudgeOrchestrator(
        num_judges=3,  # Use 3 judges for consensus
        consensus_threshold=2,  # At least 2 must agree
    )

    # Initialize solution cache
    cache = SolutionCache(cache_dir=CACHE_DIR)

    # Create tournament
    tournament = TournamentRunner(
        duts=duts,
        tasks=tasks,
        judges=judges,
        arenas=arenas,
        cache=cache,
        samples_per_pairing=SAMPLES_PER_PAIRING,
    )

    return tournament


def main() -> None:
    """Run tournament with default configuration."""
    tournament = create_tournament()

    # Run tournament with progress tracking
    def progress_callback(count: int) -> None:
        print(f"Completed {count} comparisons...", flush=True)

    result = tournament.run(
        progress_callback=progress_callback,
        output_dir=OUTPUT_DIR,
        checkpoint_dir=CHECKPOINT_DIR,
        checkpoint_interval=CHECKPOINT_INTERVAL,
    )

    # Print summary
    print("\n" + "="*80)
    print("TOURNAMENT RESULTS")
    print("="*80)
    print(f"\nTotal comparisons: {result.total_comparisons}")
    print(f"Total cost: ${result.total_cost_usd:.2f}")
    print(f"Duration: {result.duration_seconds:.1f}s")

    print("\n" + "-"*80)
    print("LEADERBOARD")
    print("-"*80)
    for i, rating in enumerate(result.get_leaderboard(), 1):
        print(f"{i}. {rating.dut_id}")
        print(f"   ELO: {rating.elo:.1f} ± {rating.elo_std:.1f}")
        print(f"   W/L/T: {rating.wins}/{rating.losses}/{rating.ties}")
        print(f"   Cost: ${rating.total_cost_usd:.4f}")

    if result.errors:
        print("\n" + "-"*80)
        print(f"ERRORS ({len(result.errors)} total)")
        print("-"*80)
        for error in result.errors[:5]:  # Show first 5 errors
            print(f"- {error.phase}: {error.error_type} - {error.error_message[:100]}")


if __name__ == "__main__":
    main()
