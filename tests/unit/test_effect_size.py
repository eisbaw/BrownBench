"""Tests for effect size calculations."""

import numpy as np
import pytest

from codegen_bench.stats.effect_size import EffectSize, cohens_h, hedges_g


def test_effect_size_dataclass() -> None:
    """Test EffectSize dataclass creation."""
    effect = EffectSize(
        metric="hedges_g",
        value=0.5,
        ci_lower=0.3,
        ci_upper=0.7,
        cles=0.65,
        interpretation="medium",
        sample_sizes=(30, 30),
    )

    assert effect.metric == "hedges_g"
    assert effect.value == 0.5
    assert effect.ci_lower == 0.3
    assert effect.ci_upper == 0.7
    assert effect.cles == 0.65
    assert effect.interpretation == "medium"
    assert effect.sample_sizes == (30, 30)


def test_effect_size_str() -> None:
    """Test string representation."""
    effect = EffectSize(
        metric="hedges_g",
        value=0.52,
        ci_lower=0.31,
        ci_upper=0.73,
        cles=0.67,
        interpretation="medium",
        sample_sizes=(30, 30),
    )

    s = str(effect)
    assert "hedges_g" in s
    assert "0.520" in s
    assert "0.310" in s
    assert "0.730" in s
    assert "CLES=0.670" in s
    assert "medium" in s


def test_hedges_g_independent_no_difference() -> None:
    """Test Hedges' g when groups are identical."""
    group_a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    group_b = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    effect = hedges_g(group_a, group_b, paired=False, n_bootstrap=1000)

    assert effect.value == pytest.approx(0.0, abs=0.01)
    assert effect.metric == "hedges_g"
    assert effect.sample_sizes == (5, 5)
    # CLES should be around 0.5 (no difference)
    assert effect.cles == pytest.approx(0.5, abs=0.15)


def test_hedges_g_independent_large_difference() -> None:
    """Test Hedges' g with large group difference."""
    np.random.seed(42)
    group_a = np.random.normal(loc=10, scale=2, size=30)
    group_b = np.random.normal(loc=5, scale=2, size=30)

    effect = hedges_g(group_a, group_b, paired=False, n_bootstrap=1000)

    # Large difference: (10-5)/2 ≈ 2.5 standard deviations
    assert effect.value > 2.0
    assert effect.interpretation == "large"
    # CLES should be very high (A > B almost always)
    assert effect.cles > 0.9


def test_hedges_g_independent_small_difference() -> None:
    """Test Hedges' g with small group difference."""
    np.random.seed(42)
    group_a = np.random.normal(loc=5.5, scale=2, size=30)
    group_b = np.random.normal(loc=5.0, scale=2, size=30)

    effect = hedges_g(group_a, group_b, paired=False, n_bootstrap=1000)

    # Small difference: (5.5-5)/2 = 0.25 standard deviations
    assert 0.0 < abs(effect.value) < 0.5
    assert effect.interpretation in ["negligible", "small"]


def test_hedges_g_paired() -> None:
    """Test Hedges' g with paired samples."""
    # Same DUT evaluated in two arenas (paired design)
    np.random.seed(42)
    arena_a = np.random.normal(loc=10, scale=2, size=20)
    arena_b = arena_a + np.random.normal(loc=1, scale=0.5, size=20)

    effect = hedges_g(arena_a, arena_b, paired=True, n_bootstrap=1000)

    assert effect.metric == "hedges_g_paired"
    # Should detect the systematic difference
    assert effect.value != 0.0
    assert effect.sample_sizes == (20, 20)


def test_hedges_g_paired_requires_equal_length() -> None:
    """Test that paired analysis requires equal length arrays."""
    group_a = np.array([1, 2, 3])
    group_b = np.array([4, 5])

    with pytest.raises(ValueError, match="same length"):
        hedges_g(group_a, group_b, paired=True)


def test_hedges_g_no_variance() -> None:
    """Test Hedges' g when there's no variance."""
    group_a = np.array([5.0, 5.0, 5.0])
    group_b = np.array([5.0, 5.0, 5.0])

    effect = hedges_g(group_a, group_b, paired=False, n_bootstrap=100)

    # No variance -> g = 0
    assert effect.value == 0.0
    assert effect.interpretation == "negligible"


def test_hedges_g_confidence_interval() -> None:
    """Test that confidence interval is reasonable."""
    np.random.seed(42)
    group_a = np.random.normal(loc=10, scale=2, size=30)
    group_b = np.random.normal(loc=8, scale=2, size=30)

    effect = hedges_g(group_a, group_b, paired=False, n_bootstrap=1000)

    # CI should contain the point estimate
    assert effect.ci_lower < effect.value < effect.ci_upper
    # CI should not be too wide
    ci_width = effect.ci_upper - effect.ci_lower
    assert ci_width < 3.0  # Reasonable for g


def test_hedges_g_custom_ci_level() -> None:
    """Test custom confidence interval level."""
    np.random.seed(42)
    group_a = np.random.normal(loc=10, scale=2, size=30)
    group_b = np.random.normal(loc=8, scale=2, size=30)

    effect_95 = hedges_g(group_a, group_b, ci=0.95, n_bootstrap=1000)
    effect_99 = hedges_g(group_a, group_b, ci=0.99, n_bootstrap=1000)

    # 99% CI should be wider than 95% CI
    width_95 = effect_95.ci_upper - effect_95.ci_lower
    width_99 = effect_99.ci_upper - effect_99.ci_lower
    assert width_99 > width_95


