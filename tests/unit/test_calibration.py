"""Tests for judge calibration metrics."""

import pytest

from codegen_bench.stats.calibration import (
    calculate_agreement,
    calculate_confusion_matrix,
    detect_position_bias,
    generate_calibration_report,
)


def test_perfect_agreement():
    """Test perfect agreement between judge and ground truth."""
    judge = ["A", "B", "A", "TIE", "B"]
    truth = ["A", "B", "A", "TIE", "B"]

    metrics = calculate_agreement(judge, truth)

    assert metrics.agreement_rate == 1.0
    assert metrics.fleiss_kappa == pytest.approx(1.0, abs=0.01)
    assert metrics.interpretation == "almost perfect"
    assert metrics.num_comparisons == 5


def test_no_agreement():
    """Test complete disagreement."""
    judge = ["A", "A", "A", "A"]
    truth = ["B", "B", "B", "B"]

    metrics = calculate_agreement(judge, truth)

    assert metrics.agreement_rate == 0.0
    assert metrics.fleiss_kappa < 0  # Worse than chance
    assert metrics.interpretation == "poor"


def test_partial_agreement():
    """Test partial agreement."""
    judge = ["A", "A", "B", "TIE", "A"]
    truth = ["A", "B", "B", "TIE", "A"]

    metrics = calculate_agreement(judge, truth)

    # Matches: indices 0 (A=A), 2 (B=B), 3 (TIE=TIE), 4 (A=A) = 4 out of 5
    assert metrics.agreement_rate == 0.8  # 4 out of 5
    assert 0 < metrics.fleiss_kappa < 1
    assert metrics.num_comparisons == 5


def test_agreement_empty_raises():
    """Test that empty lists raise error."""
    with pytest.raises(ValueError, match="at least one comparison"):
        calculate_agreement([], [])


def test_agreement_length_mismatch_raises():
    """Test that mismatched lengths raise error."""
    with pytest.raises(ValueError, match="same length"):
        calculate_agreement(["A", "B"], ["A"])


def test_position_bias_none():
    """Test no position bias (balanced judgments)."""
    judge = ["A", "B", "A", "B", "A", "B"]
    truth = ["A", "B", "A", "B", "A", "B"]

    bias = detect_position_bias(judge, truth)

    assert bias.position_bias == pytest.approx(0.0, abs=0.01)
    assert bias.position_bias_pvalue > 0.05
    assert not bias.has_significant_position_bias


def test_position_bias_toward_a():
    """Test significant bias toward position A."""
    # Judge heavily favors A
    judge = ["A"] * 9 + ["B"] * 1
    # Truth is balanced
    truth = ["A"] * 5 + ["B"] * 5

    bias = detect_position_bias(judge, truth)

    assert bias.position_bias > 0.5  # Strong A bias
    assert bias.has_significant_position_bias
    assert bias.position_bias_pvalue < 0.05


def test_position_bias_toward_b():
    """Test significant bias toward position B."""
    # Judge heavily favors B
    judge = ["B"] * 9 + ["A"] * 1
    # Truth is balanced
    truth = ["A"] * 5 + ["B"] * 5

    bias = detect_position_bias(judge, truth)

    assert bias.position_bias < -0.5  # Strong B bias
    assert bias.has_significant_position_bias


def test_position_bias_all_ties():
    """Test position bias when all comparisons are ties."""
    judge = ["TIE"] * 5
    truth = ["TIE"] * 5

    bias = detect_position_bias(judge, truth)

    assert bias.position_bias == 0.0
    assert not bias.has_significant_position_bias
    assert bias.length_correlation is None
    assert bias.has_significant_length_bias is None


def test_confusion_matrix_perfect():
    """Test confusion matrix with perfect predictions."""
    judge = ["A", "B", "A", "B"]
    truth = ["A", "B", "A", "B"]

    cm = calculate_confusion_matrix(judge, truth)

    assert cm.accuracy == 1.0
    assert cm.precision == 1.0
    assert cm.recall == 1.0
    assert cm.f1_score == 1.0
    assert cm.true_positives == 2
    assert cm.false_positives == 0
    assert cm.true_negatives == 2
    assert cm.false_negatives == 0


