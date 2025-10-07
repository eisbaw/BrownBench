"""Tests for Multi-Arm Multi-Stage (MAMS) adaptive design."""

import numpy as np
import pytest

from codegen_bench.stats.adaptive.mams import MAMSConfig, MAMSDesign, MAMSResult


def test_mams_config_creation() -> None:
    """Test MAMS configuration creation."""
    config = MAMSConfig(num_arms=5, control_id="baseline")

    assert config.num_arms == 5
    assert config.control_id == "baseline"
    assert config.alpha == 0.05
    assert config.power == 0.80
    assert config.max_selected == 3
    assert config.futility_threshold == 0.2


def test_mams_config_custom() -> None:
    """Test MAMS configuration with custom values."""
    config = MAMSConfig(
        num_arms=10,
        control_id="control",
        alpha=0.01,
        power=0.90,
        max_selected=5,
        futility_threshold=0.3,
    )

    assert config.num_arms == 10
    assert config.alpha == 0.01
    assert config.power == 0.90
    assert config.max_selected == 5
    assert config.futility_threshold == 0.3


def test_mams_design_initialization() -> None:
    """Test MAMS design initialization."""
    config = MAMSConfig(num_arms=5, control_id="baseline")
    design = MAMSDesign(config)

    assert design.config == config


def test_mams_evaluate_stage1_basic() -> None:
    """Test Stage 1 evaluation with clear winner."""
    np.random.seed(42)

    config = MAMSConfig(num_arms=5, control_id="baseline", max_selected=3)
    design = MAMSDesign(config)

    # Control performs moderately
    # DUT2 and DUT5 perform much better
    # DUT1 and DUT4 perform worse
    # DUT3 performs slightly better
    results = {
        "baseline": np.random.normal(0.90, 0.02, 20).tolist(),
        "dut1": np.random.normal(0.85, 0.02, 20).tolist(),
        "dut2": np.random.normal(0.98, 0.02, 20).tolist(),
        "dut3": np.random.normal(0.92, 0.02, 20).tolist(),
        "dut4": np.random.normal(0.83, 0.02, 20).tolist(),
        "dut5": np.random.normal(0.97, 0.02, 20).tolist(),
    }

    result = design.evaluate_stage1(results, higher_is_better=True)

    assert isinstance(result, MAMSResult)
    assert len(result.selected_arms) <= 3
    assert len(result.eliminated_arms) >= 2

    # Top performers should be selected
    assert "dut2" in result.selected_arms
    assert "dut5" in result.selected_arms

    # Poor performers should be eliminated
    assert "dut1" in result.eliminated_arms
    assert "dut4" in result.eliminated_arms

    assert result.decision in ["continue", "stop_futility", "stop_efficacy"]


def test_mams_evaluate_stage1_no_control() -> None:
    """Test that missing control raises error."""
    config = MAMSConfig(num_arms=3, control_id="baseline")
    design = MAMSDesign(config)

    results = {
        "dut1": [0.8, 0.9, 0.85],
        "dut2": [0.9, 0.95, 0.92],
    }

    with pytest.raises(ValueError, match="Control arm"):
        design.evaluate_stage1(results)


def test_mams_evaluate_stage1_no_treatments() -> None:
    """Test that no treatment arms raises error."""
    config = MAMSConfig(num_arms=3, control_id="baseline")
    design = MAMSDesign(config)

    results = {
        "baseline": [0.8, 0.9, 0.85],
    }

    with pytest.raises(ValueError, match="No treatment arms"):
        design.evaluate_stage1(results)


