"""Unit tests for Pareto frontier analysis."""

import numpy as np
import numpy.typing as npt
import pytest

from codegen_bench.stats.pareto import (
    ParetoResult,
    analyze_pareto_frontier,
    calculate_hypervolume,
    find_pareto_front,
    get_pareto_visualization_data,
    is_dominated,
)


class TestIsDominated:
    """Tests for domination checking."""

    def test_dominated_by_single_point(self) -> None:
        """Test point clearly dominated by another."""
        point = np.array([5.0, 5.0])
        other_points = np.array([[3.0, 3.0], [6.0, 6.0]])
        assert is_dominated(point, other_points)

    def test_not_dominated(self) -> None:
        """Test point not dominated by any other."""
        point = np.array([1.0, 5.0])
        other_points = np.array([[2.0, 4.0], [3.0, 2.0]])
        assert not is_dominated(point, other_points)

    def test_equal_point_not_dominated(self) -> None:
        """Test equal point is not considered dominated."""
        point = np.array([3.0, 3.0])
        other_points = np.array([[3.0, 3.0], [4.0, 4.0]])
        assert not is_dominated(point, other_points)

    def test_partially_better_not_dominated(self) -> None:
        """Test point better in one objective, worse in another."""
        point = np.array([2.0, 5.0])
        other_points = np.array([[3.0, 4.0], [4.0, 3.0]])
        assert not is_dominated(point, other_points)

    def test_three_objectives(self) -> None:
        """Test domination with 3 objectives."""
        point = np.array([5.0, 5.0, 5.0])
        other_points = np.array([[4.0, 4.0, 4.0], [6.0, 6.0, 6.0]])
        assert is_dominated(point, other_points)


class TestFindParetoFront:
    """Tests for Pareto front identification."""

    def test_simple_2d_front(self) -> None:
        """Test simple 2D Pareto front."""
        objectives = np.array(
            [
                [1.0, 5.0],  # Pareto optimal
                [2.0, 3.0],  # Pareto optimal
                [3.0, 2.0],  # Pareto optimal
                [2.5, 4.0],  # Dominated by point 1
                [4.0, 4.0],  # Dominated
            ]
        )
        pareto = find_pareto_front(objectives)
        expected = np.array([0, 1, 2])
        np.testing.assert_array_equal(pareto, expected)

    def test_all_pareto_optimal(self) -> None:
        """Test when all points are Pareto optimal."""
        objectives = np.array(
            [
                [1.0, 3.0],
                [2.0, 2.0],
                [3.0, 1.0],
            ]
        )
        pareto = find_pareto_front(objectives)
        expected = np.array([0, 1, 2])
        np.testing.assert_array_equal(pareto, expected)

    def test_single_optimal(self) -> None:
        """Test when single point dominates all."""
        objectives = np.array(
            [
                [1.0, 1.0],  # Dominates all
                [2.0, 2.0],
                [3.0, 3.0],
            ]
        )
        pareto = find_pareto_front(objectives)
        expected = np.array([0])
        np.testing.assert_array_equal(pareto, expected)

    def test_three_objectives(self) -> None:
        """Test Pareto front with 3 objectives."""
        objectives = np.array(
            [
                [1.0, 2.0, 3.0],  # Pareto optimal
                [2.0, 1.0, 4.0],  # Pareto optimal
                [3.0, 3.0, 1.0],  # Pareto optimal
                [2.0, 2.0, 3.0],  # Dominated by point 0
            ]
        )
        pareto = find_pareto_front(objectives)
        assert len(pareto) == 3
        assert 3 not in pareto