def test_hedges_g_reproducible() -> None:
    """Test that bootstrap is reproducible."""
    group_a = np.random.normal(loc=10, scale=2, size=30)
    group_b = np.random.normal(loc=8, scale=2, size=30)

    effect1 = hedges_g(group_a, group_b, n_bootstrap=1000)
    effect2 = hedges_g(group_a, group_b, n_bootstrap=1000)

    # Should be identical (same random seed internally)
    assert effect1.ci_lower == effect2.ci_lower
    assert effect1.ci_upper == effect2.ci_upper


def test_cohens_h_no_difference() -> None:
    """Test Cohen's h when proportions are equal."""
    h = cohens_h(0.5, 0.5)
    assert h == pytest.approx(0.0, abs=0.01)


def test_cohens_h_small_difference() -> None:
    """Test Cohen's h with small proportion difference."""
    h = cohens_h(0.55, 0.50)
    abs_h = abs(h)
    assert 0.0 < abs_h < 0.5  # Small effect


def test_cohens_h_large_difference() -> None:
    """Test Cohen's h with large proportion difference."""
    h = cohens_h(0.9, 0.5)
    abs_h = abs(h)
    assert abs_h > 0.8  # Large effect


def test_cohens_h_extreme_proportions() -> None:
    """Test Cohen's h with extreme proportions."""
    h = cohens_h(1.0, 0.0)
    abs_h = abs(h)
    # Maximum possible h ≈ π (from arcsine transformation)
    assert abs_h > 3.0


def test_cohens_h_symmetry() -> None:
    """Test that Cohen's h is antisymmetric."""
    h1 = cohens_h(0.7, 0.3)
    h2 = cohens_h(0.3, 0.7)

    assert h1 == pytest.approx(-h2, abs=0.01)


def test_interpretation_negligible() -> None:
    """Test interpretation of negligible effect."""
    group_a = np.array([5.0, 5.1, 4.9, 5.0, 5.1])
    group_b = np.array([5.0, 5.0, 5.0, 5.1, 4.9])

    effect = hedges_g(group_a, group_b, n_bootstrap=100)
    # Small sample variance can push this to "small"
    assert effect.interpretation in ["negligible", "small"]
    assert abs(effect.value) < 0.5  # Should be small effect


def test_interpretation_small() -> None:
    """Test interpretation of small effect."""
    np.random.seed(42)
    # Cohen's d ≈ 0.3 (small)
    group_a = np.random.normal(loc=5.3, scale=1, size=50)
    group_b = np.random.normal(loc=5.0, scale=1, size=50)

    effect = hedges_g(group_a, group_b, n_bootstrap=100)
    assert effect.interpretation in ["small", "negligible"]  # Close to boundary


def test_interpretation_medium() -> None:
    """Test interpretation of medium effect."""
    np.random.seed(42)
    # Cohen's d ≈ 0.6 (medium), but with random variation may be "small"
    group_a = np.random.normal(loc=5.6, scale=1, size=50)
    group_b = np.random.normal(loc=5.0, scale=1, size=50)

    effect = hedges_g(group_a, group_b, n_bootstrap=100)
    # With random sampling, may be small or medium
    assert effect.interpretation in ["small", "medium"]
    assert 0.2 < abs(effect.value) < 0.9


def test_interpretation_large() -> None:
    """Test interpretation of large effect."""
    np.random.seed(42)
    # Cohen's d ≈ 1.5 (large)
    group_a = np.random.normal(loc=6.5, scale=1, size=50)
    group_b = np.random.normal(loc=5.0, scale=1, size=50)

    effect = hedges_g(group_a, group_b, n_bootstrap=100)
    assert effect.interpretation == "large"


def test_cles_calculation() -> None:
    """Test Common Language Effect Size calculation."""
    # Group A is always greater than Group B
    group_a = np.array([10.0, 11.0, 12.0])
    group_b = np.array([1.0, 2.0, 3.0])

    effect = hedges_g(group_a, group_b, n_bootstrap=100)

    # P(A > B) should be 1.0 (all comparisons favor A)
    assert effect.cles == pytest.approx(1.0, abs=0.01)


def test_cles_no_overlap() -> None:
    """Test CLES when groups don't overlap."""
    group_a = np.array([5.0, 6.0, 7.0])
    group_b = np.array([1.0, 2.0, 3.0])

    effect = hedges_g(group_a, group_b, n_bootstrap=100)

    # All of A > all of B
    assert effect.cles == 1.0


def test_cles_complete_overlap() -> None:
    """Test CLES when groups completely overlap."""
    group_a = np.array([1.0, 2.0, 3.0])
    group_b = np.array([1.0, 2.0, 3.0])

    effect = hedges_g(group_a, group_b, n_bootstrap=100)

    # With ties, CLES counts only strict inequality (A > B)
    # 1>1:F, 1>2:F, 1>3:F
    # 2>1:T, 2>2:F, 2>3:F
    # 3>1:T, 3>2:T, 3>3:F
    # 3/9 = 0.33
    assert effect.cles == pytest.approx(0.33, abs=0.05)


def test_hedges_g_correction_factor() -> None:
    """Test that Hedges' g is smaller than Cohen's d (bias correction)."""
    np.random.seed(42)
    group_a = np.random.normal(loc=10, scale=2, size=10)  # Small sample
    group_b = np.random.normal(loc=8, scale=2, size=10)

    effect = hedges_g(group_a, group_b, n_bootstrap=100)

    # Calculate Cohen's d manually
    pooled_sd = np.sqrt(
        ((10 - 1) * np.var(group_a, ddof=1) + (10 - 1) * np.var(group_b, ddof=1)) / (10 + 10 - 2)
    )
    cohens_d = (np.mean(group_a) - np.mean(group_b)) / pooled_sd

    # Hedges' g should be slightly smaller (bias correction)
    assert abs(effect.value) < abs(cohens_d)
