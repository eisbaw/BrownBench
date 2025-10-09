"""Example: Configuring tournaments with TournamentConfig and TrueSkillConfig.

This example demonstrates how to use the configuration dataclasses
for setting up reproducible, configurable tournaments.
"""

from pathlib import Path
from codegen_bench.core.config import TournamentConfig, TrueSkillConfig
from codegen_bench.stats.ratings.trueskill_rating import TrueSkillRating


def example_basic_tournament_config():
    """Demonstrate basic tournament configuration."""
    print("Basic Tournament Configuration")
    print("-" * 40)

    # Default configuration
    default_config = TournamentConfig()
    print("Default configuration:")
    print(f"  base_seed: {default_config.base_seed}")
    print(f"  samples_per_pairing: {default_config.samples_per_pairing}")
    print(f"  checkpoint_interval: {default_config.checkpoint_interval}")

    # Custom configuration for quick evaluation
    quick_config = TournamentConfig(
        base_seed=123,           # Different seed for variety
        samples_per_pairing=2,    # Fewer samples for speed
        checkpoint_interval=5     # More frequent checkpoints
    )
    print("\nQuick evaluation config:")
    print(f"  base_seed: {quick_config.base_seed}")
    print(f"  samples_per_pairing: {quick_config.samples_per_pairing}")
    print(f"  checkpoint_interval: {quick_config.checkpoint_interval}")

    # Research configuration for statistical rigor
    research_config = TournamentConfig(
        base_seed=42,             # Fixed seed for reproducibility
        samples_per_pairing=10,   # Many samples for power
        checkpoint_interval=20    # Less frequent checkpoints
    )
    print("\nResearch config:")
    print(f"  base_seed: {research_config.base_seed}")
    print(f"  samples_per_pairing: {research_config.samples_per_pairing}")
    print(f"  checkpoint_interval: {research_config.checkpoint_interval}")

    print()


def example_trueskill_configuration():
    """Demonstrate TrueSkill rating configuration."""
    print("TrueSkill Rating Configuration")
    print("-" * 40)

    # Default TrueSkill configuration
    default_ts = TrueSkillConfig()
    print("Default TrueSkill config:")
    print(f"  initial_mu: {default_ts.initial_mu}")
    print(f"  initial_sigma: {default_ts.initial_sigma}")
    print(f"  beta: {default_ts.beta}")
    print(f"  tau: {default_ts.tau}")
    print(f"  draw_probability: {default_ts.draw_probability}")

    # Configuration for environment with no draws
    no_draws_config = TrueSkillConfig(
        initial_mu=25.0,
        initial_sigma=8.33,
        draw_probability=0.0  # No draws expected
    )
    print("\nNo-draws environment:")
    print(f"  draw_probability: {no_draws_config.draw_probability}")

    # Configuration for volatile environment (skills change quickly)
    volatile_config = TrueSkillConfig(
        initial_mu=25.0,
        initial_sigma=10.0,   # Higher initial uncertainty
        tau=0.5              # Higher dynamics factor
    )
    print("\nVolatile environment:")
    print(f"  initial_sigma: {volatile_config.initial_sigma}")
    print(f"  tau: {volatile_config.tau}")

    # Configuration for stable environment (skills change slowly)
    stable_config = TrueSkillConfig(
        initial_mu=30.0,      # Different baseline
        initial_sigma=5.0,    # Lower initial uncertainty
        tau=0.0              # No skill drift
    )
    print("\nStable environment:")
    print(f"  initial_mu: {stable_config.initial_mu}")
    print(f"  initial_sigma: {stable_config.initial_sigma}")
    print(f"  tau: {stable_config.tau}")

    print()


def example_trueskill_in_action():
    """Demonstrate using TrueSkill configuration with ratings."""
    print("TrueSkill in Action")
    print("-" * 40)

    # Configure TrueSkill for our environment
    config = TrueSkillConfig(
        initial_mu=30.0,
        initial_sigma=10.0,
        draw_probability=0.15  # 15% draws expected
    )

    # Set as default for all new ratings
    TrueSkillRating.set_default_config(config)
    print(f"Set default config with mu={config.initial_mu}, sigma={config.initial_sigma}")

    # Create players
    player_a = TrueSkillRating()
    player_b = TrueSkillRating()

    print(f"\nInitial ratings:")
    print(f"  Player A: μ={player_a.mu:.2f}, σ={player_a.sigma:.2f}")
    print(f"  Player B: μ={player_b.mu:.2f}, σ={player_b.sigma:.2f}")

    # Simulate matches
    print("\nSimulating matches...")

    # A beats B
    player_a.update(player_b, "win")
    print(f"After A beats B:")
    print(f"  Player A: μ={player_a.mu:.2f}, σ={player_a.sigma:.2f}")
    print(f"  Player B: μ={player_b.mu:.2f}, σ={player_b.sigma:.2f}")

    # B beats A (upset)
    player_b.update(player_a, "win")
    print(f"After B beats A:")
    print(f"  Player A: μ={player_a.mu:.2f}, σ={player_a.sigma:.2f}")
    print(f"  Player B: μ={player_b.mu:.2f}, σ={player_b.sigma:.2f}")

    # Draw
    player_a.update(player_b, "draw")
    print(f"After draw:")
    print(f"  Player A: μ={player_a.mu:.2f}, σ={player_a.sigma:.2f}")
    print(f"  Player B: μ={player_b.mu:.2f}, σ={player_b.sigma:.2f}")

    print()


