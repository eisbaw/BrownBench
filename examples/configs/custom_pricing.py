"""Example: Configuring custom API pricing.

This example shows how to use PricingConfig to adjust API pricing
calculations, useful when API pricing changes or when tracking costs
for different models.
"""

from codegen_bench.core.config import PricingConfig
from codegen_bench.dut.simple_chat import SimpleChatDUT


def example_custom_pricing():
    """Demonstrate custom pricing configuration."""

    # Default pricing (as of January 2025)
    default_pricing = PricingConfig()
    print(f"Default Claude Sonnet 4.5 pricing:")
    print(f"  Input:  ${default_pricing.claude_sonnet_4_5_input_per_1k:.3f} per 1K tokens")
    print(f"  Output: ${default_pricing.claude_sonnet_4_5_output_per_1k:.3f} per 1K tokens")

    # Custom pricing (e.g., if pricing changes or for special agreements)
    custom_pricing = PricingConfig(
        claude_sonnet_4_5_input_per_1k=0.002,   # $2.00 per million tokens
        claude_sonnet_4_5_output_per_1k=0.010,  # $10.00 per million tokens
    )
    print(f"\nCustom pricing:")
    print(f"  Input:  ${custom_pricing.claude_sonnet_4_5_input_per_1k:.3f} per 1K tokens")
    print(f"  Output: ${custom_pricing.claude_sonnet_4_5_output_per_1k:.3f} per 1K tokens")

    # Calculate costs for a typical request
    input_tokens = 2000
    output_tokens = 800

    # With default pricing
    default_input_cost = (input_tokens / 1000) * default_pricing.claude_sonnet_4_5_input_per_1k
    default_output_cost = (output_tokens / 1000) * default_pricing.claude_sonnet_4_5_output_per_1k
    default_total = default_input_cost + default_output_cost

    # With custom pricing
    custom_input_cost = (input_tokens / 1000) * custom_pricing.claude_sonnet_4_5_input_per_1k
    custom_output_cost = (output_tokens / 1000) * custom_pricing.claude_sonnet_4_5_output_per_1k
    custom_total = custom_input_cost + custom_output_cost

    print(f"\nCost for {input_tokens} input + {output_tokens} output tokens:")
    print(f"  Default pricing: ${default_total:.4f}")
    print(f"  Custom pricing:  ${custom_total:.4f}")
    print(f"  Savings: ${default_total - custom_total:.4f} ({((default_total - custom_total) / default_total * 100):.1f}%)")


def example_zero_cost_testing():
    """Demonstrate zero-cost configuration for testing."""

    # Zero-cost configuration for testing (no actual API costs)
    test_pricing = PricingConfig(
        claude_sonnet_4_5_input_per_1k=0.0,
        claude_sonnet_4_5_output_per_1k=0.0,
    )

    print("\nTest configuration (zero cost):")
    print("  This is useful for unit tests where you want to track token")
    print("  usage but not calculate actual costs.")

    # Example: Calculate "cost" for testing
    test_tokens = 10000
    test_cost = (test_tokens / 1000) * test_pricing.claude_sonnet_4_5_input_per_1k
    print(f"  Cost for {test_tokens} tokens: ${test_cost:.2f}")


def example_cost_estimation():
    """Demonstrate cost estimation for a tournament."""

    pricing = PricingConfig()

    # Tournament parameters
    num_duts = 3
    num_tasks = 20
    samples_per_pairing = 5
    avg_input_tokens = 1500
    avg_output_tokens = 600

    # Calculate total tokens
    total_generations = num_duts * num_tasks * samples_per_pairing
    total_input_tokens = total_generations * avg_input_tokens
    total_output_tokens = total_generations * avg_output_tokens

    # Calculate costs
    input_cost = (total_input_tokens / 1000) * pricing.claude_sonnet_4_5_input_per_1k
    output_cost = (total_output_tokens / 1000) * pricing.claude_sonnet_4_5_output_per_1k
    total_cost = input_cost + output_cost

    print("\nTournament Cost Estimation:")
    print(f"  DUTs: {num_duts}")
    print(f"  Tasks: {num_tasks}")
    print(f"  Samples per pairing: {samples_per_pairing}")
    print(f"  Total generations: {total_generations}")
    print(f"\nToken usage:")
    print(f"  Input tokens:  {total_input_tokens:,}")
    print(f"  Output tokens: {total_output_tokens:,}")
    print(f"\nEstimated costs:")
    print(f"  Input cost:  ${input_cost:.2f}")
    print(f"  Output cost: ${output_cost:.2f}")
    print(f"  Total cost:  ${total_cost:.2f}")

    # Cost per comparison
    cost_per_generation = total_cost / total_generations
    print(f"\nCost per generation: ${cost_per_generation:.3f}")


def example_pricing_comparison():
    """Compare pricing across different model configurations."""

    # Different pricing tiers (hypothetical)
    configs = {
        "Standard": PricingConfig(
            claude_sonnet_4_5_input_per_1k=0.003,
            claude_sonnet_4_5_output_per_1k=0.015
        ),
        "Volume": PricingConfig(
            claude_sonnet_4_5_input_per_1k=0.0025,  # Volume discount
            claude_sonnet_4_5_output_per_1k=0.012
        ),
        "Enterprise": PricingConfig(
            claude_sonnet_4_5_input_per_1k=0.002,   # Enterprise pricing
            claude_sonnet_4_5_output_per_1k=0.010
        ),
    }

    # Typical monthly usage
    monthly_input_tokens = 10_000_000   # 10M tokens
    monthly_output_tokens = 3_000_000   # 3M tokens

    print("\nPricing Tier Comparison (Monthly):")
    print("-" * 50)

    for tier_name, config in configs.items():
        input_cost = (monthly_input_tokens / 1000) * config.claude_sonnet_4_5_input_per_1k
        output_cost = (monthly_output_tokens / 1000) * config.claude_sonnet_4_5_output_per_1k
        total = input_cost + output_cost

        print(f"\n{tier_name}:")
        print(f"  Input cost:  ${input_cost:,.2f}")
        print(f"  Output cost: ${output_cost:,.2f}")
        print(f"  Total:       ${total:,.2f}")

        if tier_name != "Standard":
            standard_total = (
                (monthly_input_tokens / 1000) * configs["Standard"].claude_sonnet_4_5_input_per_1k +
                (monthly_output_tokens / 1000) * configs["Standard"].claude_sonnet_4_5_output_per_1k
            )
            savings = standard_total - total
            print(f"  Savings vs Standard: ${savings:,.2f} ({savings/standard_total*100:.1f}%)")


if __name__ == "__main__":
    print("=" * 60)
    print("PricingConfig Examples")
    print("=" * 60)

    example_custom_pricing()
    example_zero_cost_testing()
    example_cost_estimation()
    example_pricing_comparison()

    print("\n" + "=" * 60)
    print("Note: Actual API pricing may vary. Check provider documentation.")
    print("=" * 60)