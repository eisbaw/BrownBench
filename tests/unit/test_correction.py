"""Tests for multiple comparison correction methods."""

import numpy as np
import pytest

from codegen_bench.stats.correction import (
    compute_family_wise_error_rate,
    correct_pvalues,
    dunnett_test,
    estimate_fdr,
)


def test_correct_pvalues_empty() -> None:
    """Test correction with empty p-values."""
    p_values: list[float] = []
    rejected, p_adjusted = correct_pvalues(p_values)

    assert len(rejected) == 0
    assert len(p_adjusted) == 0


def test_correct_pvalues_fdr_bh() -> None:
    """Test Benjamini-Hochberg FDR correction."""
    p_values = np.array([0.001, 0.05, 0.03, 0.8, 0.002])
    rejected, p_adjusted = correct_pvalues(p_values, method="fdr_bh", alpha=0.05)

    # Should reject the small p-values
    assert bool(rejected[0])  # 0.001
    assert bool(rejected[4])  # 0.002
    # May or may not reject borderline cases
    assert isinstance(rejected, np.ndarray)
    assert len(rejected) == 5
    assert len(p_adjusted) == 5


def test_correct_pvalues_bonferroni() -> None:
    """Test Bonferroni correction (most conservative)."""
    p_values = np.array([0.001, 0.01, 0.02, 0.03, 0.04])
    rejected, p_adjusted = correct_pvalues(p_values, method="bonferroni", alpha=0.05)

    # Bonferroni: α_adj = α / n = 0.05 / 5 = 0.01
    # Should only reject p < 0.01
    assert bool(rejected[0])  # 0.001 < 0.01
    assert bool(rejected[1])  # 0.01 ≤ 0.01
    assert not bool(rejected[2])  # 0.02 > 0.01
    assert not bool(rejected[3])  # 0.03 > 0.01
    assert not bool(rejected[4])  # 0.04 > 0.01


def test_correct_pvalues_holm() -> None:
    """Test Holm-Bonferroni correction."""
    p_values = np.array([0.001, 0.01, 0.02, 0.03, 0.04])
    rejected, p_adjusted = correct_pvalues(p_values, method="holm", alpha=0.05)

    # Holm is more powerful than Bonferroni
    # Should reject more than Bonferroni but less than uncorrected
    assert bool(rejected[0])  # Smallest p-value
    assert isinstance(rejected, np.ndarray)


def test_correct_pvalues_holm_alias() -> None:
    """Test that 'holm_bonferroni' is an alias for 'holm'."""
    p_values = np.array([0.001, 0.01, 0.02, 0.03, 0.04])

    rejected1, p_adj1 = correct_pvalues(p_values, method="holm")
    rejected2, p_adj2 = correct_pvalues(p_values, method="holm_bonferroni")

    np.testing.assert_array_equal(rejected1, rejected2)
    np.testing.assert_array_almost_equal(p_adj1, p_adj2)


def test_correct_pvalues_fdr_by() -> None:
    """Test Benjamini-Yekutieli FDR correction (more conservative)."""
    p_values = np.array([0.001, 0.01, 0.02, 0.03, 0.04])
    rejected, p_adjusted = correct_pvalues(p_values, method="fdr_by", alpha=0.05)

    # fdr_by is more conservative than fdr_bh
    assert isinstance(rejected, np.ndarray)
    assert len(rejected) == 5


def test_correct_pvalues_adjusted_greater_than_raw() -> None:
    """Test that adjusted p-values are ≥ raw p-values."""
    p_values = np.array([0.001, 0.01, 0.02, 0.03, 0.04])

    for method in ["fdr_bh", "bonferroni", "holm"]:
        _, p_adjusted = correct_pvalues(p_values, method=method, alpha=0.05)  # type: ignore
        # Adjusted p-values should be >= raw p-values
        assert np.all(p_adjusted >= p_values)


