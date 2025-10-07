"""Effect size calculations with confidence intervals.

This module implements effect size metrics for comparing code generation approaches.
All effect sizes include bootstrap confidence intervals and interpretations.

Effect sizes quantify the magnitude of differences beyond statistical significance.
They enable meta-analysis and practical significance assessment.

References:
- Hedges & Olkin (1985): "Statistical Methods for Meta-Analysis"
- Kampenes et al. (2007): "A systematic review of effect size in SE experiments"
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats


@dataclass
class EffectSize:
    """Effect size with confidence interval and interpretation.

    Attributes:
        metric: Effect size metric name ('hedges_g', 'cohens_d', 'cohens_h', 'cles')
        value: Point estimate of effect size
        ci_lower: Lower bound of confidence interval
        ci_upper: Upper bound of confidence interval
        cles: Common Language Effect Size (probability of superiority)
        interpretation: Qualitative interpretation ('negligible', 'small', 'medium', 'large')
        sample_sizes: Tuple of (n_a, n_b) for documentation
    """

    metric: str
    value: float
    ci_lower: float
    ci_upper: float
    cles: float
    interpretation: str
    sample_sizes: tuple[int, int]

    def __str__(self) -> str:
        """String representation."""
        return (
            f"{self.metric}={self.value:.3f} "
            f"[{self.ci_lower:.3f}, {self.ci_upper:.3f}], "
            f"CLES={self.cles:.3f}, "
            f"interpretation={self.interpretation}"
        )


def hedges_g(
    group_a: np.ndarray,
    group_b: np.ndarray,
    paired: bool = False,
    ci: float = 0.95,
    n_bootstrap: int = 10000,
) -> EffectSize:
    """Calculate Hedges' g with bootstrap confidence interval.

    Hedges' g is a bias-corrected version of Cohen's d for small samples.
    Use paired=True when comparing the same solutions across different arenas.

    Args:
        group_a: Measurements for group A
        group_b: Measurements for group B
        paired: Whether samples are paired (default: False)
        ci: Confidence level (default: 0.95)
        n_bootstrap: Number of bootstrap resamples (default: 10000)

    Returns:
        EffectSize with g, CI, CLES, and interpretation

    Note:
        For paired data (e.g., same solutions in different arenas),
        use paired=True to account for within-subject correlation.
        This is the **correct** approach per the PRD.
    """
    group_a = np.asarray(group_a, dtype=float)
    group_b = np.asarray(group_b, dtype=float)

    if paired and len(group_a) != len(group_b):
        raise ValueError("Paired samples must have same length")

    n_a, n_b = len(group_a), len(group_b)

    if paired:
        # Paired design: use differences
        differences = group_a - group_b
        mean_diff = np.mean(differences)
        sd_diff = np.std(differences, ddof=1)

        if sd_diff == 0:
            # No variance in differences
            g = 0.0
        else:
            # Cohen's d_z for paired samples
            d_z = mean_diff / sd_diff

            # Hedges' correction for paired data
            correction = 1 - (3 / (4 * n_a - 5))
            g = d_z * correction

    else:
        # Independent samples
        pooled_sd = _pooled_std(group_a, group_b)

        if pooled_sd == 0:
            # No variance
            g = 0.0
        else:
            # Cohen's d
            d = (np.mean(group_a) - np.mean(group_b)) / pooled_sd

            # Hedges' correction for small samples
            correction = 1 - (3 / (4 * (n_a + n_b) - 9))
            g = d * correction

    # Bootstrap confidence interval
    ci_lower, ci_upper = _bootstrap_ci(
        group_a, group_b, paired=paired, ci=ci, n_bootstrap=n_bootstrap
    )

    # Common Language Effect Size
    cles = _compute_cles(group_a, group_b)

    # Interpretation (software engineering norms)
    interpretation = _interpret_hedges_g(g)

    return EffectSize(
        metric="hedges_g_paired" if paired else "hedges_g",
        value=g,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        cles=cles,
        interpretation=interpretation,
        sample_sizes=(n_a, n_b),
    )


def cohens_h(p1: float, p2: float) -> float:
    """Calculate Cohen's h for comparing two proportions.

    Cohen's h measures effect size for differences in proportions.
    Useful for comparing win rates between approaches.

    Args:
        p1: Proportion in group 1 (0-1)
        p2: Proportion in group 2 (0-1)

    Returns:
        Cohen's h

    Interpretation:
        h < 0.20: negligible
        0.20 ≤ h < 0.50: small
        0.50 ≤ h < 0.80: medium
        h ≥ 0.80: large
    """
    # Arcsine transformation
    phi1 = 2 * np.arcsin(np.sqrt(p1))
    phi2 = 2 * np.arcsin(np.sqrt(p2))

    return phi1 - phi2


def _pooled_std(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Calculate pooled standard deviation."""
    n_a, n_b = len(group_a), len(group_b)

    var_a = np.var(group_a, ddof=1)
    var_b = np.var(group_b, ddof=1)

    pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)

    return np.sqrt(pooled_var)