class TestCalculateHypervolume:
    """Tests for hypervolume calculation."""

    def test_1d_hypervolume(self) -> None:
        """Test 1D hypervolume (simple range)."""
        pareto_front = np.array([[2.0]])
        reference_point = np.array([5.0])
        hv = calculate_hypervolume(pareto_front, reference_point)
        assert hv == 3.0

    def test_2d_hypervolume_single_point(self) -> None:
        """Test 2D hypervolume with single point."""
        pareto_front = np.array([[2.0, 3.0]])
        reference_point = np.array([5.0, 6.0])
        hv = calculate_hypervolume(pareto_front, reference_point)
        # Area = (5-2) * (6-3) = 3 * 3 = 9
        assert hv == 9.0

    def test_2d_hypervolume_multiple_points(self) -> None:
        """Test 2D hypervolume with multiple points."""
        pareto_front = np.array(
            [
                [1.0, 4.0],
                [2.0, 2.0],
                [4.0, 1.0],
            ]
        )
        reference_point = np.array([5.0, 5.0])
        hv = calculate_hypervolume(pareto_front, reference_point)
        # Correct hypervolume from pymoo (not the buggy implementation)
        assert hv == 11.0

    def test_3d_hypervolume_single_point(self) -> None:
        """Test 3D hypervolume with single point."""
        pareto_front = np.array([[1.0, 2.0, 3.0]])
        reference_point = np.array([4.0, 5.0, 6.0])
        hv = calculate_hypervolume(pareto_front, reference_point)
        # Volume = (4-1) * (5-2) * (6-3) = 3 * 3 * 3 = 27
        assert hv == 27.0

    def test_invalid_reference_point(self) -> None:
        """Test error when reference point doesn't dominate."""
        pareto_front = np.array([[5.0, 5.0]])
        reference_point = np.array([3.0, 3.0])  # Doesn't dominate
        with pytest.raises(ValueError, match="Reference point must dominate"):
            calculate_hypervolume(pareto_front, reference_point)

    def test_high_dimensional_hypervolume(self) -> None:
        """Test hypervolume with > 3 objectives (pymoo supports this)."""
        pareto_front = np.array([[1.0, 2.0, 3.0, 4.0]])
        reference_point = np.array([5.0, 6.0, 7.0, 8.0])
        # pymoo supports any number of objectives
        hv = calculate_hypervolume(pareto_front, reference_point)
        assert hv > 0  # Should compute successfully


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_objectives(self) -> None:
        """Test error with empty objectives array."""
        objectives = np.array([]).reshape(0, 2)
        with pytest.raises(ValueError, match="cannot be empty"):
            find_pareto_front(objectives)

    def test_invalid_objectives_shape(self) -> None:
        """Test error with 1D objectives array."""
        objectives = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="must be 2D array"):
            find_pareto_front(objectives)

    def test_mismatched_objective_lengths(self) -> None:
        """Test error when objective arrays have different lengths."""
        approach_names = ["A", "B"]
        objectives = {
            "quality": np.array([1.0, 2.0]),
            "cost": np.array([3.0]),  # Wrong length
        }
        with pytest.raises(ValueError, match="same length"):
            get_pareto_visualization_data(approach_names, objectives)

    def test_mismatched_approach_count(self) -> None:
        """Test error when approach count doesn't match objective length."""
        approach_names = ["A"]
        objectives = {
            "quality": np.array([1.0, 2.0]),
            "cost": np.array([3.0, 4.0]),
        }
        with pytest.raises(ValueError, match="must match"):
            get_pareto_visualization_data(approach_names, objectives)

    def test_empty_objectives_dict(self) -> None:
        """Test error with empty objectives dictionary."""
        approach_names = ["A", "B"]
        objectives: dict[str, npt.NDArray[np.float64]] = {}
        with pytest.raises(ValueError, match="cannot be empty"):
            get_pareto_visualization_data(approach_names, objectives)

    def test_empty_approach_names(self) -> None:
        """Test error with empty approach names list."""
        approach_names: list[str] = []
        objectives = {"quality": np.array([1.0, 2.0])}
        with pytest.raises(ValueError, match="cannot be empty"):
            get_pareto_visualization_data(approach_names, objectives)