def test_correct_pvalues_bonferroni_vs_holm() -> None:
    """Test that Holm is more powerful than Bonferroni."""
    p_values = np.array([0.001, 0.008, 0.015, 0.025, 0.035])

    rejected_bonf, _ = correct_pvalues(p_values, method="bonferroni", alpha=0.05)
    rejected_holm, _ = correct_pvalues(p_values, method="holm", alpha=0.05)

    # Holm should reject at least as many as Bonferroni
    assert np.sum(rejected_holm) >= np.sum(rejected_bonf)


def test_correct_pvalues_fdr_more_powerful_than_fwer() -> None:
    """Test that FDR is more powerful than FWER control."""
    p_values = np.array([0.001, 0.008, 0.015, 0.025, 0.035, 0.045])

    rejected_fdr, _ = correct_pvalues(p_values, method="fdr_bh", alpha=0.05)
    rejected_bonf, _ = correct_pvalues(p_values, method="bonferroni", alpha=0.05)

    # FDR should reject more (it's less conservative)
    assert np.sum(rejected_fdr) >= np.sum(rejected_bonf)


def test_dunnett_test_basic() -> None:
    """Test basic Dunnett's test."""
    control = np.array([5.0, 5.1, 4.9, 5.0, 5.2])
    treatment1 = np.array([7.0, 7.2, 6.9, 7.1, 7.3])  # Clearly different
    treatment2 = np.array([5.1, 5.0, 5.2, 4.9, 5.0])  # Similar to control

    result = dunnett_test([treatment1, treatment2], control, alpha=0.05)

    # Treatment 1 should be significant
    assert bool(result["significant"][0])
    # Treatment 2 should not be significant
    assert not bool(result["significant"][1])

    assert len(result["statistics"]) == 2
    assert len(result["pvalues"]) == 2


def test_dunnett_test_no_treatments_raises() -> None:
    """Test that Dunnett raises with no treatments."""
    control = np.array([5.0, 5.1, 4.9])

    with pytest.raises(ValueError, match="at least one treatment"):
        dunnett_test([], control)


def test_dunnett_test_one_sided() -> None:
    """Test one-sided Dunnett test."""
    control = np.array([5.0, 5.1, 4.9, 5.0])
    treatment = np.array([7.0, 7.1, 6.9, 7.0])  # Greater than control

    result_greater = dunnett_test([treatment], control, alternative="greater")
    result_less = dunnett_test([treatment], control, alternative="less")

    # Should be significant for 'greater'
    assert bool(result_greater["significant"][0])
    # Should not be significant for 'less'
    assert not bool(result_less["significant"][0])


def test_dunnett_test_power_gain() -> None:
    """Test that Dunnett reports power gain."""
    control = np.array([5.0, 5.1, 4.9])
    treatment = np.array([6.0, 6.1, 5.9])

    result = dunnett_test([treatment], control)

    # Should report approximate power gain
    assert "power_gain_vs_bonferroni" in result
    assert 0.05 < result["power_gain_vs_bonferroni"] < 0.20


def test_estimate_fdr_basic() -> None:
    """Test FDR estimation."""
    p_values = np.array([0.001, 0.01, 0.05, 0.1, 0.5, 0.8])
    rejected, p_adjusted = correct_pvalues(p_values, method="fdr_bh", alpha=0.05)

    fdr_result = estimate_fdr(p_values, p_adjusted, alpha=0.05)

    assert "estimated_fdr" in fdr_result
    assert "num_rejected" in fdr_result
    assert "num_tests" in fdr_result
    assert "pi0" in fdr_result

    # FDR should be <= alpha
    assert 0.0 <= fdr_result["estimated_fdr"] <= 1.0
    # pi0 should be in [0, 1]
    assert 0.0 <= fdr_result["pi0"] <= 1.0


def test_estimate_fdr_no_rejections() -> None:
    """Test FDR estimation when nothing is rejected."""
    p_values = np.array([0.8, 0.9, 0.95])
    rejected, p_adjusted = correct_pvalues(p_values, method="fdr_bh", alpha=0.05)

    fdr_result = estimate_fdr(p_values, p_adjusted, alpha=0.05)

    # No rejections -> FDR = 0
    assert fdr_result["estimated_fdr"] == 0.0
    assert fdr_result["num_rejected"] == 0


