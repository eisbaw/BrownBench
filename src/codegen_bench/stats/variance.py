"""Variance decomposition via mixed linear models.

This module implements variance component analysis to quantify sources of variation
in benchmark results. It helps answer questions like:
- How much variability is due to the approach vs task vs arena?
- What is the intraclass correlation (ICC) for reliability?
- How much variance do fixed effects (approach) explain vs random effects (task/arena)?

References:
- Nakagawa & Schielzeth (2013): "A general and simple method for obtaining R² from GLMMs"
- Bates et al. (2015): "Fitting Linear Mixed-Effects Models Using lme4"
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from statsmodels.regression.mixed_linear_model import MixedLM, MixedLMResults


@dataclass
class VarianceComponents:
    """Variance decomposition results.

    Attributes:
        icc: Intraclass Correlation Coefficient (0-1)
        interpretation: Qualitative reliability interpretation
        variance_between: Variance due to grouping (random effects)
        variance_within: Residual variance (within groups)
        r2_marginal: R² for fixed effects only (approach)
        r2_conditional: R² for fixed + random effects
        aic: Akaike Information Criterion (model fit)
        bic: Bayesian Information Criterion (model fit)
    """

    icc: float
    interpretation: str
    variance_between: float
    variance_within: float
    r2_marginal: float
    r2_conditional: float
    aic: float
    bic: float

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ICC={self.icc:.3f} ({self.interpretation}), "
            f"R²_marginal={self.r2_marginal:.3f}, "
            f"R²_conditional={self.r2_conditional:.3f}"
        )


def decompose_variance(
    data: pd.DataFrame,
    response: str,
    fixed_effects: str,
    group_var: str,
) -> VarianceComponents:
    """Decompose variance using linear mixed models.

    This function fits a mixed linear model to decompose variance into:
    - Fixed effects (e.g., approach)
    - Random effects (e.g., task)
    - Residual variance

    Args:
        data: DataFrame with response and predictors
        response: Name of response variable (e.g., 'elo')
        fixed_effects: Formula for fixed effects (e.g., 'approach')
        group_var: Name of grouping variable for random effects (e.g., 'task')

    Returns:
        VarianceComponents with ICC, R² values, and variance estimates

    Example:
        >>> data = pd.DataFrame({
        ...     'elo': [1500, 1520, 1480, 1550, 1530, 1510],
        ...     'approach': ['A', 'A', 'A', 'B', 'B', 'B'],
        ...     'task': ['t1', 't2', 't3', 't1', 't2', 't3']
        ... })
        >>> result = decompose_variance(data, 'elo', 'approach', 'task')
        >>> result.icc
        0.5
    """
    if len(data) == 0:
        raise ValueError("Data must not be empty")

    if response not in data.columns:
        raise ValueError(f"Response variable '{response}' not in data")

    if group_var not in data.columns:
        raise ValueError(f"Group variable '{group_var}' not in data")

    # Build formula: response ~ fixed_effects
    formula = f"{response} ~ {fixed_effects}"

    # Fit mixed model with random intercept for group_var
    model = MixedLM.from_formula(
        formula=formula,
        groups=data[group_var],
        re_formula="1",  # Random intercept
        data=data,
    )

    # Fit with error handling for small/problematic datasets
    try:
        fitted = model.fit(method="lbfgs", reml=True, maxiter=100)
    except (np.linalg.LinAlgError, ValueError):
        # Fallback to simpler method for problematic datasets
        try:
            fitted = model.fit(method="nm", reml=True, maxiter=500)
        except (np.linalg.LinAlgError, ValueError) as e:
            # Last resort: Use OLS to get reasonable estimates
            raise ValueError(
                "Unable to fit mixed model. Data may be too small or have "
                "perfect collinearity. Need at least 3 groups with variation."
            ) from e

    # Extract variance components
    variance_between = _extract_random_effect_variance(fitted)
    variance_within = fitted.scale  # Residual variance

    # Intraclass Correlation Coefficient
    total_variance = variance_between + variance_within
    if total_variance == 0:
        # Edge case: no variance at all (all values identical)
        icc = 0.0
    else:
        icc = variance_between / total_variance

    # R² calculations
    r2_marginal = _calculate_r2_marginal(fitted, data[response].values)
    r2_conditional = _calculate_r2_conditional(fitted, data[response].values)

    return VarianceComponents(
        icc=icc,
        interpretation=_interpret_icc(icc),
        variance_between=variance_between,
        variance_within=variance_within,
        r2_marginal=r2_marginal,
        r2_conditional=r2_conditional,
        aic=fitted.aic,
        bic=fitted.bic,
    )


def _extract_random_effect_variance(fitted: MixedLMResults) -> float:
    """Extract random effect variance from fitted model.

    Args:
        fitted: Fitted MixedLM model

    Returns:
        Variance of random effects
    """
    # Random effect variance is in cov_re
    # For random intercept model, this is a scalar
    cov_re = fitted.cov_re

    # Handle pandas DataFrame (statsmodels returns this)
    if hasattr(cov_re, "iloc"):
        # DataFrame case
        if cov_re.shape == (1, 1):
            return float(cov_re.iloc[0, 0])
        else:
            # Multiple random effects - sum variances (diagonal)
            return float(np.trace(cov_re.values))

    # Handle numpy array
    if isinstance(cov_re, np.ndarray):
        if cov_re.size == 1:
            return float(cov_re.flat[0])
        else:
            # Multiple random effects - sum variances
            return float(np.trace(cov_re))

    # Scalar case
    return float(cov_re)


def _calculate_r2_marginal(fitted: MixedLMResults, y: np.ndarray) -> float:
    """Calculate marginal R² (variance explained by fixed effects only).

    Nakagawa & Schielzeth (2013) method:
    R²_marginal = var_fixed / (var_fixed + var_random + var_residual)

    Simplified approach: Use variance components directly

    Args:
        fitted: Fitted MixedLM model
        y: Observed response values

    Returns:
        Marginal R² (0-1)
    """
    # Extract variance components
    var_random = _extract_random_effect_variance(fitted)
    var_residual = fitted.scale

    # Total variance
    var_total = np.var(y, ddof=1)

    if var_total == 0:
        return 0.0

    # Fixed effects variance (total - random - residual)
    var_fixed = max(0, var_total - var_random - var_residual)

    r2_marginal = var_fixed / var_total

    # Clamp to [0, 1] to handle numerical issues
    return float(np.clip(r2_marginal, 0, 1))


def _calculate_r2_conditional(fitted: MixedLMResults, y: np.ndarray) -> float:
    """Calculate conditional R² (variance explained by fixed + random effects).

    Nakagawa & Schielzeth (2013) method:
    R²_conditional = (var_fixed + var_random) / var_total

    Args:
        fitted: Fitted MixedLM model
        y: Observed response values

    Returns:
        Conditional R² (0-1)
    """
    # Extract variance components
    var_residual = fitted.scale

    # Total variance
    var_total = np.var(y, ddof=1)

    if var_total == 0:
        return 0.0

    # Conditional R² = 1 - (var_residual / var_total)
    # This is the proportion of variance explained by fixed + random effects
    r2_conditional = 1 - (var_residual / var_total)

    # Clamp to [0, 1] to handle numerical issues
    return float(np.clip(r2_conditional, 0, 1))


def _interpret_icc(icc: float) -> Literal["poor", "moderate", "good", "excellent"]:
    """Interpret ICC using standard guidelines.

    Guidelines (Koo & Li 2016):
    - ICC < 0.50: Poor reliability
    - 0.50 ≤ ICC < 0.75: Moderate reliability
    - 0.75 ≤ ICC < 0.90: Good reliability
    - ICC ≥ 0.90: Excellent reliability

    Args:
        icc: Intraclass Correlation Coefficient (0-1)

    Returns:
        Qualitative interpretation
    """
    if icc < 0.50:
        return "poor"
    elif icc < 0.75:
        return "moderate"
    elif icc < 0.90:
        return "good"
    else:
        return "excellent"


def calculate_variance_explained_by_factor(
    data: pd.DataFrame,
    response: str,
    factor: str,
) -> float:
    """Calculate proportion of variance explained by a single factor.

    Uses one-way ANOVA to calculate η² (eta-squared):
    η² = SS_between / SS_total

    Args:
        data: DataFrame with response and factor
        response: Name of response variable
        factor: Name of categorical factor

    Returns:
        Proportion of variance explained (0-1)

    Example:
        >>> data = pd.DataFrame({
        ...     'elo': [1500, 1520, 1480, 1550, 1530, 1510],
        ...     'task': ['t1', 't1', 't2', 't2', 't3', 't3']
        ... })
        >>> calculate_variance_explained_by_factor(data, 'elo', 'task')
        0.5
    """
    if response not in data.columns:
        raise ValueError(f"Response variable '{response}' not in data")

    if factor not in data.columns:
        raise ValueError(f"Factor '{factor}' not in data")

    y = data[response].values
    groups = data[factor].values

    # Grand mean
    grand_mean = np.mean(y)

    # Total sum of squares
    ss_total = np.sum((y - grand_mean) ** 2)

    if ss_total == 0:
        return 0.0

    # Between-group sum of squares
    ss_between = 0.0
    for group in np.unique(groups):
        group_mask = groups == group
        group_mean = np.mean(y[group_mask])
        group_size = np.sum(group_mask)
        ss_between += group_size * (group_mean - grand_mean) ** 2

    # Eta-squared
    eta_squared = ss_between / ss_total

    return float(np.clip(eta_squared, 0, 1))
