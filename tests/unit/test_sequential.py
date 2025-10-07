"""Tests for group sequential design."""

import numpy as np
import pytest

from codegen_bench.stats.adaptive.sequential import (
    GroupSequentialDesign,
    SequentialBoundaries,
)


def test_sequential_boundaries_creation() -> None:
    """Test SequentialBoundaries dataclass."""
    boundaries = SequentialBoundaries(
        checkpoints=np.array([100, 200, 300]),
        alpha_spending=np.array([0.001, 0.01, 0.05]),
        z_boundaries=np.array([4.0, 2.5, 1.96]),
        information_fractions=np.array([0.33, 0.67, 1.0]),
    )

    assert len(boundaries.checkpoints) == 3
    assert boundaries.checkpoints[0] == 100
    assert boundaries.alpha_spending[-1] == pytest.approx(0.05, abs=0.001)


def test_sequential_boundaries_str() -> None:
    """Test string representation of boundaries."""
    boundaries = SequentialBoundaries(
        checkpoints=np.array([100, 200]),
        alpha_spending=np.array([0.001, 0.05]),
        z_boundaries=np.array([4.0, 2.0]),
        information_fractions=np.array([0.5, 1.0]),
    )

    output = str(boundaries)
    assert "O'Brien-Fleming" in output
    assert "Look 1" in output
    assert "100" in output  # Check for the number, not exact formatting


def test_group_sequential_design_initialization() -> None:
    """Test GroupSequentialDesign initialization."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    assert design.max_n == 300
    assert design.num_looks == 3
    assert design.alpha == 0.05
    assert design.futility_threshold == 0.20


def test_obrien_fleming_boundaries() -> None:
    """Test O'Brien-Fleming boundary calculation."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # Check checkpoints are equally spaced
    expected_checkpoints = [100, 200, 300]
    np.testing.assert_array_equal(design.boundaries.checkpoints, expected_checkpoints)

    # Check information fractions
    expected_info = np.array([1 / 3, 2 / 3, 1.0])
    np.testing.assert_array_almost_equal(
        design.boundaries.information_fractions, expected_info, decimal=5
    )

    # Check z-boundaries decrease over time (easier to stop later)
    assert design.boundaries.z_boundaries[0] > design.boundaries.z_boundaries[1]
    assert design.boundaries.z_boundaries[1] > design.boundaries.z_boundaries[2]

    # Final boundary should be close to 1.96 (α=0.05, two-sided)
    assert design.boundaries.z_boundaries[-1] == pytest.approx(1.96, abs=0.01)


def test_obrien_fleming_early_boundary_conservative() -> None:
    """Test that early boundaries are very conservative."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # First look should require z > 3.0 (very conservative)
    # O'Brien-Fleming at info=1/3: z = 1.96/sqrt(1/3) ≈ 3.39
    assert design.boundaries.z_boundaries[0] > 3.0


def test_check_stopping_continue() -> None:
    """Test stopping decision: continue collecting data."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # At first checkpoint with moderate z-statistic
    decision = design.check_stopping(n=100, z_statistic=2.5)

    # Should continue (need much higher z early on)
    assert decision == "continue"


def test_check_stopping_efficacy_early() -> None:
    """Test stopping decision: early efficacy stop."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # At first checkpoint with very strong evidence
    decision = design.check_stopping(n=100, z_statistic=5.0)

    # Should stop for efficacy (crosses boundary)
    assert decision == "stop_efficacy"


def test_check_stopping_efficacy_late() -> None:
    """Test stopping decision: efficacy at later checkpoint."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # At final checkpoint with moderate evidence
    decision = design.check_stopping(n=300, z_statistic=2.1)

    # Should stop for efficacy (final boundary ~1.96)
    assert decision == "stop_efficacy"


def test_check_stopping_futility() -> None:
    """Test stopping decision: futility."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # At interim with weak evidence and low conditional power
    decision = design.check_stopping(n=200, z_statistic=0.5, effect_size_estimate=0.1)

    # Should stop for futility (unlikely to succeed)
    assert decision == "stop_futility"


def test_check_stopping_past_max_n() -> None:
    """Test stopping decision after max_n."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # Beyond max sample size
    decision = design.check_stopping(n=400, z_statistic=2.5)

    # Should continue (no more checkpoints)
    assert decision == "continue"