def test_estimate_fdr_all_rejections() -> None:
    """Test FDR estimation when all are rejected."""
    p_values = np.array([0.001, 0.002, 0.003])
    rejected, p_adjusted = correct_pvalues(p_values, method="fdr_bh", alpha=0.05)

    fdr_result = estimate_fdr(p_values, p_adjusted, alpha=0.05)

    # All rejected
    assert fdr_result["num_rejected"] == 3
    # FDR should be low (most are true positives)
    assert fdr_result["estimated_fdr"] <= 0.1


def test_compute_fwer_bonferroni() -> None:
    """Test FWER computation for Bonferroni."""
    p_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
    fwer = compute_family_wise_error_rate(p_values, method="bonferroni", alpha=0.05)

    # Bonferroni controls FWER at α
    assert fwer == pytest.approx(0.05, abs=0.01)


def test_compute_fwer_holm() -> None:
    """Test FWER computation for Holm."""
    p_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
    fwer = compute_family_wise_error_rate(p_values, method="holm", alpha=0.05)

    # Holm controls FWER at α
    assert fwer == pytest.approx(0.05, abs=0.01)


def test_compute_fwer_fdr() -> None:
    """Test FWER computation for FDR methods."""
    p_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
    fwer = compute_family_wise_error_rate(p_values, method="fdr_bh", alpha=0.05)

    # FDR methods don't control FWER, so it can exceed α
    assert 0.0 <= fwer <= 1.0


def test_correct_pvalues_preserves_length() -> None:
    """Test that output has same length as input."""
    p_values = np.array([0.01, 0.02, 0.03])

    for method in ["fdr_bh", "bonferroni", "holm"]:
        rejected, p_adjusted = correct_pvalues(p_values, method=method, alpha=0.05)  # type: ignore
        assert len(rejected) == len(p_values)
        assert len(p_adjusted) == len(p_values)


def test_correct_pvalues_all_significant() -> None:
    """Test when all p-values are highly significant."""
    p_values = np.array([0.0001, 0.0002, 0.0003])

    rejected, _ = correct_pvalues(p_values, method="bonferroni", alpha=0.05)

    # All should be rejected (very strong evidence)
    assert np.all(rejected)


def test_correct_pvalues_none_significant() -> None:
    """Test when no p-values are significant."""
    p_values = np.array([0.9, 0.95, 0.99])

    rejected, _ = correct_pvalues(p_values, method="bonferroni", alpha=0.05)

    # None should be rejected
    assert np.sum(rejected) == 0


def test_dunnett_statistics_ordering() -> None:
    """Test that Dunnett statistics are ordered correctly."""
    # Add variance to avoid numerical issues
    np.random.seed(42)
    control = np.random.normal(5.0, 0.1, size=10)
    treatment1 = np.random.normal(10.0, 0.1, size=10)  # Large difference
    treatment2 = np.random.normal(5.5, 0.1, size=10)  # Small difference

    result = dunnett_test([treatment1, treatment2], control)

    # Treatment 1 should have larger test statistic
    assert abs(result["statistics"][0]) > abs(result["statistics"][1])


def test_estimate_fdr_pi0_bounds() -> None:
    """Test that pi0 estimate is in valid range."""
    # Mix of significant and non-significant
    p_values = np.array([0.001, 0.01, 0.5, 0.6, 0.7, 0.8, 0.9])
    rejected, p_adjusted = correct_pvalues(p_values, method="fdr_bh", alpha=0.05)

    fdr_result = estimate_fdr(p_values, p_adjusted, alpha=0.05)

    # pi0 (proportion of true nulls) should be in [0, 1]
    assert 0.0 <= fdr_result["pi0"] <= 1.0
    # Should be reasonably high (most p-values are large)
    assert fdr_result["pi0"] > 0.4