def test_mams_evaluate_stage1_lower_is_better() -> None:
    """Test Stage 1 with lower_is_better metric (e.g., error rate)."""
    np.random.seed(42)

    config = MAMSConfig(num_arms=4, control_id="baseline", max_selected=2)
    design = MAMSDesign(config)

    # Lower error rate is better
    # DUT2 has lowest error rate
    results = {
        "baseline": np.random.normal(0.10, 0.01, 20).tolist(),
        "dut1": np.random.normal(0.12, 0.01, 20).tolist(),
        "dut2": np.random.normal(0.03, 0.01, 20).tolist(),
        "dut3": np.random.normal(0.09, 0.01, 20).tolist(),
        "dut4": np.random.normal(0.15, 0.01, 20).tolist(),
    }

    result = design.evaluate_stage1(results, higher_is_better=False)

    # DUT2 should be selected (lowest error)
    assert "dut2" in result.selected_arms


def test_mams_statistics_dict() -> None:
    """Test that statistics and p-values are returned as dicts."""
    np.random.seed(42)

    config = MAMSConfig(num_arms=3, control_id="baseline")
    design = MAMSDesign(config)

    results = {
        "baseline": np.random.normal(0.90, 0.02, 20).tolist(),
        "dut1": np.random.normal(0.95, 0.02, 20).tolist(),
        "dut2": np.random.normal(0.85, 0.02, 20).tolist(),
        "dut3": np.random.normal(0.92, 0.02, 20).tolist(),
    }

    result = design.evaluate_stage1(results)

    assert isinstance(result.statistics, dict)
    assert isinstance(result.p_values, dict)

    # All treatment arms should have statistics
    assert "dut1" in result.statistics
    assert "dut2" in result.statistics
    assert "dut3" in result.statistics

    assert "dut1" in result.p_values
    assert "dut2" in result.p_values
    assert "dut3" in result.p_values


def test_mams_futility_threshold() -> None:
    """Test that futility threshold filters out small effects."""
    np.random.seed(42)

    config = MAMSConfig(
        num_arms=3,
        control_id="baseline",
        max_selected=3,
        futility_threshold=0.5,  # High threshold
    )
    design = MAMSDesign(config)

    # All DUTs only slightly better than baseline
    results = {
        "baseline": np.random.normal(0.90, 0.02, 20).tolist(),
        "dut1": np.random.normal(0.91, 0.02, 20).tolist(),
        "dut2": np.random.normal(0.92, 0.02, 20).tolist(),
        "dut3": np.random.normal(0.91, 0.02, 20).tolist(),
    }

    result = design.evaluate_stage1(results)

    # With high futility threshold, small effects should be eliminated
    # Result may be stop_futility or have fewer selected
    assert len(result.selected_arms) < 3 or result.decision == "stop_futility"


def test_mams_all_arms_worse_than_control() -> None:
    """Test when all treatment arms perform worse than control."""
    np.random.seed(42)

    config = MAMSConfig(num_arms=3, control_id="baseline")
    design = MAMSDesign(config)

    results = {
        "baseline": np.random.normal(0.95, 0.02, 20).tolist(),
        "dut1": np.random.normal(0.85, 0.02, 20).tolist(),
        "dut2": np.random.normal(0.80, 0.02, 20).tolist(),
        "dut3": np.random.normal(0.82, 0.02, 20).tolist(),
    }

    result = design.evaluate_stage1(results, higher_is_better=True)

    # All arms should be eliminated
    assert len(result.selected_arms) == 0
    assert len(result.eliminated_arms) == 3
    assert result.decision == "stop_futility"


def test_mams_compute_stage1_sample_size() -> None:
    """Test sample size computation for Stage 1."""
    config = MAMSConfig(num_arms=5, control_id="baseline")
    design = MAMSDesign(config)

    # Medium effect size
    n = design.compute_stage1_sample_size(effect_size=0.5)

    assert n >= 10  # Minimum
    assert n < 200  # Reasonable upper bound for medium effect

    # Small effect requires larger sample
    n_small = design.compute_stage1_sample_size(effect_size=0.2)
    assert n_small > n