def test_check_stopping_negative_z() -> None:
    """Test stopping with negative z-statistic (two-sided)."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # Strong negative z (two-sided test)
    decision = design.check_stopping(n=300, z_statistic=-2.5)

    # Should stop (absolute value crosses boundary)
    assert decision == "stop_efficacy"


def test_conditional_power_high() -> None:
    """Test conditional power calculation with strong interim results."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # At n=100 with strong z and large effect
    cond_power = design._conditional_power(
        n_current=100, z_current=3.0, effect_estimate=0.8
    )

    # Should have high conditional power (likely to succeed)
    assert cond_power > 0.80


def test_conditional_power_low() -> None:
    """Test conditional power calculation with weak interim results."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # At n=200 with weak z and small effect
    cond_power = design._conditional_power(
        n_current=200, z_current=0.5, effect_estimate=0.1
    )

    # Should have low conditional power (unlikely to succeed)
    assert cond_power < 0.30


def test_conditional_power_at_max_n() -> None:
    """Test conditional power at maximum sample size."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    # Already at max with significant result
    cond_power = design._conditional_power(
        n_current=300, z_current=2.5, effect_estimate=0.5
    )

    # Should be 1.0 (already significant)
    assert cond_power == 1.0


def test_expected_sample_size_under_h1() -> None:
    """Test expected sample size under alternative hypothesis."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    ess = design.expected_sample_size(true_effect=0.5)

    # Should expect to stop early (ESS < max_n)
    assert ess["under_h1"] < ess["max_n"]
    assert ess["reduction_percent_h1"] > 0


def test_expected_sample_size_under_h0() -> None:
    """Test expected sample size under null hypothesis."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    ess = design.expected_sample_size(true_effect=0.0)

    # Under H0, rarely stop early (ESS close to max_n)
    assert ess["under_h0"] < ess["max_n"]  # Should be less than max
    assert ess["under_h0"] >= 0.85 * ess["max_n"]  # But close to it


def test_expected_sample_size_large_effect() -> None:
    """Test ESS with large effect (more early stopping)."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    ess_small = design.expected_sample_size(true_effect=0.3)
    ess_large = design.expected_sample_size(true_effect=0.8)

    # Larger effect -> more early stopping -> smaller ESS
    assert ess_large["under_h1"] < ess_small["under_h1"]


def test_group_sequential_design_str() -> None:
    """Test string representation of design."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    output = str(design)
    assert "Group Sequential Design" in output
    assert "Max N: 300" in output
    assert "Looks: 3" in output
    assert "Alpha: 0.05" in output


def test_multiple_looks() -> None:
    """Test design with different numbers of looks."""
    design_2 = GroupSequentialDesign(max_n=300, num_looks=2, alpha=0.05)
    design_5 = GroupSequentialDesign(max_n=300, num_looks=5, alpha=0.05)

    # More looks -> more checkpoints
    assert len(design_2.boundaries.checkpoints) == 2
    assert len(design_5.boundaries.checkpoints) == 5

    # More looks -> earlier first checkpoint
    assert design_5.boundaries.checkpoints[0] < design_2.boundaries.checkpoints[0]


def test_different_alpha_levels() -> None:
    """Test design with different alpha levels."""
    design_05 = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)
    design_01 = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.01)

    # Stricter alpha -> higher z-boundaries
    for i in range(3):
        assert design_01.boundaries.z_boundaries[i] > design_05.boundaries.z_boundaries[i]


def test_custom_futility_threshold() -> None:
    """Test custom futility threshold."""
    design = GroupSequentialDesign(
        max_n=300, num_looks=3, alpha=0.05, futility_threshold=0.10
    )

    assert design.futility_threshold == 0.10

    # With stricter threshold, more likely to stop for futility
    decision = design.check_stopping(n=200, z_statistic=1.0, effect_size_estimate=0.2)

    # Might stop for futility with 10% threshold (vs 20% default)
    assert decision in ["continue", "stop_futility"]


def test_alpha_spending_increases() -> None:
    """Test that cumulative alpha spending increases monotonically."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    alpha_spending = design.boundaries.alpha_spending

    # Should increase monotonically
    assert alpha_spending[0] < alpha_spending[1] < alpha_spending[2]

    # Final spending should equal overall alpha
    assert alpha_spending[-1] == pytest.approx(design.alpha, abs=0.001)


def test_information_fraction_correct() -> None:
    """Test that information fractions are correct."""
    design = GroupSequentialDesign(max_n=300, num_looks=3, alpha=0.05)

    info_frac = design.boundaries.information_fractions

    # Should match sample size ratios
    expected = design.boundaries.checkpoints / design.max_n
    np.testing.assert_array_almost_equal(info_frac, expected, decimal=5)