def test_confusion_matrix_mixed():
    """Test confusion matrix with mixed results."""
    judge = ["A", "A", "B", "B", "A"]
    truth = ["A", "B", "B", "A", "A"]

    cm = calculate_confusion_matrix(judge, truth)

    # TP: truth=A, judge=A -> indices 0, 4 = 2
    # FP: truth=B, judge=A -> index 1 = 1
    # TN: truth=B, judge=B -> index 2 = 1
    # FN: truth=A, judge=B -> index 3 = 1

    assert cm.true_positives == 2
    assert cm.false_positives == 1
    assert cm.true_negatives == 1
    assert cm.false_negatives == 1
    assert cm.accuracy == 0.6  # (2+1)/5


def test_confusion_matrix_all_ties():
    """Test confusion matrix when all are ties."""
    judge = ["TIE", "TIE", "TIE"]
    truth = ["TIE", "TIE", "TIE"]

    with pytest.raises(ValueError, match="Confusion matrix requires at least one A or B decision"):
        calculate_confusion_matrix(judge, truth)


def test_confusion_matrix_no_positives():
    """Test confusion matrix with no positive predictions."""
    judge = ["B", "B", "B"]
    truth = ["A", "A", "A"]

    cm = calculate_confusion_matrix(judge, truth)

    assert cm.true_positives == 0
    assert cm.false_negatives == 3
    assert cm.precision == 0.0  # No positive predictions
    assert cm.recall == 0.0  # Missed all positives


def test_confusion_matrix_no_negatives():
    """Test confusion matrix with no negative predictions."""
    judge = ["A", "A", "A"]
    truth = ["B", "B", "B"]

    cm = calculate_confusion_matrix(judge, truth)

    assert cm.false_positives == 3
    assert cm.true_negatives == 0
    assert cm.precision == 0.0  # All predictions wrong


def test_generate_calibration_report():
    """Test calibration report generation."""
    judge = ["A", "A", "B", "TIE", "A"]
    truth = ["A", "B", "B", "TIE", "A"]

    report = generate_calibration_report(judge, truth, "Test Judge")

    # Check report structure
    assert "Calibration Report: Test Judge" in report
    assert "Agreement Metrics:" in report
    assert "Bias Detection:" in report
    assert "Confusion Matrix:" in report
    assert "Recommendations:" in report


def test_generate_report_high_agreement():
    """Test report with high agreement."""
    # 90% agreement
    judge = ["A"] * 9 + ["B"]
    truth = ["A"] * 9 + ["A"]  # One disagreement

    report = generate_calibration_report(judge, truth)

    assert "Good agreement rate" in report or "agreement" in report.lower()


def test_generate_report_low_agreement():
    """Test report with low agreement."""
    # 40% agreement
    judge = ["A"] * 4 + ["B"] * 6
    truth = ["A"] * 6 + ["B"] * 4

    report = generate_calibration_report(judge, truth)

    assert "[WARNING]" in report  # Should have warnings


def test_generate_report_position_bias():
    """Test report detects position bias."""
    # Heavy position A bias
    judge = ["A"] * 18 + ["B"] * 2
    truth = ["A"] * 10 + ["B"] * 10

    report = generate_calibration_report(judge, truth)

    assert "position bias" in report.lower()


def test_fleiss_kappa_interpretation():
    """Test Fleiss' Kappa interpretation levels."""
    # High agreement with varied decisions
    judge = ["A", "A", "B", "B", "A", "A", "B", "B", "A", "A"]
    truth = ["A", "A", "B", "B", "A", "A", "B", "B", "A", "A"]

    metrics = calculate_agreement(judge, truth)
    assert metrics.agreement_rate == 1.0
    assert metrics.interpretation in ["substantial", "almost perfect"]


