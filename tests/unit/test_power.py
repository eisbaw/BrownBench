"""Tests for statistical power analysis."""

import pytest

from codegen_bench.stats.power import (
    PowerAnalysisResult,
    calculate_minimum_detectable_effect,
    calculate_power_proportion,
    calculate_power_ttest,
    calculate_sample_size_proportion,
    calculate_sample_size_ttest,
    interpret_power,
)


def test_power_analysis_result_str() -> None:
    """Test PowerAnalysisResult string representation."""
    result = PowerAnalysisResult(
        power=0.80,
        sample_size=64,
        effect_size=0.5,
        alpha=0.05,
        test_type="t-test",
        notes="Test note",
    )

    output = str(result)
    assert "Power: 0.800" in output
    assert "Sample size" in output
    assert "64" in output
    assert "0.500" in output


def test_calculate_sample_size_ttest_medium_effect() -> None:
    """Test sample size calculation for medium effect (d=0.5)."""
    result = calculate_sample_size_ttest(effect_size=0.5, alpha=0.05, power=0.80)

    # Cohen (1988): n ≈ 64 per group for d=0.5, power=0.80
    assert result.sample_size is not None
    assert 60 <= result.sample_size <= 70
    assert result.power == 0.80
    assert result.effect_size == 0.5
    assert result.alpha == 0.05


def test_calculate_sample_size_ttest_small_effect() -> None:
    """Test sample size calculation for small effect (d=0.2)."""
    result = calculate_sample_size_ttest(effect_size=0.2, alpha=0.05, power=0.80)

    # Small effects require much larger samples
    assert result.sample_size is not None
    assert result.sample_size > 300


def test_calculate_sample_size_ttest_large_effect() -> None:
    """Test sample size calculation for large effect (d=0.8)."""
    result = calculate_sample_size_ttest(effect_size=0.8, alpha=0.05, power=0.80)

    # Large effects require smaller samples
    assert result.sample_size is not None
    assert result.sample_size < 50


def test_calculate_sample_size_ttest_high_power() -> None:
    """Test sample size increases with higher power requirement."""
    result_80 = calculate_sample_size_ttest(effect_size=0.5, power=0.80)
    result_90 = calculate_sample_size_ttest(effect_size=0.5, power=0.90)
    result_95 = calculate_sample_size_ttest(effect_size=0.5, power=0.95)

    # Higher power requires more samples
    assert result_80.sample_size is not None
    assert result_90.sample_size is not None
    assert result_95.sample_size is not None
    assert result_80.sample_size < result_90.sample_size < result_95.sample_size


def test_calculate_sample_size_ttest_stricter_alpha() -> None:
    """Test sample size increases with stricter alpha."""
    result_05 = calculate_sample_size_ttest(effect_size=0.5, alpha=0.05)
    result_01 = calculate_sample_size_ttest(effect_size=0.5, alpha=0.01)

    # Stricter alpha requires more samples
    assert result_05.sample_size is not None
    assert result_01.sample_size is not None
    assert result_01.sample_size > result_05.sample_size


def test_calculate_sample_size_ttest_one_sided() -> None:
    """Test one-sided test requires fewer samples."""
    result_two = calculate_sample_size_ttest(
        effect_size=0.5, alternative="two-sided"
    )
    result_one = calculate_sample_size_ttest(effect_size=0.5, alternative="larger")

    # One-sided test is more powerful
    assert result_two.sample_size is not None
    assert result_one.sample_size is not None
    assert result_one.sample_size < result_two.sample_size


def test_calculate_sample_size_ttest_unequal_groups() -> None:
    """Test sample size calculation with unequal group sizes."""
    result = calculate_sample_size_ttest(effect_size=0.5, ratio=2.0)

    # With ratio=2, group 2 has 2x samples of group 1
    assert result.sample_size is not None
    assert "ratio=2.0" in result.notes


def test_calculate_power_ttest_basic() -> None:
    """Test power calculation for t-test."""
    # With n=64, d=0.5, should achieve ~80% power
    result = calculate_power_ttest(sample_size=64, effect_size=0.5)

    assert 0.75 <= result.power <= 0.85
    assert result.sample_size == 64
    assert result.effect_size == 0.5


def test_calculate_power_ttest_small_sample() -> None:
    """Test power is low with small samples."""
    result = calculate_power_ttest(sample_size=10, effect_size=0.5)

    # Small sample -> low power
    assert result.power < 0.50


def test_calculate_power_ttest_large_sample() -> None:
    """Test power is high with large samples."""
    result = calculate_power_ttest(sample_size=200, effect_size=0.5)

    # Large sample -> high power
    assert result.power > 0.95


def test_calculate_minimum_detectable_effect_basic() -> None:
    """Test minimum detectable effect calculation."""
    result = calculate_minimum_detectable_effect(sample_size=30, power=0.80)

    # With small sample, can only detect large effects
    assert result.effect_size is not None
    assert result.effect_size > 0.6  # Larger than medium effect


def test_calculate_minimum_detectable_effect_large_sample() -> None:
    """Test MDE decreases with larger samples."""
    result_small = calculate_minimum_detectable_effect(sample_size=30)
    result_large = calculate_minimum_detectable_effect(sample_size=200)

    # Larger sample can detect smaller effects
    assert result_small.effect_size is not None
    assert result_large.effect_size is not None
    assert result_large.effect_size < result_small.effect_size