def _bootstrap_ci(
    group_a: np.ndarray,
    group_b: np.ndarray,
    paired: bool,
    ci: float,
    n_bootstrap: int,
) -> tuple[float, float]:
    """Bootstrap confidence interval for Hedges' g."""

    def _hedges_g_stat(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate Hedges' g for bootstrap."""
        if paired:
            differences = a - b
            mean_diff = np.mean(differences)
            sd_diff = np.std(differences, ddof=1)
            if sd_diff == 0:
                return 0.0
            d_z = mean_diff / sd_diff
            correction = 1 - (3 / (4 * len(a) - 5))
            return d_z * correction
        else:
            pooled_sd = _pooled_std(a, b)
            if pooled_sd == 0:
                return 0.0
            d = (np.mean(a) - np.mean(b)) / pooled_sd
            correction = 1 - (3 / (4 * (len(a) + len(b)) - 9))
            return d * correction

    # Bootstrap resampling
    bootstrap_gs = []
    rng = np.random.RandomState(42)  # Reproducible

    for _ in range(n_bootstrap):
        if paired:
            # Resample pairs together
            indices = rng.choice(len(group_a), size=len(group_a), replace=True)
            a_boot = group_a[indices]
            b_boot = group_b[indices]
        else:
            # Resample independently
            indices_a = rng.choice(len(group_a), size=len(group_a), replace=True)
            indices_b = rng.choice(len(group_b), size=len(group_b), replace=True)
            a_boot = group_a[indices_a]
            b_boot = group_b[indices_b]

        g_boot = _hedges_g_stat(a_boot, b_boot)
        bootstrap_gs.append(g_boot)

    # Percentile method
    alpha = 1 - ci
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    ci_lower = np.percentile(bootstrap_gs, lower_percentile)
    ci_upper = np.percentile(bootstrap_gs, upper_percentile)

    return float(ci_lower), float(ci_upper)


def _compute_cles(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Compute Common Language Effect Size.

    CLES is the probability that a random sample from A
    is greater than a random sample from B.

    Returns:
        Probability P(A > B)
    """
    # Count all comparisons
    comparisons = [(a > b) for a in group_a for b in group_b]

    if len(comparisons) == 0:
        return 0.5

    return float(np.mean(comparisons))


def _interpret_hedges_g(g: float) -> Literal["negligible", "small", "medium", "large"]:
    """Interpret Hedges' g using software engineering norms.

    Based on meta-analyses in software engineering (Kampenes et al. 2007):
    - Small: |g| ≈ 0.20
    - Medium: |g| ≈ 0.50
    - Large: |g| ≈ 0.80

    Do NOT use generic Cohen benchmarks without domain context.
    """
    abs_g = abs(g)

    if abs_g < 0.20:
        return "negligible"
    elif abs_g < 0.50:
        return "small"
    elif abs_g < 0.80:
        return "medium"
    else:
        return "large"