class TestAnalyzeParetoFrontier:
    """Tests for complete Pareto analysis."""

    def test_basic_analysis(self) -> None:
        """Test basic Pareto frontier analysis."""
        objectives = np.array(
            [
                [1.0, 5.0],  # Pareto optimal
                [2.0, 3.0],  # Pareto optimal
                [3.0, 2.0],  # Pareto optimal
                [2.5, 4.0],  # Dominated
            ]
        )
        result = analyze_pareto_frontier(objectives)

        assert isinstance(result, ParetoResult)
        assert len(result.pareto_indices) == 3
        assert result.pareto_front.shape == (3, 2)
        assert result.hypervolume > 0
        assert result.dominated_mask.sum() == 1  # 1 dominated point

    def test_auto_reference_point(self) -> None:
        """Test automatic reference point calculation."""
        objectives = np.array(
            [
                [1.0, 2.0],
                [2.0, 1.0],
            ]
        )
        result = analyze_pareto_frontier(objectives)

        # Reference point should be max values * 1.1
        expected_ref = np.array([2.0, 2.0]) * 1.1
        np.testing.assert_array_almost_equal(result.reference_point, expected_ref)

    def test_custom_reference_point(self) -> None:
        """Test with custom reference point."""
        objectives = np.array(
            [
                [1.0, 2.0],
                [2.0, 1.0],
            ]
        )
        reference_point = np.array([5.0, 5.0])
        result = analyze_pareto_frontier(objectives, reference_point)

        np.testing.assert_array_equal(result.reference_point, reference_point)

    def test_dominated_mask_correct(self) -> None:
        """Test that dominated mask is correctly set."""
        objectives = np.array(
            [
                [1.0, 1.0],  # Dominates all
                [2.0, 2.0],  # Dominated
                [3.0, 3.0],  # Dominated
            ]
        )
        result = analyze_pareto_frontier(objectives)

        expected_mask = np.array([False, True, True])
        np.testing.assert_array_equal(result.dominated_mask, expected_mask)


class TestGetParetoVisualizationData:
    """Tests for visualization data preparation."""

    def test_basic_visualization_data(self) -> None:
        """Test basic visualization data generation."""
        approach_names = ["A", "B", "C"]
        objectives = {
            "quality": np.array([1.0, 2.0, 3.0]),
            "cost": np.array([5.0, 3.0, 2.0]),
        }

        data = get_pareto_visualization_data(approach_names, objectives)

        assert data["objective_names"] == ["quality", "cost"]
        assert data["approach_names"] == approach_names
        assert "pareto_indices" in data
        assert "pareto_approaches" in data
        assert "hypervolume" in data
        assert data["objective_matrix"].shape == (3, 2)

    def test_pareto_approaches_identified(self) -> None:
        """Test that Pareto optimal approaches are correctly identified."""
        approach_names = ["Simple", "Elaborate", "Expert"]
        objectives = {
            "cost": np.array([1.0, 2.0, 4.0]),
            "quality": np.array([5.0, 3.0, 1.0]),
        }

        data = get_pareto_visualization_data(approach_names, objectives)

        # Points (1,5) and (2,3) should be Pareto optimal
        # Point (4,1) is dominated by (2,3) in cost but not in quality, so it's also Pareto
        assert "Simple" in data["pareto_approaches"]

    def test_three_objectives(self) -> None:
        """Test with three objectives."""
        approach_names = ["A", "B", "C"]
        objectives = {
            "quality": np.array([1.0, 2.0, 3.0]),
            "cost": np.array([3.0, 2.0, 1.0]),
            "speed": np.array([2.0, 2.0, 2.0]),
        }

        data = get_pareto_visualization_data(approach_names, objectives)

        assert len(data["objective_names"]) == 3
        assert data["objective_matrix"].shape == (3, 3)

    def test_custom_reference_point(self) -> None:
        """Test with custom reference point."""
        approach_names = ["A", "B"]
        objectives = {
            "quality": np.array([1.0, 2.0]),
            "cost": np.array([2.0, 1.0]),
        }
        reference_point = np.array([10.0, 10.0])

        data = get_pareto_visualization_data(approach_names, objectives, reference_point)

        np.testing.assert_array_equal(data["reference_point"], reference_point)

    def test_dominated_mask_in_data(self) -> None:
        """Test that dominated mask is included in data."""
        approach_names = ["Best", "Dominated"]
        objectives = {
            "cost": np.array([1.0, 2.0]),
            "quality": np.array([1.0, 2.0]),
        }

        data = get_pareto_visualization_data(approach_names, objectives)

        expected_mask = np.array([False, True])
        np.testing.assert_array_equal(data["dominated_mask"], expected_mask)
