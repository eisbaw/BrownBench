#!/usr/bin/env python3
"""Full research configuration - comprehensive evaluation with high statistical power.

This configuration is suitable for:
- Academic research and publications
- Comprehensive DUT comparisons
- Final production evaluation
- When cost is less of a concern than statistical validity

Features:
- All 26 tasks across diverse domains
- High sample count (5 per pairing) for statistical power
- Multiple arenas for comprehensive quality assessment
- Checkpointing for long-running tournaments
- Estimated cost: $50-200 per tournament
- Estimated time: 2-4 hours
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

# DUTs to evaluate - can include multiple approaches
DUTS = [
    "simple_chat_claude",
    "simple_chat_gpt4o",
    "elaborate_prompt_claude",  # If available
]

# Full task set - all 26 tasks for comprehensive coverage
TASK_IDS = [
    # Original tasks
    "task_001", "task_002", "task_003", "task_004", "task_005",
    # Phase 1 tasks
    "task_006", "task_007", "task_008", "task_009", "task_010",
    "task_011", "task_012", "task_013", "task_014", "task_015",
    "task_016", "task_017", "task_018", "task_019", "task_020",
    "task_021",
    # New tasks
    "task_022", "task_023", "task_024", "task_025", "task_026",
]

# Multiple arenas for comprehensive quality assessment
ARENA_NAMES = [
    "correctness",      # Does it work correctly?
    "maintainability",  # Is it clean and readable?
    "performance",      # Is it efficient?
    "robustness",       # Does it handle edge cases?
]

# High sampling for statistical power
SAMPLES_PER_PAIRING = 5  # Generate 5 solutions per (DUT, task) pair

# Output configuration
OUTPUT_DIR = Path("./results/full_research")
CACHE_DIR = Path(".cache/solutions")
CHECKPOINT_DIR = Path(".checkpoints/full_research")  # Important for long runs
CHECKPOINT_INTERVAL = 20  # Save every 20 comparisons

# ============================================================================
# Setup
# ============================================================================

def create_tournament() -> TournamentRunner:
    """Create tournament with full research configuration.

    Returns:
        Configured TournamentRunner instance
    """
    registry = DUTRegistry()
    duts = []
    for dut_id in DUTS:
        try:
            dut = registry.get(dut_id)
            duts.append(dut)
        except KeyError:
            print(f"Warning: DUT '{dut_id}' not found, skipping")

    tasks_dir = Path("tasks/core")
    tasks = []
    for task_id in TASK_IDS:
        task_file = tasks_dir / f"{task_id}.yaml"
        if task_file.exists():
            task = Task.from_yaml_file(task_file)
            tasks.append(task)
        else:
            print(f"Warning: Task file not found: {task_file}")

    arenas = [Arena(name=name) for name in ARENA_NAMES]

    # Higher judge consensus for research quality
    judges = JudgeOrchestrator(
        num_judges=5,  # Use 5 judges for stronger consensus
        consensus_threshold=3,  # Require 3/5 to agree
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
    """Run full research tournament."""
    print("="*80)
    print("FULL RESEARCH TOURNAMENT")
    print("="*80)
    print(f"\n  Tasks: {len(TASK_IDS)} (all available)")
    print(f"  DUTs: {len(DUTS)}")
    print(f"  Arenas: {len(ARENA_NAMES)} (comprehensive)")
    print(f"  Samples per pairing: {SAMPLES_PER_PAIRING} (high statistical power)")
    print(f"  Checkpointing: ENABLED ({CHECKPOINT_DIR})")
    print("\nThis will be a comprehensive evaluation.")
    print("Estimated time: 2-4 hours")
    print("Estimated cost: $50-200 depending on DUTs")
    print()

    # Create tournament
    tournament = create_tournament()

    # Progress tracking
    comparison_count = [0]
    total_expected = len(DUTS) * (len(DUTS) - 1) // 2 * len(TASK_IDS) * len(ARENA_NAMES)

    def progress_callback(count: int) -> None:
        comparison_count[0] = count
        pct = (count / total_expected * 100) if total_expected > 0 else 0
        print(f"  Progress: {count}/{total_expected} comparisons ({pct:.1f}%)", flush=True)

    # Run tournament with checkpointing
    result = tournament.run(
        progress_callback=progress_callback,
        output_dir=OUTPUT_DIR,
        checkpoint_dir=CHECKPOINT_DIR,
        checkpoint_interval=CHECKPOINT_INTERVAL,
    )

    # Comprehensive summary
    print("\n" + "="*80)
    print("FULL RESEARCH TOURNAMENT RESULTS")
    print("="*80)
    print(f"\nMetadata:")
    print(f"  Total comparisons: {result.total_comparisons}")
    print(f"  Total cost: ${result.total_cost_usd:.2f}")
    print(f"  Duration: {result.duration_seconds/60:.1f} minutes")
    print(f"  Tasks evaluated: {len(result.tasks_evaluated)}")
    print(f"  Arenas: {', '.join(result.arenas)}")

    if result.errors:
        print(f"\n  Errors encountered: {len(result.errors)}")
        print("  (See full results for error details)")

    print("\n" + "-"*80)
    print("FINAL LEADERBOARD")
    print("-"*80)
    for i, rating in enumerate(result.get_leaderboard(), 1):
        print(f"\n{i}. {rating.dut_id}")
        print(f"   ELO Rating: {rating.elo:.1f} ± {rating.elo_std:.1f}")
        print(f"   95% CI: [{rating.elo_lower_bound:.1f}, {rating.elo_upper_bound:.1f}]")
        print(f"   Record: {rating.wins}W / {rating.losses}L / {rating.ties}T")
        print(f"   Cost: ${rating.total_cost_usd:.2f}")
        print(f"   Time: {rating.total_time_seconds:.1f}s")
        print(f"   Tokens: {rating.total_tokens:,}")

    print("\n" + "="*80)
    print(f"Results saved to: {OUTPUT_DIR}")
    print("="*80)


if __name__ == "__main__":
    main()
