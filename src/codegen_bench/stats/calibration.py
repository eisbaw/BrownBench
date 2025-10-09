"""Judge calibration and bias detection metrics.

This module provides metrics for evaluating LLM judge performance against
human ground truth, including inter-rater reliability, bias detection,
and calibration analysis.

Key metrics:
- Agreement rate: Simple percentage of matching judgments
- Fleiss' Kappa: Inter-rater reliability accounting for chance agreement
- Position bias: Tendency to favor position A or B
- Length bias: Correlation between judgment and solution length
- Confusion matrix: Judge accuracy breakdown

References:
- Fleiss (1971): "Measuring nominal scale agreement among many raters"
- Landis & Koch (1977): "The measurement of observer agreement for categorical data"
- Cohen (1960): "A coefficient of agreement for nominal scales"
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats

JudgeDecision = Literal["A", "B", "TIE"]


@dataclass
class AgreementMetrics:
    """Agreement and reliability metrics.

    Attributes:
        agreement_rate: Simple agreement percentage (0-1)
        fleiss_kappa: Inter-rater reliability (-1 to 1)
        interpretation: Qualitative interpretation of kappa
        num_comparisons: Number of comparison pairs evaluated
        num_judges: Number of judges (including ground truth)
    """

    agreement_rate: float
    fleiss_kappa: float
    interpretation: str
    num_comparisons: int
    num_judges: int

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Agreement: {self.agreement_rate:.1%}, "
            f"Kappa: {self.fleiss_kappa:.3f} ({self.interpretation}), "
            f"n={self.num_comparisons}"
        )


@dataclass
class BiasMetrics:
    """Judge bias detection metrics.

    Attributes:
        position_bias: Difference in P(A) - P(B) relative to ground truth distribution
        position_bias_pvalue: Statistical significance of position bias
        length_correlation: Correlation between length difference and judgment (None if not calculated)
        length_correlation_pvalue: Statistical significance of length bias (None if not calculated)
        has_significant_position_bias: Whether position bias is significant (p < 0.05)
        has_significant_length_bias: Whether length bias is significant (None if not calculated)
    """

    position_bias: float
    position_bias_pvalue: float
    length_correlation: float | None
    length_correlation_pvalue: float | None
    has_significant_position_bias: bool
    has_significant_length_bias: bool | None

    def __str__(self) -> str:
        """String representation."""
        pos_flag = "WARNING" if self.has_significant_position_bias else "OK"

        if self.length_correlation is not None and self.has_significant_length_bias is not None:
            len_flag = "WARNING" if self.has_significant_length_bias else "OK"
            return (
                f"[{pos_flag}] Position bias: {self.position_bias:+.3f} (p={self.position_bias_pvalue:.3f}), "
                f"[{len_flag}] Length bias: r={self.length_correlation:+.3f} (p={self.length_correlation_pvalue:.3f})"
            )
        else:
            return f"[{pos_flag}] Position bias: {self.position_bias:+.3f} (p={self.position_bias_pvalue:.3f})"


@dataclass
class ConfusionMatrix:
    """Confusion matrix for judge accuracy.

    Attributes:
        true_positives: Correct A judgments
        false_positives: Incorrect A judgments (actually B)
        true_negatives: Correct B judgments
        false_negatives: Incorrect B judgments (actually A)
        accuracy: Overall accuracy (TP + TN) / Total
        precision: TP / (TP + FP)
        recall: TP / (TP + FN)
        f1_score: Harmonic mean of precision and recall
    """

    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Accuracy: {self.accuracy:.1%}, "
            f"Precision: {self.precision:.1%}, "
            f"Recall: {self.recall:.1%}, "
            f"F1: {self.f1_score:.3f}"
        )


def calculate_agreement(
    judge_decisions: list[JudgeDecision],
    ground_truth: list[JudgeDecision],
) -> AgreementMetrics:
    """Calculate agreement rate and Fleiss' Kappa.

    Args:
        judge_decisions: List of judge decisions
        ground_truth: List of ground truth decisions

    Returns:
        AgreementMetrics with agreement rate and Fleiss' Kappa

    Example:
        >>> judge = ["A", "A", "B", "TIE", "A"]
        >>> truth = ["A", "B", "B", "TIE", "A"]
        >>> metrics = calculate_agreement(judge, truth)
        >>> metrics.agreement_rate
        0.6  # 3 out of 5 correct
    """
    if len(judge_decisions) != len(ground_truth):
        raise ValueError("Judge decisions and ground truth must have same length")

    if len(judge_decisions) == 0:
        raise ValueError("Must have at least one comparison")

    judge_arr = np.array(judge_decisions)
    truth_arr = np.array(ground_truth)

    # Simple agreement rate
    agreement_rate = float(np.mean(judge_arr == truth_arr))

    # Fleiss' Kappa for 2 raters (judge + ground truth)
    # For 2 raters, this is equivalent to Cohen's Kappa
    n = len(judge_decisions)

    # Build rating matrix (n_items x n_categories)
    categories = ["A", "B", "TIE"]
    matrix = np.zeros((n, len(categories)))

    for i in range(n):
        for j, cat in enumerate(categories):
            # Count how many raters (out of 2) chose this category
            count = 0
            if judge_arr[i] == cat:
                count += 1
            if truth_arr[i] == cat:
                count += 1
            matrix[i, j] = count

    fleiss_kappa = _fleiss_kappa(matrix)

    return AgreementMetrics(
        agreement_rate=agreement_rate,
        fleiss_kappa=fleiss_kappa,
        interpretation=_interpret_kappa(fleiss_kappa),
        num_comparisons=n,
        num_judges=2,
    )


def _fleiss_kappa(matrix: np.ndarray) -> float:
    """Calculate Fleiss' Kappa from rating matrix.

    Args:
        matrix: Rating matrix (n_items x n_categories)
            Each cell contains count of raters who chose that category

    Returns:
        Fleiss' Kappa coefficient (-1 to 1)
    """
    n_items, n_categories = matrix.shape
    n_raters = int(matrix[0].sum())  # Total raters per item

    # Proportion of all assignments in each category
    p_j = matrix.sum(axis=0) / (n_items * n_raters)

    # Extent of agreement for each item
    P_i = (np.sum(matrix**2, axis=1) - n_raters) / (n_raters * (n_raters - 1))

    # Mean agreement across items
    P_bar = P_i.mean()

    # Expected agreement by chance
    P_e = (p_j**2).sum()

    # Fleiss' Kappa
    if P_e == 1.0:
        # Perfect agreement by chance (all same category)
        return 1.0 if P_bar == 1.0 else 0.0

    kappa = (P_bar - P_e) / (1 - P_e)
    return float(kappa)


def _interpret_kappa(kappa: float) -> str:
    """Interpret Fleiss' Kappa using Landis & Koch guidelines.

    Args:
        kappa: Kappa coefficient

    Returns:
        Qualitative interpretation
    """
    if kappa < 0:
        return "poor"
    elif kappa < 0.20:
        return "slight"
    elif kappa < 0.40:
        return "fair"
    elif kappa < 0.60:
        return "moderate"
    elif kappa < 0.80:
        return "substantial"
    else:
        return "almost perfect"


def detect_position_bias(
    judge_decisions: list[JudgeDecision],
    ground_truth: list[JudgeDecision],
) -> BiasMetrics:
    """Detect position bias (favoring A or B position).

    Position bias occurs when a judge systematically favors the first or
    second position, independent of actual quality. This test compares the
    judge's A/B distribution against the ground truth distribution.

    Args:
        judge_decisions: List of judge decisions
        ground_truth: List of ground truth decisions

    Returns:
        BiasMetrics with position bias indicators (length bias not implemented)

    Example:
        >>> judge = ["A"] * 8 + ["B"] * 2  # Heavy A bias
        >>> truth = ["A"] * 5 + ["B"] * 5  # Actually balanced
        >>> bias = detect_position_bias(judge, truth)
        >>> bias.has_significant_position_bias
        True  # Judge favors position A relative to ground truth
    """
    if len(judge_decisions) != len(ground_truth):
        raise ValueError("Judge decisions and ground truth must have same length")

    judge_arr = np.array(judge_decisions)
    truth_arr = np.array(ground_truth)

    # Filter to non-tie cases for position bias
    non_tie_mask = truth_arr != "TIE"
    judge_non_tie = judge_arr[non_tie_mask]
    truth_non_tie = truth_arr[non_tie_mask]

    if len(judge_non_tie) == 0:
        # All ties, no position bias measurable
        return BiasMetrics(
            position_bias=0.0,
            position_bias_pvalue=1.0,
            length_correlation=None,
            length_correlation_pvalue=None,
            has_significant_position_bias=False,
            has_significant_length_bias=None,
        )

    # Calculate judge's A/B distribution
    n_judge_a = (judge_non_tie == "A").sum()
    n_judge_b = (judge_non_tie == "B").sum()
    n_total = len(judge_non_tie)

    # Calculate ground truth's A/B distribution
    n_truth_a = (truth_non_tie == "A").sum()
    p_truth_a = n_truth_a / len(truth_non_tie)

    # Position bias: difference from ground truth distribution
    position_bias = (n_judge_a - n_judge_b) / n_total

    # Test if judge's A rate differs from ground truth A rate
    # Binomial test: H0: p = p_truth_a
    binom_test_result = stats.binomtest(n_judge_a, n_total, p=p_truth_a, alternative="two-sided")
    position_bias_pvalue = float(binom_test_result.pvalue)

    # Length bias not implemented - would require solution length data
    return BiasMetrics(
        position_bias=position_bias,
        position_bias_pvalue=position_bias_pvalue,
        length_correlation=None,
        length_correlation_pvalue=None,
        has_significant_position_bias=position_bias_pvalue < 0.05,
        has_significant_length_bias=None,
    )


def calculate_confusion_matrix(
    judge_decisions: list[JudgeDecision],
    ground_truth: list[JudgeDecision],
) -> ConfusionMatrix:
    """Calculate confusion matrix for judge accuracy.

    Treats "A" as positive class, "B" as negative class.
    Ties are excluded from precision/recall calculations.

    Args:
        judge_decisions: List of judge decisions
        ground_truth: List of ground truth decisions

    Returns:
        ConfusionMatrix with accuracy metrics

    Example:
        >>> judge = ["A", "A", "B", "B", "A"]
        >>> truth = ["A", "B", "B", "A", "A"]
        >>> cm = calculate_confusion_matrix(judge, truth)
        >>> cm.accuracy
        0.6  # 3 correct out of 5
    """
    if len(judge_decisions) != len(ground_truth):
        raise ValueError("Judge decisions and ground truth must have same length")

    judge_arr = np.array(judge_decisions)
    truth_arr = np.array(ground_truth)

    # Filter to non-tie cases
    non_tie_mask = (judge_arr != "TIE") & (truth_arr != "TIE")
    judge_filtered = judge_arr[non_tie_mask]
    truth_filtered = truth_arr[non_tie_mask]

    if len(judge_filtered) == 0:
        # All ties - confusion matrix requires A/B decisions
        raise ValueError(
            "Confusion matrix requires at least one A or B decision. "
            "All comparisons were TIE, which cannot be classified as TP/FP/TN/FN."
        )

    # Calculate confusion matrix
    # Positive class: A, Negative class: B
    tp = int(((judge_filtered == "A") & (truth_filtered == "A")).sum())
    fp = int(((judge_filtered == "A") & (truth_filtered == "B")).sum())
    tn = int(((judge_filtered == "B") & (truth_filtered == "B")).sum())
    fn = int(((judge_filtered == "B") & (truth_filtered == "A")).sum())

    # Calculate metrics
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total > 0 else 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return ConfusionMatrix(
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
    )


def generate_calibration_report(
    judge_decisions: list[JudgeDecision],
    ground_truth: list[JudgeDecision],
    judge_name: str = "LLM Judge",
) -> str:
    """Generate comprehensive calibration report.

    Args:
        judge_decisions: List of judge decisions
        ground_truth: List of ground truth decisions
        judge_name: Name of judge for report

    Returns:
        Formatted calibration report string

    Example:
        >>> judge = ["A", "A", "B", "TIE", "A"]
        >>> truth = ["A", "B", "B", "TIE", "A"]
        >>> report = generate_calibration_report(judge, truth, "Claude Judge")
        >>> print(report)
        Calibration Report: Claude Judge
        ================================
        Agreement: 60.0%, Kappa: 0.XXX (moderate)
        ...
    """
    agreement = calculate_agreement(judge_decisions, ground_truth)
    bias = detect_position_bias(judge_decisions, ground_truth)
    confusion = calculate_confusion_matrix(judge_decisions, ground_truth)

    report_lines = [
        f"Calibration Report: {judge_name}",
        "=" * (len(judge_name) + 21),
        "",
        "Agreement Metrics:",
        f"  {agreement}",
        "",
        "Bias Detection:",
        f"  {bias}",
        "",
        "Confusion Matrix:",
        f"  {confusion}",
        f"  TP={confusion.true_positives}, FP={confusion.false_positives}, "
        f"TN={confusion.true_negatives}, FN={confusion.false_negatives}",
        "",
        "Recommendations:",
    ]

    # Add recommendations based on metrics
    if agreement.agreement_rate < 0.70:
        report_lines.append("  [WARNING] Low agreement rate (<70%). Consider revising prompts.")
    elif agreement.agreement_rate < 0.85:
        report_lines.append(
            "  [WARNING] Moderate agreement (70-85%). Some prompt refinement may help."
        )
    else:
        report_lines.append("  [OK] Good agreement rate (≥85%).")

    if bias.has_significant_position_bias:
        report_lines.append(
            "  [WARNING] Significant position bias detected. Review prompt neutrality."
        )

    if agreement.fleiss_kappa < 0.40:
        report_lines.append(
            "  [WARNING] Low inter-rater reliability (κ<0.40). Poor agreement beyond chance."
        )

    return "\n".join(report_lines)
