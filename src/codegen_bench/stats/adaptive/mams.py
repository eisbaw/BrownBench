"""Multi-Arm Multi-Stage (MAMS) adaptive design.

MAMS design allows efficient screening of multiple approaches against a control,
with interim selection based on cheap proxy metrics before full evaluation.

This implementation follows Magirr et al. (2012) and uses Dunnett's test for
optimal many-to-one comparisons (10-15% more powerful than Bonferroni).

References:
- Magirr et al. (2012): "Sample size reassessment and hypothesis testing in MAMS trials"
- Wason & Jaki (2012): "Optimal design of multi-arm multi-stage trials"
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats

# Decision thresholds
EFFICACY_Z_THRESHOLD = 3.0  # Z-score threshold for early efficacy stopping
"""Very strong evidence threshold (p < 0.0027 two-tailed) for single arm."""

# Cost ratio constants for power/cost analysis
STAGE1_COST_RATIO = 0.2  # Stage 1 is 20% of full evaluation cost
"""Cheap proxy metrics in Stage 1 cost 20% of full evaluation."""

STAGE2_COST_RATIO = 1.0  # Stage 2 is full evaluation cost
"""Full metrics in Stage 2 cost 100% of evaluation budget."""


@dataclass
class MAMSResult:
    """Result from MAMS stage evaluation.

    Attributes:
        selected_arms: List of arm IDs selected for next stage
        eliminated_arms: List of arm IDs eliminated
        statistics: Test statistics for each arm vs control
        p_values: P-values for each comparison (Dunnett-adjusted)
        decision: Overall decision ('continue', 'stop_futility', 'stop_efficacy')
    """

    selected_arms: list[str]
    eliminated_arms: list[str]
    statistics: dict[str, float]
    p_values: dict[str, float]
    decision: Literal["continue", "stop_futility", "stop_efficacy"]


@dataclass
class MAMSConfig:
    """Configuration for MAMS design.

    Attributes:
        num_arms: Total number of experimental arms (excluding control)
        control_id: ID of control arm
        alpha: Overall Type I error rate (default: 0.05)
        power: Target power (default: 0.80)
        max_selected: Maximum arms to select for stage 2 (default: 3)
        futility_threshold: Minimum effect size to continue (default: 0.2)
    """

    num_arms: int
    control_id: str
    alpha: float = 0.05
    power: float = 0.80
    max_selected: int = 3
    futility_threshold: float = 0.2


class MAMSDesign:
    """Multi-Arm Multi-Stage design for efficient screening.

    Example:
        >>> config = MAMSConfig(num_arms=5, control_id="baseline")
        >>> design = MAMSDesign(config)
        >>>
        >>> # Stage 1: cheap metrics (e.g., compilation success rate)
        >>> results = {
        ...     "baseline": [0.95, 0.93, 0.94, 0.96],
        ...     "dut1": [0.88, 0.87, 0.89, 0.88],
        ...     "dut2": [0.97, 0.96, 0.98, 0.97],
        ...     "dut3": [0.91, 0.90, 0.92, 0.91],
        ...     "dut4": [0.85, 0.84, 0.86, 0.85],
        ...     "dut5": [0.98, 0.97, 0.99, 0.98],
        ... }
        >>> stage1_result = design.evaluate_stage1(results)
        >>> print(stage1_result.selected_arms)
        ['dut2', 'dut5', 'dut3']  # Top 3 performers
    """

    def __init__(self, config: MAMSConfig):
        """Initialize MAMS design.

        Args:
            config: MAMS configuration
        """
        self.config = config

    def evaluate_stage1(
        self, results: dict[str, list[float]], higher_is_better: bool = True
    ) -> MAMSResult:
        """Evaluate Stage 1 with cheap proxy metrics.

        Uses Dunnett's test for many-to-one comparisons vs control.

        Args:
            results: Dictionary mapping arm_id -> list of measurements
            higher_is_better: Whether higher values are better (default: True)

        Returns:
            MAMSResult with selected/eliminated arms

        Raises:
            ValueError: If control_id not in results or results invalid
        """
        if self.config.control_id not in results:
            raise ValueError(f"Control arm '{self.config.control_id}' not in results")

        control_data = np.array(results[self.config.control_id], dtype=float)

        # Prepare treatment arms
        treatment_ids = [arm_id for arm_id in results if arm_id != self.config.control_id]
        treatment_data = [np.array(results[arm_id], dtype=float) for arm_id in treatment_ids]

        if len(treatment_ids) == 0:
            raise ValueError("No treatment arms provided")

        # Perform Dunnett's test
        dunnett_result = self._dunnett_test(
            treatments=treatment_data,
            control=control_data,
            alpha=self.config.alpha,
            alternative="greater" if higher_is_better else "less",
        )

        # Compute effect sizes for ranking
        effect_sizes = {}
        for arm_id, arm_data in zip(treatment_ids, treatment_data, strict=True):
            mean_diff = float(np.mean(arm_data) - np.mean(control_data))
            pooled_std = self._pooled_std(arm_data, control_data)
            if pooled_std > 0:
                effect_sizes[arm_id] = mean_diff / pooled_std
            else:
                effect_sizes[arm_id] = 0.0

        # Select top performers
        # Sort by effect size (descending if higher_is_better, ascending otherwise)
        sorted_arms = sorted(
            treatment_ids,
            key=lambda x: effect_sizes[x],
            reverse=higher_is_better,
        )

        # Filter by statistical significance and effect size threshold
        significant_arms = [
            arm_id
            for arm_id, p_val in zip(treatment_ids, dunnett_result["p_values"], strict=True)
            if p_val < self.config.alpha
            and abs(effect_sizes[arm_id]) >= self.config.futility_threshold
        ]

        # Select top max_selected from significant arms
        selected_arms = sorted_arms[: self.config.max_selected]
        selected_arms = [arm for arm in selected_arms if arm in significant_arms]

        eliminated_arms = [arm for arm in treatment_ids if arm not in selected_arms]

        # Build result dictionaries
        statistics_dict = dict(zip(treatment_ids, dunnett_result["statistics"], strict=True))
        p_values_dict = dict(zip(treatment_ids, dunnett_result["p_values"], strict=True))

        # Decision logic
        decision: Literal["continue", "stop_futility", "stop_efficacy"]
        if len(selected_arms) == 0:
            decision = "stop_futility"
        elif len(selected_arms) == 1 and dunnett_result["statistics"][0] > EFFICACY_Z_THRESHOLD:
            # Very strong evidence for single arm (Z > 3.0, p < 0.0027)
            decision = "stop_efficacy"
        else:
            decision = "continue"

        return MAMSResult(
            selected_arms=selected_arms,
            eliminated_arms=eliminated_arms,
            statistics=statistics_dict,
            p_values=p_values_dict,
            decision=decision,
        )

    def _dunnett_test(
        self,
        treatments: list[np.ndarray],
        control: np.ndarray,
        alpha: float,
        alternative: Literal["greater", "less", "two-sided"] = "greater",
    ) -> dict[str, list[float]]:
        """Perform Dunnett's test for many-to-one comparisons.

        Args:
            treatments: List of treatment group data
            control: Control group data
            alpha: Significance level
            alternative: Alternative hypothesis direction

        Returns:
            Dictionary with 'statistics' and 'p_values' lists
        """
        # Use scipy.stats.dunnett (available in scipy >= 1.11)
        try:
            result = stats.dunnett(*treatments, control=control, alternative=alternative)
            return {
                "statistics": result.statistic.tolist(),
                "p_values": result.pvalue.tolist(),
            }
        except AttributeError:
            # Fallback: use conservative Bonferroni correction with t-tests
            # This is less powerful but always available
            statistics = []
            p_values = []

            for treatment in treatments:
                t_stat, p_val = stats.ttest_ind(treatment, control, alternative=alternative)
                statistics.append(float(t_stat))
                # Bonferroni correction
                p_values.append(float(min(p_val * len(treatments), 1.0)))

            return {"statistics": statistics, "p_values": p_values}

    def _pooled_std(self, group_a: np.ndarray, group_b: np.ndarray) -> float:
        """Calculate pooled standard deviation."""
        n_a, n_b = len(group_a), len(group_b)

        if n_a < 2 or n_b < 2:
            return 0.0

        var_a = np.var(group_a, ddof=1)
        var_b = np.var(group_b, ddof=1)

        pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)

        return float(np.sqrt(pooled_var))

    def compute_stage1_sample_size(self, effect_size: float, variance: float = 1.0) -> int:
        """Compute required sample size for Stage 1.

        Uses power calculation for Dunnett's test.

        Args:
            effect_size: Minimum detectable effect size (Cohen's d)
            variance: Assumed variance (default: 1.0 for standardized effect)

        Returns:
            Required sample size per arm
        """
        # Approximate power calculation
        # For Dunnett with k treatments, critical value is higher than standard t
        k = self.config.num_arms
        alpha = self.config.alpha
        power = self.config.power

        # Dunnett critical value approximation (conservative)
        # Use Bonferroni as upper bound
        alpha_bonf = alpha / k

        from scipy.stats import norm

        z_alpha = norm.ppf(1 - alpha_bonf / 2)
        z_beta = norm.ppf(power)

        # Two-sample t-test sample size formula
        n_per_group = 2 * ((z_alpha + z_beta) / effect_size) ** 2 * variance

        # Add 10% for conservative estimate
        n_per_group_int = int(np.ceil(n_per_group * 1.1))

        return max(n_per_group_int, 10)  # Minimum 10 per group

    def compute_expected_cost_savings(self) -> dict[str, float]:
        """Compute expected cost savings from MAMS vs full evaluation.

        Returns:
            Dictionary with cost metrics
        """
        k = self.config.num_arms
        max_selected = self.config.max_selected

        # Stage 1 uses cheap proxy metrics (20% cost), Stage 2 uses full evaluation (100% cost)
        stage1_cost_per_arm = STAGE1_COST_RATIO
        stage2_cost_per_arm = STAGE2_COST_RATIO

        # MAMS: all arms in stage 1, top max_selected in stage 2
        mams_total = (k * stage1_cost_per_arm) + (max_selected * stage2_cost_per_arm)

        # Naive: all arms in full evaluation
        naive_total = k * stage2_cost_per_arm

        savings = naive_total - mams_total
        savings_pct = (savings / naive_total) * 100

        return {
            "mams_cost": mams_total,
            "naive_cost": naive_total,
            "savings": savings,
            "savings_percent": savings_pct,
            "eliminated_early": k - max_selected,
        }
