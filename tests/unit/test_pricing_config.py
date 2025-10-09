"""Unit tests for PricingConfig."""

import pytest

from codegen_bench.core.config import PricingConfig


def test_pricing_config_defaults():
    """Test PricingConfig default values."""
    config = PricingConfig()

    assert config.claude_sonnet_4_5_input_per_1k == 0.003
    assert config.claude_sonnet_4_5_output_per_1k == 0.015


def test_pricing_config_custom_values():
    """Test PricingConfig with custom values."""
    config = PricingConfig(
        claude_sonnet_4_5_input_per_1k=0.005, claude_sonnet_4_5_output_per_1k=0.020
    )

    assert config.claude_sonnet_4_5_input_per_1k == 0.005
    assert config.claude_sonnet_4_5_output_per_1k == 0.020


def test_pricing_config_immutable():
    """Test that PricingConfig is immutable."""
    config = PricingConfig()

    with pytest.raises(AttributeError):
        config.claude_sonnet_4_5_input_per_1k = 0.010


def test_pricing_config_negative_input_cost():
    """Test that negative input cost raises ValueError."""
    with pytest.raises(ValueError, match="claude_sonnet_4_5_input_per_1k must be non-negative"):
        PricingConfig(claude_sonnet_4_5_input_per_1k=-0.001)


def test_pricing_config_negative_output_cost():
    """Test that negative output cost raises ValueError."""
    with pytest.raises(ValueError, match="claude_sonnet_4_5_output_per_1k must be non-negative"):
        PricingConfig(claude_sonnet_4_5_output_per_1k=-0.001)


def test_pricing_config_zero_cost_allowed():
    """Test that zero cost is allowed (e.g., for testing)."""
    config = PricingConfig(claude_sonnet_4_5_input_per_1k=0.0, claude_sonnet_4_5_output_per_1k=0.0)

    assert config.claude_sonnet_4_5_input_per_1k == 0.0
    assert config.claude_sonnet_4_5_output_per_1k == 0.0


def test_pricing_config_cost_calculation():
    """Test cost calculation using PricingConfig."""
    config = PricingConfig()

    # Example: 1500 input tokens, 500 output tokens
    input_tokens = 1500
    output_tokens = 500

    input_cost = (input_tokens / 1000) * config.claude_sonnet_4_5_input_per_1k
    output_cost = (output_tokens / 1000) * config.claude_sonnet_4_5_output_per_1k
    total_cost = input_cost + output_cost

    # 1.5 * 0.003 + 0.5 * 0.015 = 0.0045 + 0.0075 = 0.012
    assert total_cost == pytest.approx(0.012, rel=1e-9)


def test_pricing_config_large_token_count():
    """Test cost calculation with large token counts."""
    config = PricingConfig()

    # 1M input tokens, 100K output tokens
    input_tokens = 1_000_000
    output_tokens = 100_000

    input_cost = (input_tokens / 1000) * config.claude_sonnet_4_5_input_per_1k
    output_cost = (output_tokens / 1000) * config.claude_sonnet_4_5_output_per_1k
    total_cost = input_cost + output_cost

    # 1000 * 0.003 + 100 * 0.015 = 3.0 + 1.5 = 4.5
    assert total_cost == pytest.approx(4.5, rel=1e-9)