def test_calculate_sample_size_proportion_basic() -> None:
    """Test sample size for proportion comparison."""
    # Detect win rate increase from 50% to 60%
    result = calculate_sample_size_proportion(p1=0.5, p2=0.6, power=0.80)

    assert result.sample_size is not None
    assert result.sample_size > 300  # Proportions need large samples
    assert "p1=0.500" in result.notes
    assert "p2=0.600" in result.notes


def test_calculate_sample_size_proportion_small_difference() -> None:
    """Test sample size for small proportion difference."""
    # Detect 50% vs 55% - very subtle difference
    result = calculate_sample_size_proportion(p1=0.5, p2=0.55, power=0.80)

    assert result.sample_size is not None
    assert result.sample_size > 1000  # Need many samples for small differences


def test_calculate_sample_size_proportion_large_difference() -> None:
    """Test sample size for large proportion difference."""
    # Detect 50% vs 80% - obvious difference
    result = calculate_sample_size_proportion(p1=0.5, p2=0.8, power=0.80)

    assert result.sample_size is not None
    assert result.sample_size < 100  # Large differences need fewer samples


def test_calculate_power_proportion_basic() -> None:
    """Test power calculation for proportions."""
    # Check power with n=400 to detect 50% vs 60%
    result = calculate_power_proportion(sample_size=400, p1=0.5, p2=0.6)

    assert 0.75 <= result.power <= 0.90


def test_calculate_power_proportion_insufficient_sample() -> None:
    """Test power is low with insufficient samples."""
    # Only n=50 to detect 50% vs 60%
    result = calculate_power_proportion(sample_size=50, p1=0.5, p2=0.6)

    assert result.power < 0.50  # Insufficient power


def test_calculate_power_proportion_ample_sample() -> None:
    """Test power is high with ample samples."""
    # Large n=1000 to detect 50% vs 60%
    result = calculate_power_proportion(sample_size=1000, p1=0.5, p2=0.6)

    assert result.power > 0.95  # Very high power


def test_interpret_power_very_low() -> None:
    """Test interpretation of very low power."""
    interpretation = interpret_power(0.3)
    assert "very low" in interpretation


def test_interpret_power_low() -> None:
    """Test interpretation of low power."""
    interpretation = interpret_power(0.6)
    assert "low" in interpretation


def test_interpret_power_moderate() -> None:
    """Test interpretation of moderate power."""
    interpretation = interpret_power(0.75)
    assert "moderate" in interpretation


def test_interpret_power_good() -> None:
    """Test interpretation of good power."""
    interpretation = interpret_power(0.85)
    assert "good" in interpretation
    assert "conventional" in interpretation


def test_interpret_power_high() -> None:
    """Test interpretation of high power."""
    interpretation = interpret_power(0.92)
    assert "high" in interpretation


def test_interpret_power_very_high() -> None:
    """Test interpretation of very high power."""
    interpretation = interpret_power(0.97)
    assert "very high" in interpretation


def test_sample_size_and_power_are_inverses() -> None:
    """Test that sample size and power calculations are consistent."""
    # Calculate required sample size
    result_n = calculate_sample_size_ttest(effect_size=0.5, power=0.80)

    # Use that sample size to calculate power
    assert result_n.sample_size is not None
    result_p = calculate_power_ttest(
        sample_size=result_n.sample_size, effect_size=0.5
    )

    # Should recover original power (within tolerance)
    assert abs(result_p.power - 0.80) < 0.02


def test_minimum_detectable_effect_consistency() -> None:
    """Test MDE calculation is consistent with power calculation."""
    # Calculate MDE for n=50
    result_mde = calculate_minimum_detectable_effect(sample_size=50, power=0.80)

    # Use that effect size to calculate power with n=50
    assert result_mde.effect_size is not None
    result_p = calculate_power_ttest(
        sample_size=50, effect_size=result_mde.effect_size
    )

    # Should recover original power
    assert abs(result_p.power - 0.80) < 0.02


def test_proportion_calculations_consistency() -> None:
    """Test proportion sample size and power are consistent."""
    # Calculate required sample size
    result_n = calculate_sample_size_proportion(p1=0.5, p2=0.6, power=0.80)

    # Use that sample size to calculate power
    assert result_n.sample_size is not None
    result_p = calculate_power_proportion(
        sample_size=result_n.sample_size, p1=0.5, p2=0.6
    )

    # Should recover original power (within tolerance)
    assert abs(result_p.power - 0.80) < 0.03


def test_negative_effect_size_handled() -> None:
    """Test that negative effect sizes are handled correctly."""
    result_pos = calculate_sample_size_ttest(effect_size=0.5)
    result_neg = calculate_sample_size_ttest(effect_size=-0.5)

    # Absolute value should be used - same sample size
    assert result_pos.sample_size == result_neg.sample_size


def test_power_result_types() -> None:
    """Test that PowerAnalysisResult fields have correct types."""
    result = calculate_sample_size_ttest(effect_size=0.5)

    assert isinstance(result.power, float)
    assert isinstance(result.sample_size, int) or result.sample_size is None
    assert isinstance(result.effect_size, float) or result.effect_size is None
    assert isinstance(result.alpha, float)
    assert isinstance(result.test_type, str)
    assert isinstance(result.notes, str)
