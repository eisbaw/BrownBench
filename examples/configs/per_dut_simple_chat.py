#!/usr/bin/env python3
"""Per-DUT configuration example for SimpleChatDUT.

This shows how to configure and run a tournament with specific SimpleChatDUT variants.
SimpleChatDUT is a minimal DUT that sends the task specification directly to an AI model
with a basic system prompt.

Variants demonstrated:
- Claude 3.5 Sonnet
- GPT-4o
- GPT-4o-mini (cost-effective variant)
"""

from pathlib import Path

from codegen_bench.cache.store import SolutionCache
from codegen_bench.core.arena import Arena
from codegen_bench.core.task import Task
from codegen_bench.core.tournament import TournamentRunner
from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.judge.orchestrator import JudgeOrchestrator

# ============================================================================
# SimpleChatDUT Configuration
# ============================================================================

# Define specific SimpleChatDUT instances to compare
SIMPLE_CHAT_DUTS = [
    {
        "id": "simple_chat_claude_sonnet",
        "model": "claude-3-5-sonnet-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
        "provider": "anthropic",
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    {
        "id": "simple_chat_gpt4o",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "provider": "openai",
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    {
        "id": "simple_chat_gpt4o_mini",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "provider": "openai",
        "max_tokens": 4096,
        "temperature": 0.7,
    },
]

# Task selection - diverse set
TASK_IDS = [
    "task_006",  # zstd - C
    "task_007",  # ripgrep - Rust
    "task_015",  # containerd - Go
    "task_022",  # zstd - C
    "task_023",  # ripgrep - Rust
]

ARENA_NAMES = ["correctness", "maintainability"]
SAMPLES_PER_PAIRING = 3

# Paths
OUTPUT_DIR = Path("./results/simple_chat_comparison")
CACHE_DIR = Path(".cache/solutions")
CHECKPOINT_DIR = Path(".checkpoints/simple_chat")

# ============================================================================
# Setup Functions
# ============================================================================

def create_simple_chat_duts() -> list[SimpleChatDUT]:
    """Create SimpleChatDUT instances from configuration.

    Returns:
        List of configured SimpleChatDUT instances
    """
    duts = []
    for config in SIMPLE_CHAT_DUTS:
        dut = SimpleChatDUT(
            dut_id=config["id"],
            model=config["model"],
            api_key_env=config["api_key_env"],
            provider=config["provider"],
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        )
        duts.append(dut)
    return duts


def create_tournament() -> TournamentRunner:
    """Create tournament for SimpleChatDUT comparison.

    Returns:
        Configured TournamentRunner
    """
    # Create DUTs
    duts = create_simple_chat_duts()

    # Load tasks
    tasks_dir = Path("tasks/core")
    tasks = []
    for task_id in TASK_IDS:
        task_file = tasks_dir / f"{task_id}.yaml"
        task = Task.from_yaml_file(task_file)
        tasks.append(task)

    # Create arenas
    arenas = [Arena(name=name) for name in ARENA_NAMES]

    # Initialize judges
    judges = JudgeOrchestrator(num_judges=3, consensus_threshold=2)

    # Initialize cache
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
    """Run SimpleChatDUT comparison tournament."""
    print("="*80)
    print("SimpleChatDUT COMPARISON TOURNAMENT")
    print("="*80)
    print("\nDUTs being compared:")
    for i, config in enumerate(SIMPLE_CHAT_DUTS, 1):
        print(f"  {i}. {config['id']} ({config['model']})")

    print(f"\nTasks: {len(TASK_IDS)}")
    print(f"Arenas: {', '.join(ARENA_NAMES)}")
    print(f"Samples per pairing: {SAMPLES_PER_PAIRING}")
    print()

    tournament = create_tournament()

    result = tournament.run(
        progress_callback=lambda c: print(f"  Comparisons: {c}", flush=True),
        output_dir=OUTPUT_DIR,
        checkpoint_dir=CHECKPOINT_DIR,
    )

    # Print detailed results
    print("\n" + "="*80)
    print("RESULTS: SimpleChatDUT Variants")
    print("="*80)

    for i, rating in enumerate(result.get_leaderboard(), 1):
        config = next(c for c in SIMPLE_CHAT_DUTS if c["id"] == rating.dut_id)

        print(f"\n{i}. {rating.dut_id}")
        print(f"   Model: {config['model']}")
        print(f"   ELO: {rating.elo:.1f} ± {rating.elo_std:.1f}")
        print(f"   Record: {rating.wins}W-{rating.losses}L-{rating.ties}T")
        print(f"   Cost: ${rating.total_cost_usd:.4f}")
        print(f"   Tokens: {rating.total_tokens:,}")
        print(f"   Avg time/task: {rating.total_time_seconds/len(TASK_IDS):.1f}s")

    # Cost-effectiveness analysis
    print("\n" + "-"*80)
    print("COST-EFFECTIVENESS ANALYSIS")
    print("-"*80)
    leaderboard = result.get_leaderboard()
    best_elo = leaderboard[0].elo
    for rating in leaderboard:
        elo_ratio = rating.elo / best_elo if best_elo > 0 else 0
        cost_per_point = rating.total_cost_usd / rating.elo if rating.elo > 0 else 0
        print(f"{rating.dut_id}:")
        print(f"  Performance: {elo_ratio*100:.1f}% of best")
        print(f"  Cost per ELO point: ${cost_per_point:.6f}")


if __name__ == "__main__":
    main()