def test_mams_compute_stage1_sample_size_large_effect() -> None:
    """Test sample size for large effect."""
    config = MAMSConfig(num_arms=5, control_id="baseline")
    design = MAMSDesign(config)

    # Large effect requires smaller sample
    n = design.compute_stage1_sample_size(effect_size=0.8)

    assert n >= 10
    assert n < 50  # Large effects need fewer samples


def test_mams_compute_expected_cost_savings() -> None:
    """Test cost savings computation."""
    config = MAMSConfig(num_arms=10, control_id="baseline", max_selected=3)
    design = MAMSDesign(config)

    savings = design.compute_expected_cost_savings()

    assert "mams_cost" in savings
    assert "naive_cost" in savings
    assert "savings" in savings
    assert "savings_percent" in savings
    assert "eliminated_early" in savings

    # MAMS should be cheaper than naive
    assert savings["mams_cost"] < savings["naive_cost"]
    assert savings["savings"] > 0
    assert savings["savings_percent"] > 0

    # Eliminated early should be num_arms - max_selected
    assert savings["eliminated_early"] == 7


def test_mams_cost_savings_scales_with_arms() -> None:
    """Test that cost savings increase with more arms."""
    config_small = MAMSConfig(num_arms=5, control_id="baseline", max_selected=2)
    design_small = MAMSDesign(config_small)

    config_large = MAMSConfig(num_arms=20, control_id="baseline", max_selected=2)
    design_large = MAMSDesign(config_large)

    savings_small = design_small.compute_expected_cost_savings()
    savings_large = design_large.compute_expected_cost_savings()

    # More arms = more savings
    assert savings_large["savings_percent"] > savings_small["savings_percent"]
    assert savings_large["eliminated_early"] > savings_small["eliminated_early"]


def test_mams_result_dataclass() -> None:
    """Test MAMSResult dataclass attributes."""
    result = MAMSResult(
        selected_arms=["dut1", "dut2"],
        eliminated_arms=["dut3", "dut4"],
        statistics={"dut1": 2.5, "dut2": 3.0, "dut3": 1.0, "dut4": 0.5},
        p_values={"dut1": 0.01, "dut2": 0.005, "dut3": 0.2, "dut4": 0.5},
        decision="continue",
    )

    assert len(result.selected_arms) == 2
    assert len(result.eliminated_arms) == 2
    assert len(result.statistics) == 4
    assert len(result.p_values) == 4
    assert result.decision == "continue"


def test_mams_pooled_std() -> None:
    """Test pooled standard deviation calculation."""
    config = MAMSConfig(num_arms=2, control_id="baseline")
    design = MAMSDesign(config)

    group_a = np.array([1, 2, 3, 4, 5], dtype=float)
    group_b = np.array([2, 3, 4, 5, 6], dtype=float)

    pooled_std = design._pooled_std(group_a, group_b)

    assert pooled_std > 0
    # Should be approximately sqrt(2) for these groups
    assert 1.0 < pooled_std < 2.0


def test_mams_pooled_std_zero_variance() -> None:
    """Test pooled std with zero variance."""
    config = MAMSConfig(num_arms=2, control_id="baseline")
    design = MAMSDesign(config)

    group_a = np.array([5, 5, 5], dtype=float)
    group_b = np.array([5, 5, 5], dtype=float)

    pooled_std = design._pooled_std(group_a, group_b)

    assert pooled_std == 0.0


def test_mams_pooled_std_small_samples() -> None:
    """Test pooled std with very small samples."""
    config = MAMSConfig(num_arms=2, control_id="baseline")
    design = MAMSDesign(config)

    group_a = np.array([1], dtype=float)
    group_b = np.array([2], dtype=float)

    pooled_std = design._pooled_std(group_a, group_b)

    # Should return 0 for insufficient samples
    assert pooled_std == 0.0


