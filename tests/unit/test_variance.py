"""Tests for variance decomposition module."""

import numpy as np
import pandas as pd
import pytest

from codegen_bench.stats.variance import (
    VarianceComponents,
    calculate_variance_explained_by_factor,
    decompose_variance,
)


class TestDecomposeVariance:
    """Tests for decompose_variance function."""

    def test_simple_mixed_model(self):
        """Test basic mixed model variance decomposition."""
        # Create data with clear grouping structure
        data = pd.DataFrame(
            {
                "elo": [1500, 1520, 1480, 1550, 1530, 1510, 1600, 1580, 1620],
                "approach": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
                "task": ["t1", "t2", "t3", "t1", "t2", "t3", "t1", "t2", "t3"],
            }
        )

        result = decompose_variance(data, "elo", "approach", "task")

        # Check result type
        assert isinstance(result, VarianceComponents)

        # Check ICC is in valid range
        assert 0 <= result.icc <= 1

        # Check variance components are non-negative
        assert result.variance_between >= 0
        assert result.variance_within >= 0

        # Check R² values are in valid range
        assert 0 <= result.r2_marginal <= 1
        assert 0 <= result.r2_conditional <= 1

        # Conditional R² should be >= marginal R²
        assert result.r2_conditional >= result.r2_marginal - 0.01  # Allow small numerical error

        # Check interpretation is valid
        assert result.interpretation in ["poor", "moderate", "good", "excellent"]

    def test_high_between_group_variance(self):
        """Test case with high between-group variance (high ICC)."""
        # Create data where tasks are very different
        data = pd.DataFrame(
            {
                "elo": ([1500] * 3 + [1700] * 3 + [1900] * 3),  # Tasks differ a lot
                "approach": ["A", "B", "C"] * 3,
                "task": ["t1", "t1", "t1", "t2", "t2", "t2", "t3", "t3", "t3"],
            }
        )

        result = decompose_variance(data, "elo", "approach", "task")

        # High ICC expected (most variance is between tasks)
        assert result.icc > 0.5
        assert result.variance_between > result.variance_within

    def test_low_between_group_variance(self):
        """Test case with low between-group variance (low ICC)."""
        # Create data where tasks are similar but approaches differ
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "elo": np.concatenate(
                    [
                        np.random.normal(1500, 50, 3),  # Approach A
                        np.random.normal(1700, 50, 3),  # Approach B
                        np.random.normal(1900, 50, 3),  # Approach C
                    ]
                ),
                "approach": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
                "task": ["t1", "t2", "t3"] * 3,
            }
        )

        result = decompose_variance(data, "elo", "approach", "task")

        # Check result is valid
        assert 0 <= result.icc <= 1
        assert result.variance_between >= 0
        assert result.variance_within >= 0

    def test_no_variance_case(self):
        """Test case with no variance (all values identical)."""
        data = pd.DataFrame(
            {
                "elo": [1500] * 9,  # All identical
                "approach": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
                "task": ["t1", "t2", "t3"] * 3,
            }
        )

        result = decompose_variance(data, "elo", "approach", "task")

        # ICC is undefined when there's no variance, but should not error
        # R² should be 0 or close to 0
        assert result.r2_marginal <= 0.01
        assert result.r2_conditional <= 0.01

    def test_icc_interpretation(self):
        """Test ICC interpretation categories."""
        # Create data with known ICC ranges
        test_cases = [
            # (variance_between, variance_within, expected_interpretation)
            (0.3, 0.7, "poor"),  # ICC = 0.3
            (0.6, 0.4, "moderate"),  # ICC = 0.6
            (0.8, 0.2, "good"),  # ICC = 0.8
            (0.95, 0.05, "excellent"),  # ICC = 0.95
        ]

        for var_between, var_within, expected in test_cases:
            # Create synthetic data
            np.random.seed(42)
            n_groups = 5
            n_per_group = 10

            group_means = np.random.normal(0, np.sqrt(var_between), n_groups)
            data_list = []

            for i, group_mean in enumerate(group_means):
                group_values = np.random.normal(group_mean, np.sqrt(var_within), n_per_group)
                for j, value in enumerate(group_values):
                    data_list.append(
                        {
                            "y": value,
                            "group": f"g{i}",
                            "x": f"x{j % 2}",  # Binary predictor
                        }
                    )

            df = pd.DataFrame(data_list)
            result = decompose_variance(df, "y", "x", "group")

            # Check interpretation matches expected category
            # Allow some flexibility due to sampling variation
            if expected == "poor":
                assert result.interpretation in ["poor", "moderate"]
            elif expected == "moderate":
                assert result.interpretation in ["poor", "moderate", "good"]
            elif expected == "good":
                assert result.interpretation in ["moderate", "good", "excellent"]
            else:  # excellent
                assert result.interpretation in ["good", "excellent"]

    def test_empty_data_raises_error(self):
        """Test that empty data raises ValueError."""
        data = pd.DataFrame({"elo": [], "approach": [], "task": []})

        with pytest.raises(ValueError, match="Data must not be empty"):
            decompose_variance(data, "elo", "approach", "task")

    def test_missing_response_variable(self):
        """Test that missing response variable raises ValueError."""
        data = pd.DataFrame(
            {
                "approach": ["A", "B"],
                "task": ["t1", "t2"],
            }
        )

        with pytest.raises(ValueError, match="Response variable 'elo' not in data"):
            decompose_variance(data, "elo", "approach", "task")

    def test_missing_group_variable(self):
        """Test that missing group variable raises ValueError."""
        data = pd.DataFrame(
            {
                "elo": [1500, 1520],
                "approach": ["A", "B"],
            }
        )

        with pytest.raises(ValueError, match="Group variable 'task' not in data"):
            decompose_variance(data, "elo", "approach", "task")

    def test_r2_values_valid_range(self):
        """Test that R² values are always in [0, 1]."""
        # Test with various data patterns
        np.random.seed(42)

        for _ in range(10):
            n = 50
            data = pd.DataFrame(
                {
                    "y": np.random.normal(1500, 100, n),
                    "x": np.random.choice(["A", "B", "C"], n),
                    "group": np.random.choice([f"g{i}" for i in range(10)], n),
                }
            )

            result = decompose_variance(data, "y", "x", "group")

            assert 0 <= result.r2_marginal <= 1
            assert 0 <= result.r2_conditional <= 1
            assert result.r2_conditional >= result.r2_marginal - 0.01

    def test_variance_components_string_representation(self):
        """Test VarianceComponents string representation."""
        vc = VarianceComponents(
            icc=0.75,
            interpretation="good",
            variance_between=300.0,
            variance_within=100.0,
            r2_marginal=0.40,
            r2_conditional=0.80,
            aic=500.0,
            bic=510.0,
        )

        s = str(vc)
        assert "ICC=0.750" in s
        assert "good" in s
        assert "R²_marginal=0.400" in s
        assert "R²_conditional=0.800" in s


