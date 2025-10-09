#!/usr/bin/env python3
"""Quick evaluation configuration - fast results with minimal cost.

This configuration is suitable for:
- Rapid prototyping and iteration
- Testing new DUT implementations
- CI/CD integration
- Getting quick feedback on relative performance

Trade-offs:
- Fewer tasks (5 instead of 20+)
- Single sample per pairing (less statistical power)
- Single arena (less comprehensive evaluation)
- Estimated cost: $2-5 per tournament
- Estimated time: 5-10 minutes
"""

from pathlib import Path

from codegen_bench.cache.store import SolutionCache
from codegen_bench.core.arena import Arena
from codegen_bench.core.task import Task
from codegen_bench.core.tournament import TournamentRunner
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.judge.orchestrator import JudgeOrchestrator

# ============================================================================
# Configuration Parameters
# ============================================================================

# DUTs to evaluate
DUTS = [
    "simple_chat_claude",
    "simple_chat_gpt4o",
]

# Minimal task set - one from each major language/domain
TASK_IDS = [
    "task_006",  # C - zstd (performance)
    "task_007",  # Rust - ripgrep (bugfix)
    "task_015",  # Go - containerd (feature)
]

# Single arena for speed
ARENA_NAMES = ["correctness"]

# Minimal sampling (less statistical power, but fast)
SAMPLES_PER_PAIRING = 1

# Output configuration
OUTPUT_DIR = Path("./results/quick")
CACHE_DIR = Path(".cache/solutions")
CHECKPOINT_DIR = None  # No checkpointing for quick runs
CHECKPOINT_INTERVAL = 10

# ============================================================================
# Setup
# ============================================================================

def create_tournament() -> TournamentRunner:
    """Create tournament with quick evaluation configuration."""
    registry = DUTRegistry()
    duts = [registry.get(dut_id) for dut_id in DUTS]

    tasks_dir = Path("tasks/core")
    tasks = []
    for task_id in TASK_IDS:
        task_file = tasks_dir / f"{task_id}.yaml"
        task = Task.from_yaml_file(task_file)
        tasks.append(task)

    arenas = [Arena(name=name) for name in ARENA_NAMES]

    judges = JudgeOrchestrator(
        num_judges=3,
        consensus_threshold=2,
    )

    cache = SolutionCache(cache_dir=CACHE_DIR)

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
    """Run quick evaluation tournament."""
    print("Running QUICK EVALUATION tournament...")
    print(f"  Tasks: {len(TASK_IDS)}")
    print(f"  DUTs: {len(DUTS)}")
    print(f"  Arenas: {len(ARENA_NAMES)}")
    print(f"  Samples: {SAMPLES_PER_PAIRING}")
    print()

    tournament = create_tournament()

    result = tournament.run(
        progress_callback=lambda c: print(f"  Progress: {c} comparisons", flush=True),
        output_dir=OUTPUT_DIR,
        checkpoint_dir=CHECKPOINT_DIR,
    )

    print("\n" + "="*60)
    print("QUICK EVALUATION RESULTS")
    print("="*60)
    print(f"Comparisons: {result.total_comparisons}")
    print(f"Cost: ${result.total_cost_usd:.2f}")
    print(f"Time: {result.duration_seconds:.1f}s")
    print("\nLEADERBOARD:")
    for i, rating in enumerate(result.get_leaderboard(), 1):
        print(f"  {i}. {rating.dut_id}: {rating.elo:.1f}±{rating.elo_std:.1f}")


if __name__ == "__main__":
    main()
