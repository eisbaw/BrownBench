"""Statistical power analysis and sample size calculation.

Power analysis answers critical questions:
1. How many samples do we need to detect a meaningful difference?
2. What effect size can we detect with our sample size?
3. What is the achieved power of our study?

This module implements power analysis for:
- Two-sample comparisons (t-tests)
- Proportions (win rate differences)
- Effect size determination

References:
- Cohen (1988): "Statistical Power Analysis for the Behavioral Sciences"
- G*Power: Statistical power analysis software
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats
from statsmodels.stats.power import tt_ind_solve_power, zt_ind_solve_power


@dataclass
class PowerAnalysisResult:
    """Result of power analysis calculation."""

    power: float  # Achieved or required power
    sample_size: int | None  # Required sample size per group
    effect_size: float | None  # Detectable effect size
    alpha: float  # Significance level
    test_type: str  # Type of test (t-test, proportion, etc.)
    notes: str = ""  # Additional context

    def __str__(self) -> str:
        """String representation."""
        parts = [
            f"Power Analysis ({self.test_type}):",
            f"  Power: {self.power:.3f}",
            f"  Alpha: {self.alpha}",
        ]
        if self.sample_size:
            parts.append(f"  Sample size (per group): {self.sample_size}")
        if self.effect_size:
            parts.append(f"  Detectable effect size: {self.effect_size:.3f}")
        if self.notes:
            parts.append(f"  Notes: {self.notes}")
        return "\n".join(parts)


def calculate_sample_size_ttest(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
    ratio: float = 1.0,
) -> PowerAnalysisResult:
    """Calculate required sample size for two-sample t-test.

    Args:
        effect_size: Expected effect size (Cohen's d or Hedges' g)
        alpha: Significance level (default: 0.05)
        power: Desired statistical power (default: 0.80)
        alternative: Type of test ('two-sided', 'larger', 'smaller')
        ratio: Ratio of sample sizes (n2/n1, default: 1.0 for equal groups)

    Returns:
        PowerAnalysisResult with required sample size

    Example:
        >>> result = calculate_sample_size_ttest(effect_size=0.5, power=0.80)
        >>> result.sample_size
        64  # Need 64 per group to detect d=0.5 with 80% power
    """
    # statsmodels expects effect size as absolute value for 'larger'/'smaller'
    effect_size_abs = abs(effect_size)

    # Calculate required sample size for group 1
    n1 = tt_ind_solve_power(
        effect_size=effect_size_abs,
        alpha=alpha,
        power=power,
        ratio=ratio,
        alternative=alternative,
    )

    # Round up to ensure sufficient power
    n1 = int(np.ceil(n1))

    notes = []
    if ratio != 1.0:
        n2 = int(np.ceil(n1 * ratio))
        notes.append(f"n1={n1}, n2={n2} (ratio={ratio})")
    else:
        notes.append(f"Equal groups: {n1} per group")

    return PowerAnalysisResult(
        power=power,
        sample_size=n1,
        effect_size=effect_size,
        alpha=alpha,
        test_type="independent t-test",
        notes="; ".join(notes),
    )


def calculate_power_ttest(
    sample_size: int,
    effect_size: float,
    alpha: float = 0.05,
    alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
    ratio: float = 1.0,
) -> PowerAnalysisResult:
    """Calculate achieved power for two-sample t-test.

    Args:
        sample_size: Sample size per group (for group 1 if ratio != 1)
        effect_size: Observed or expected effect size
        alpha: Significance level (default: 0.05)
        alternative: Type of test ('two-sided', 'larger', 'smaller')
        ratio: Ratio of sample sizes (n2/n1, default: 1.0)

    Returns:
        PowerAnalysisResult with achieved power

    Example:
        >>> result = calculate_power_ttest(sample_size=64, effect_size=0.5)
        >>> result.power
        0.80  # 80% power to detect d=0.5 with n=64
    """
    effect_size_abs = abs(effect_size)

    power = tt_ind_solve_power(
        effect_size=effect_size_abs,
        nobs1=sample_size,
        alpha=alpha,
        ratio=ratio,
        alternative=alternative,
    )

    notes = []
    if ratio != 1.0:
        n2 = int(sample_size * ratio)
        notes.append(f"n1={sample_size}, n2={n2}")
    else:
        notes.append(f"n={sample_size} per group")

    return PowerAnalysisResult(
        power=float(power),
        sample_size=sample_size,
        effect_size=effect_size,
        alpha=alpha,
        test_type="independent t-test",
        notes="; ".join(notes),
    )


def calculate_minimum_detectable_effect(
    sample_size: int,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
    ratio: float = 1.0,
) -> PowerAnalysisResult:
    """Calculate minimum detectable effect size.

    Args:
        sample_size: Available sample size per group
        alpha: Significance level (default: 0.05)
        power: Desired statistical power (default: 0.80)
        alternative: Type of test ('two-sided', 'larger', 'smaller')
        ratio: Ratio of sample sizes (n2/n1, default: 1.0)

    Returns:
        PowerAnalysisResult with minimum detectable effect size

    Example:
        >>> result = calculate_minimum_detectable_effect(sample_size=30)
        >>> result.effect_size
        0.74  # Can detect effects ≥ 0.74 with n=30, power=0.80
    """
    effect_size = tt_ind_solve_power(
        nobs1=sample_size,
        alpha=alpha,
        power=power,
        ratio=ratio,
        alternative=alternative,
    )

    return PowerAnalysisResult(
        power=power,
        sample_size=sample_size,
        effect_size=float(effect_size),
        alpha=alpha,
        test_type="independent t-test",
        notes=f"Minimum detectable effect with n={sample_size} per group",
    )


def calculate_sample_size_proportion(
    p1: float,
    p2: float,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
    ratio: float = 1.0,
) -> PowerAnalysisResult:
    """Calculate required sample size for comparing two proportions.

    Args:
        p1: Proportion in group 1 (e.g., baseline win rate)
        p2: Proportion in group 2 (e.g., treatment win rate)
        alpha: Significance level (default: 0.05)
        power: Desired statistical power (default: 0.80)
        alternative: Type of test ('two-sided', 'larger', 'smaller')
        ratio: Ratio of sample sizes (n2/n1, default: 1.0)

    Returns:
        PowerAnalysisResult with required sample size

    Example:
        >>> # Detect win rate increase from 50% to 60%
        >>> result = calculate_sample_size_proportion(p1=0.5, p2=0.6, power=0.80)
        >>> result.sample_size
        388  # Need 388 comparisons per DUT
    """
    # Convert proportions to effect size (Cohen's h)
    # h = 2 * (arcsin(sqrt(p2)) - arcsin(sqrt(p1)))
    effect_size = 2 * (np.arcsin(np.sqrt(p2)) - np.arcsin(np.sqrt(p1)))

    # Calculate sample size using z-test for proportions
    n1 = zt_ind_solve_power(
        effect_size=abs(effect_size),
        alpha=alpha,
        power=power,
        ratio=ratio,
        alternative=alternative,
    )

    n1 = int(np.ceil(n1))

    notes = [f"p1={p1:.3f}, p2={p2:.3f}", f"Cohen's h={effect_size:.3f}"]
    if ratio != 1.0:
        n2 = int(np.ceil(n1 * ratio))
        notes.append(f"n1={n1}, n2={n2}")
    else:
        notes.append(f"{n1} per group")

    return PowerAnalysisResult(
        power=power,
        sample_size=n1,
        effect_size=effect_size,
        alpha=alpha,
        test_type="two-proportion z-test",
        notes="; ".join(notes),
    )


def calculate_power_proportion(
    sample_size: int,
    p1: float,
    p2: float,
    alpha: float = 0.05,
    alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
    ratio: float = 1.0,
) -> PowerAnalysisResult:
    """Calculate achieved power for comparing two proportions.

    Args:
        sample_size: Sample size per group
        p1: Proportion in group 1
        p2: Proportion in group 2
        alpha: Significance level (default: 0.05)
        alternative: Type of test ('two-sided', 'larger', 'smaller')
        ratio: Ratio of sample sizes (n2/n1, default: 1.0)

    Returns:
        PowerAnalysisResult with achieved power

    Example:
        >>> # Power to detect 50% vs 60% win rate with n=200
        >>> result = calculate_power_proportion(200, p1=0.5, p2=0.6)
        >>> result.power
        0.54  # Only 54% power - need more samples!
    """
    # Convert to effect size
    effect_size = 2 * (np.arcsin(np.sqrt(p2)) - np.arcsin(np.sqrt(p1)))

    power = zt_ind_solve_power(
        effect_size=abs(effect_size),
        nobs1=sample_size,
        alpha=alpha,
        ratio=ratio,
        alternative=alternative,
    )

    return PowerAnalysisResult(
        power=float(power),
        sample_size=sample_size,
        effect_size=effect_size,
        alpha=alpha,
        test_type="two-proportion z-test",
        notes=f"p1={p1:.3f}, p2={p2:.3f}; Cohen's h={effect_size:.3f}",
    )


def interpret_power(power: float) -> str:
    """Interpret power level.

    Args:
        power: Statistical power (0-1)

    Returns:
        Interpretation string

    Common thresholds:
        - 0.80: Conventional minimum (Cohen, 1988)
        - 0.90: High power (conservative studies)
        - 0.95: Very high power (critical decisions)
    """
    if power < 0.50:
        return "very low (< 50% chance of detecting effect)"
    elif power < 0.70:
        return "low (50-70% chance)"
    elif power < 0.80:
        return "moderate (70-80% chance)"
    elif power < 0.90:
        return "good (80-90% chance) - conventional"
    elif power < 0.95:
        return "high (90-95% chance) - conservative"
    else:
        return "very high (≥ 95% chance) - very conservative"