def test_fleiss_kappa_moderate():
    """Test moderate Kappa."""
    # Create moderate agreement scenario
    judge = ["A", "A", "B", "B", "A", "B", "A", "B", "A", "A"]
    truth = ["A", "B", "B", "A", "A", "B", "B", "B", "A", "A"]

    metrics = calculate_agreement(judge, truth)
    assert 0.2 < metrics.fleiss_kappa < 0.8


def test_agreement_metrics_string():
    """Test AgreementMetrics string representation."""
    judge = ["A", "A", "B"]
    truth = ["A", "B", "B"]

    metrics = calculate_agreement(judge, truth)
    s = str(metrics)

    assert "Agreement:" in s
    assert "Kappa:" in s
    assert "n=" in s


def test_bias_metrics_string():
    """Test BiasMetrics string representation."""
    judge = ["A"] * 8 + ["B"] * 2
    truth = ["A"] * 5 + ["B"] * 5

    bias = detect_position_bias(judge, truth)
    s = str(bias)

    assert "Position bias:" in s
    assert "WARNING" in s or "OK" in s  # Has indicator
    # Length bias not included when None


def test_confusion_matrix_string():
    """Test ConfusionMatrix string representation."""
    judge = ["A", "B", "A", "B"]
    truth = ["A", "B", "A", "B"]

    cm = calculate_confusion_matrix(judge, truth)
    s = str(cm)

    assert "Accuracy:" in s
    assert "Precision:" in s
    assert "Recall:" in s
    assert "F1:" in s


def test_confusion_matrix_f1_score():
    """Test F1 score calculation."""
    # Precision = 2/3, Recall = 2/3
    judge = ["A", "A", "A", "B"]
    truth = ["A", "A", "B", "B"]

    cm = calculate_confusion_matrix(judge, truth)

    # TP=2, FP=1, TN=1, FN=0
    assert cm.true_positives == 2
    assert cm.false_positives == 1
    assert cm.true_negatives == 1
    assert cm.false_negatives == 0

    expected_precision = 2 / 3
    expected_recall = 2 / 2  # All actual positives caught
    expected_f1 = 2 * expected_precision * expected_recall / (expected_precision + expected_recall)

    assert cm.precision == pytest.approx(expected_precision, abs=0.01)
    assert cm.f1_score == pytest.approx(expected_f1, abs=0.01)


def test_position_bias_length_mismatch_raises():
    """Test position bias with mismatched lengths."""
    with pytest.raises(ValueError, match="same length"):
        detect_position_bias(["A", "B"], ["A"])


def test_confusion_matrix_length_mismatch_raises():
    """Test confusion matrix with mismatched lengths."""
    with pytest.raises(ValueError, match="same length"):
        calculate_confusion_matrix(["A", "B"], ["A"])


def test_agreement_with_many_ties():
    """Test agreement calculation with many ties."""
    judge = ["TIE"] * 5 + ["A", "B"]
    truth = ["TIE"] * 5 + ["A", "B"]

    metrics = calculate_agreement(judge, truth)

    assert metrics.agreement_rate == 1.0  # All match
    assert metrics.num_comparisons == 7


def test_calibration_metrics_dataclass_fields():
    """Test that dataclass fields are accessible."""
    judge = ["A", "B"]
    truth = ["A", "B"]

    metrics = calculate_agreement(judge, truth)

    # Access all fields
    assert hasattr(metrics, "agreement_rate")
    assert hasattr(metrics, "fleiss_kappa")
    assert hasattr(metrics, "interpretation")
    assert hasattr(metrics, "num_comparisons")
    assert hasattr(metrics, "num_judges")


def test_bias_metrics_fields():
    """Test BiasMetrics fields are accessible."""
    judge = ["A", "B"]
    truth = ["A", "B"]

    bias = detect_position_bias(judge, truth)

    assert hasattr(bias, "position_bias")
    assert hasattr(bias, "position_bias_pvalue")
    assert hasattr(bias, "length_correlation")
    assert hasattr(bias, "has_significant_position_bias")
    assert hasattr(bias, "has_significant_length_bias")