def test_mams_realistic_scenario() -> None:
    """Test realistic MAMS scenario with multiple DUTs."""
    np.random.seed(123)

    # 8 experimental DUTs competing
    config = MAMSConfig(num_arms=8, control_id="gpt-3.5", max_selected=3, alpha=0.05)
    design = MAMSDesign(config)

    # Stage 1: cheap metric (e.g., compilation success rate)
    # Control: 85% success
    # Top performers: 92-95%
    # Mid performers: 87-90%
    # Poor performers: 78-82%
    results = {
        "gpt-3.5": np.random.normal(0.85, 0.03, 30).tolist(),
        "dut1": np.random.normal(0.93, 0.03, 30).tolist(),  # Top
        "dut2": np.random.normal(0.88, 0.03, 30).tolist(),  # Mid
        "dut3": np.random.normal(0.95, 0.03, 30).tolist(),  # Top
        "dut4": np.random.normal(0.80, 0.03, 30).tolist(),  # Poor
        "dut5": np.random.normal(0.89, 0.03, 30).tolist(),  # Mid
        "dut6": np.random.normal(0.92, 0.03, 30).tolist(),  # Top
        "dut7": np.random.normal(0.78, 0.03, 30).tolist(),  # Poor
        "dut8": np.random.normal(0.81, 0.03, 30).tolist(),  # Poor
    }

    result = design.evaluate_stage1(results)

    # Should select top 3 performers
    assert len(result.selected_arms) <= 3

    # Top performers should be in selected
    top_duts = ["dut1", "dut3", "dut6"]
    selected_count = sum(1 for dut in top_duts if dut in result.selected_arms)
    assert selected_count >= 2  # At least 2 of the top 3

    # Poor performers should be eliminated
    poor_duts = ["dut4", "dut7", "dut8"]
    eliminated_count = sum(1 for dut in poor_duts if dut in result.eliminated_arms)
    assert eliminated_count >= 2  # At least 2 poor ones eliminated

    # Compute cost savings
    savings = design.compute_expected_cost_savings()
    assert savings["eliminated_early"] == 5  # 8 - 3 = 5 eliminated


def test_mams_stage1_sample_size_power() -> None:
    """Test sample size scales with power requirement."""
    config_low = MAMSConfig(num_arms=5, control_id="baseline", power=0.70)
    config_high = MAMSConfig(num_arms=5, control_id="baseline", power=0.90)

    design_low = MAMSDesign(config_low)
    design_high = MAMSDesign(config_high)

    n_low = design_low.compute_stage1_sample_size(effect_size=0.5)
    n_high = design_high.compute_stage1_sample_size(effect_size=0.5)

    # Higher power requires larger sample
    assert n_high > n_low


def test_mams_dunnett_fallback_to_bonferroni(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fallback to Bonferroni when scipy.stats.dunnett unavailable."""
    import sys
    from unittest import mock

    np.random.seed(42)

    config = MAMSConfig(num_arms=3, control_id="baseline")
    design = MAMSDesign(config)

    # Create test data
    results = {
        "baseline": np.random.normal(0.90, 0.02, 20).tolist(),
        "dut1": np.random.normal(0.95, 0.02, 20).tolist(),
        "dut2": np.random.normal(0.85, 0.02, 20).tolist(),
        "dut3": np.random.normal(0.92, 0.02, 20).tolist(),
    }

    # Mock scipy.stats to not have dunnett attribute
    with mock.patch("scipy.stats.dunnett", side_effect=AttributeError("dunnett not available")):
        # This should trigger the fallback to Bonferroni
        result = design.evaluate_stage1(results)

        # Result should still be valid
        assert isinstance(result, MAMSResult)
        assert len(result.selected_arms) + len(result.eliminated_arms) == 3

        # Statistics and p-values should be present (from t-test fallback)
        assert "dut1" in result.statistics
        assert "dut1" in result.p_values

        # P-values should be Bonferroni-corrected (multiplied by num_treatments)
        # They should be larger than uncorrected values
        for p_val in result.p_values.values():
            assert 0 <= p_val <= 1.0