def example_seed_derivation():
    """Demonstrate how seeds are derived from base_seed."""
    print("Seed Derivation from base_seed")
    print("-" * 40)

    config = TournamentConfig(
        base_seed=42,
        samples_per_pairing=5
    )

    print(f"Base seed: {config.base_seed}")
    print(f"Samples per pairing: {config.samples_per_pairing}")
    print()

    # Show how seeds would be derived for each sample
    print("Derived seeds for (DUT, task) pairings:")
    for dut_idx in range(2):  # 2 DUTs
        for task_idx in range(3):  # 3 tasks
            print(f"\nDUT {dut_idx}, Task {task_idx}:")
            for sample in range(config.samples_per_pairing):
                # This is a simplified version of actual seed derivation
                derived_seed = config.base_seed + (dut_idx * 1000) + (task_idx * 100) + sample
                print(f"  Sample {sample}: seed = {derived_seed}")

    print("\nNote: Actual seed derivation may use hashing for better distribution")
    print()


def example_checkpoint_strategy():
    """Demonstrate checkpoint interval strategies."""
    print("Checkpoint Interval Strategies")
    print("-" * 40)

    scenarios = [
        ("Quick test", 5, 10, 1),      # 5 DUTs, 10 tasks, 1 sample
        ("Standard", 10, 50, 3),       # 10 DUTs, 50 tasks, 3 samples
        ("Large scale", 20, 100, 5),   # 20 DUTs, 100 tasks, 5 samples
    ]

    for name, num_duts, num_tasks, samples in scenarios:
        total_comparisons = num_duts * num_tasks * samples

        # Recommended checkpoint interval (5% of total)
        recommended_interval = max(1, total_comparisons // 20)

        config = TournamentConfig(
            samples_per_pairing=samples,
            checkpoint_interval=recommended_interval
        )

        print(f"\n{name}:")
        print(f"  DUTs: {num_duts}, Tasks: {num_tasks}, Samples: {samples}")
        print(f"  Total comparisons: {total_comparisons}")
        print(f"  Recommended checkpoint interval: {recommended_interval}")
        print(f"  Expected checkpoints: {total_comparisons // recommended_interval}")

    print()


def example_configuration_validation():
    """Demonstrate configuration validation."""
    print("Configuration Validation")
    print("-" * 40)

    # Valid configurations
    try:
        valid_config = TournamentConfig(
            base_seed=0,             # Zero is valid
            samples_per_pairing=1,   # Minimum valid value
            checkpoint_interval=1    # Minimum valid value
        )
        print("✓ Valid config with minimum values created")
    except ValueError as e:
        print(f"❌ Error: {e}")

    # Invalid configurations
    print("\nTesting invalid configurations:")

    # Negative seed
    try:
        invalid = TournamentConfig(base_seed=-1)
    except ValueError as e:
        print(f"✓ Caught negative seed: {e}")

    # Zero samples
    try:
        invalid = TournamentConfig(samples_per_pairing=0)
    except ValueError as e:
        print(f"✓ Caught zero samples: {e}")

    # Zero checkpoint interval
    try:
        invalid = TournamentConfig(checkpoint_interval=0)
    except ValueError as e:
        print(f"✓ Caught zero checkpoint interval: {e}")

    # TrueSkillConfig validation
    print("\nTrueSkill validation:")
    try:
        invalid = TrueSkillConfig(initial_sigma=-1)
    except ValueError as e:
        print(f"✓ Caught negative sigma: {e}")

    try:
        invalid = TrueSkillConfig(draw_probability=1.5)
    except ValueError as e:
        print(f"✓ Caught invalid draw probability: {e}")

    print()


def example_complete_setup():
    """Demonstrate complete tournament setup with all configs."""
    print("Complete Tournament Setup")
    print("-" * 40)

    from codegen_bench.core.config import PricingConfig

    # Set up all configurations
    tournament_config = TournamentConfig(
        base_seed=2025,
        samples_per_pairing=3,
        checkpoint_interval=10
    )

    trueskill_config = TrueSkillConfig(
        initial_mu=25.0,
        initial_sigma=8.33,
        draw_probability=0.1
    )

    pricing_config = PricingConfig(
        claude_sonnet_4_5_input_per_1k=0.003,
        claude_sonnet_4_5_output_per_1k=0.015
    )

    print("Tournament configuration:")
    print(f"  Base seed: {tournament_config.base_seed}")
    print(f"  Samples: {tournament_config.samples_per_pairing}")
    print(f"  Checkpoints: every {tournament_config.checkpoint_interval} comparisons")

    print("\nRating system:")
    print(f"  Initial skill: μ={trueskill_config.initial_mu}, σ={trueskill_config.initial_sigma}")
    print(f"  Draw probability: {trueskill_config.draw_probability*100:.0f}%")

    print("\nPricing:")
    print(f"  Input: ${pricing_config.claude_sonnet_4_5_input_per_1k}/1K tokens")
    print(f"  Output: ${pricing_config.claude_sonnet_4_5_output_per_1k}/1K tokens")

    # Estimate cost
    estimated_generations = 10 * 20 * tournament_config.samples_per_pairing  # 10 DUTs, 20 tasks
    estimated_tokens = estimated_generations * 2000  # ~2K tokens per generation
    estimated_cost = (estimated_tokens / 1000) * pricing_config.claude_sonnet_4_5_input_per_1k

    print(f"\nEstimated cost: ${estimated_cost:.2f} for {estimated_generations} generations")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Tournament Configuration Examples")
    print("=" * 60)
    print()

    example_basic_tournament_config()
    example_trueskill_configuration()
    example_trueskill_in_action()
    example_seed_derivation()
    example_checkpoint_strategy()
    example_configuration_validation()
    example_complete_setup()

    print("=" * 60)
    print("Summary: Use configuration dataclasses for reproducible tournaments")
    print("=" * 60)