class TestCalculateVarianceExplainedByFactor:
    """Tests for calculate_variance_explained_by_factor function."""

    def test_perfect_separation(self):
        """Test with perfect separation by factor."""
        data = pd.DataFrame(
            {
                "elo": [1500, 1500, 1700, 1700, 1900, 1900],
                "task": ["t1", "t1", "t2", "t2", "t3", "t3"],
            }
        )

        eta_squared = calculate_variance_explained_by_factor(data, "elo", "task")

        # Should be 1.0 (perfect separation)
        assert eta_squared == pytest.approx(1.0, abs=0.01)

    def test_no_separation(self):
        """Test with no separation by factor."""
        data = pd.DataFrame(
            {
                "elo": [1500, 1500, 1500, 1500, 1500, 1500],
                "task": ["t1", "t1", "t2", "t2", "t3", "t3"],
            }
        )

        eta_squared = calculate_variance_explained_by_factor(data, "elo", "task")

        # Should be 0.0 (no variance)
        assert eta_squared == pytest.approx(0.0, abs=0.01)

    def test_partial_separation(self):
        """Test with partial separation by factor."""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "elo": np.concatenate(
                    [
                        np.random.normal(1500, 50, 10),
                        np.random.normal(1700, 50, 10),
                        np.random.normal(1900, 50, 10),
                    ]
                ),
                "task": ["t1"] * 10 + ["t2"] * 10 + ["t3"] * 10,
            }
        )

        eta_squared = calculate_variance_explained_by_factor(data, "elo", "task")

        # Should be between 0 and 1
        assert 0 < eta_squared < 1

        # Should be relatively high (most variance is between groups)
        assert eta_squared > 0.5

    def test_missing_response_variable(self):
        """Test that missing response variable raises ValueError."""
        data = pd.DataFrame({"task": ["t1", "t2"]})

        with pytest.raises(ValueError, match="Response variable 'elo' not in data"):
            calculate_variance_explained_by_factor(data, "elo", "task")

    def test_missing_factor_variable(self):
        """Test that missing factor variable raises ValueError."""
        data = pd.DataFrame({"elo": [1500, 1520]})

        with pytest.raises(ValueError, match="Factor 'task' not in data"):
            calculate_variance_explained_by_factor(data, "elo", "task")

    def test_single_group(self):
        """Test with single group (no between-group variance)."""
        data = pd.DataFrame(
            {
                "elo": [1500, 1520, 1480, 1510],
                "task": ["t1", "t1", "t1", "t1"],
            }
        )

        eta_squared = calculate_variance_explained_by_factor(data, "elo", "task")

        # Should be 0.0 (no between-group variance)
        assert eta_squared == pytest.approx(0.0, abs=0.01)

    def test_eta_squared_range(self):
        """Test that eta-squared is always in [0, 1]."""
        np.random.seed(42)

        for _ in range(10):
            n = 50
            data = pd.DataFrame(
                {
                    "y": np.random.normal(1500, 100, n),
                    "factor": np.random.choice(["A", "B", "C", "D"], n),
                }
            )

            eta_squared = calculate_variance_explained_by_factor(data, "y", "factor")

            assert 0 <= eta_squared <= 1

    def test_multiple_factors(self):
        """Test variance explained by different factors."""
        np.random.seed(42)

        # Create data where 'task' explains more variance than 'arena'
        data = pd.DataFrame(
            {
                "elo": np.concatenate(
                    [
                        np.random.normal(1500, 30, 15),  # Task 1
                        np.random.normal(1700, 30, 15),  # Task 2
                        np.random.normal(1900, 30, 15),  # Task 3
                    ]
                ),
                "task": ["t1"] * 15 + ["t2"] * 15 + ["t3"] * 15,
                "arena": ["a1", "a2", "a3"] * 15,  # Randomly distributed
            }
        )

        eta_task = calculate_variance_explained_by_factor(data, "elo", "task")
        eta_arena = calculate_variance_explained_by_factor(data, "elo", "arena")

        # Task should explain more variance
        assert eta_task > eta_arena
