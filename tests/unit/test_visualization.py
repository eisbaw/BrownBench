"""Tests for Pareto visualization module."""

import tempfile
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import pytest

from codegen_bench.reporting.visualization import (
    create_pareto_parallel_coordinates,
    create_pareto_plot_2d,
    create_pareto_plot_3d,
    create_pareto_visualization,
    save_visualization,
)


@pytest.fixture
def sample_2d_data():
    """Sample 2D data for testing."""
    return {
        "approach_names": ["A", "B", "C", "D"],
        "objectives": {
            "quality": np.array([1.0, 2.0, 1.5, 3.0]),  # Lower is better
            "cost": np.array([3.0, 1.0, 2.0, 2.5]),  # Lower is better
        },
    }


@pytest.fixture
def sample_3d_data():
    """Sample 3D data for testing."""
    return {
        "approach_names": ["A", "B", "C", "D", "E"],
        "objectives": {
            "quality": np.array([1.0, 2.0, 1.5, 3.0, 2.5]),
            "cost": np.array([3.0, 1.0, 2.0, 2.5, 1.5]),
            "speed": np.array([2.0, 3.0, 1.0, 1.5, 2.0]),
        },
    }


@pytest.fixture
def sample_4d_data():
    """Sample 4D data for testing (requires parallel coordinates)."""
    return {
        "approach_names": ["A", "B", "C", "D"],
        "objectives": {
            "quality": np.array([1.0, 2.0, 1.5, 3.0]),
            "cost": np.array([3.0, 1.0, 2.0, 2.5]),
            "speed": np.array([2.0, 3.0, 1.0, 1.5]),
            "memory": np.array([1.5, 2.0, 2.5, 1.0]),
        },
    }


class TestParetoPlot2D:
    """Tests for 2D Pareto plot creation."""

    def test_creates_valid_figure(self, sample_2d_data):
        """Test that a valid Plotly figure is created."""
        fig = create_pareto_plot_2d(**sample_2d_data)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_shows_pareto_optimal_points(self, sample_2d_data):
        """Test that Pareto optimal points are marked correctly."""
        fig = create_pareto_plot_2d(**sample_2d_data)

        # Find Pareto optimal trace
        pareto_trace = None
        for trace in fig.data:
            if trace.name == "Pareto Optimal":
                pareto_trace = trace
                break

        assert pareto_trace is not None
        assert len(pareto_trace.x) > 0
        assert pareto_trace.marker.symbol == "star"

    def test_shows_dominated_points_when_enabled(self, sample_2d_data):
        """Test that dominated points are shown when show_dominated=True."""
        fig = create_pareto_plot_2d(**sample_2d_data, show_dominated=True)

        # Check for dominated trace
        dominated_trace = None
        for trace in fig.data:
            if trace.name == "Dominated":
                dominated_trace = trace
                break

        assert dominated_trace is not None

    def test_hides_dominated_points_when_disabled(self, sample_2d_data):
        """Test that dominated points are hidden when show_dominated=False."""
        fig = create_pareto_plot_2d(**sample_2d_data, show_dominated=False)

        # Check that no dominated trace exists
        for trace in fig.data:
            assert trace.name != "Dominated"

    def test_custom_objective_labels(self, sample_2d_data):
        """Test that custom objective labels are applied."""
        labels = {"quality": "Solution Quality", "cost": "Total Cost"}
        fig = create_pareto_plot_2d(**sample_2d_data, objective_labels=labels)

        # Check axis labels
        assert "Solution Quality" in fig.layout.xaxis.title.text
        assert "Total Cost" in fig.layout.yaxis.title.text

    def test_custom_title(self, sample_2d_data):
        """Test that custom title is applied."""
        title = "My Custom Title"
        fig = create_pareto_plot_2d(**sample_2d_data, title=title)
        assert title in fig.layout.title.text

    def test_includes_hypervolume_in_title(self, sample_2d_data):
        """Test that hypervolume is included in the title."""
        fig = create_pareto_plot_2d(**sample_2d_data)
        assert "Hypervolume" in fig.layout.title.text

    def test_rejects_non_2d_objectives(self, sample_3d_data):
        """Test that error is raised for non-2D objectives."""
        with pytest.raises(ValueError, match="exactly 2 objectives"):
            create_pareto_plot_2d(**sample_3d_data)

    def test_with_reference_point(self, sample_2d_data):
        """Test that custom reference point is used."""
        ref_point = np.array([5.0, 5.0])
        fig = create_pareto_plot_2d(**sample_2d_data, reference_point=ref_point)
        assert isinstance(fig, go.Figure)

    def test_pareto_frontier_line_present(self, sample_2d_data):
        """Test that Pareto frontier connecting line is present."""
        fig = create_pareto_plot_2d(**sample_2d_data)

        # Check for frontier line trace
        frontier_trace = None
        for trace in fig.data:
            if trace.name == "Pareto Front":
                frontier_trace = trace
                break

        assert frontier_trace is not None
        assert frontier_trace.mode == "lines"


class TestParetoPlot3D:
    """Tests for 3D Pareto plot creation."""

    def test_creates_valid_figure(self, sample_3d_data):
        """Test that a valid Plotly figure is created."""
        fig = create_pareto_plot_3d(**sample_3d_data)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_shows_pareto_optimal_points(self, sample_3d_data):
        """Test that Pareto optimal points are marked correctly."""
        fig = create_pareto_plot_3d(**sample_3d_data)

        # Find Pareto optimal trace
        pareto_trace = None
        for trace in fig.data:
            if trace.name == "Pareto Optimal":
                pareto_trace = trace
                break

        assert pareto_trace is not None
        assert len(pareto_trace.x) > 0

    def test_rejects_non_3d_objectives(self, sample_2d_data):
        """Test that error is raised for non-3D objectives."""
        with pytest.raises(ValueError, match="exactly 3 objectives"):
            create_pareto_plot_3d(**sample_2d_data)

    def test_custom_objective_labels(self, sample_3d_data):
        """Test that custom objective labels are applied."""
        labels = {
            "quality": "Solution Quality",
            "cost": "Total Cost",
            "speed": "Execution Speed",
        }
        fig = create_pareto_plot_3d(**sample_3d_data, objective_labels=labels)

        # Check scene axis labels
        assert "Solution Quality" in fig.layout.scene.xaxis.title.text
        assert "Total Cost" in fig.layout.scene.yaxis.title.text
        assert "Execution Speed" in fig.layout.scene.zaxis.title.text

    def test_includes_hypervolume_in_title(self, sample_3d_data):
        """Test that hypervolume is included in the title."""
        fig = create_pareto_plot_3d(**sample_3d_data)
        assert "Hypervolume" in fig.layout.title.text


class TestParetoParallelCoordinates:
    """Tests for parallel coordinates plot creation."""

    def test_creates_valid_figure(self, sample_4d_data):
        """Test that a valid Plotly figure is created."""
        fig = create_pareto_parallel_coordinates(**sample_4d_data)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_works_with_2d_data(self, sample_2d_data):
        """Test that parallel coordinates works with 2D data."""
        fig = create_pareto_parallel_coordinates(**sample_2d_data)
        assert isinstance(fig, go.Figure)

    def test_works_with_3d_data(self, sample_3d_data):
        """Test that parallel coordinates works with 3D data."""
        fig = create_pareto_parallel_coordinates(**sample_3d_data)
        assert isinstance(fig, go.Figure)

    def test_includes_all_objectives(self, sample_4d_data):
        """Test that all objectives are included as dimensions."""
        fig = create_pareto_parallel_coordinates(**sample_4d_data)

        # Parcoords should have dimensions for each objective
        parcoords_trace = fig.data[0]
        assert len(parcoords_trace.dimensions) == len(sample_4d_data["objectives"])

    def test_custom_objective_labels(self, sample_4d_data):
        """Test that custom objective labels are applied."""
        labels = {
            "quality": "Q",
            "cost": "C",
            "speed": "S",
            "memory": "M",
        }
        fig = create_pareto_parallel_coordinates(**sample_4d_data, objective_labels=labels)

        parcoords_trace = fig.data[0]
        dimension_labels = [dim["label"] for dim in parcoords_trace.dimensions]

        assert "Q" in dimension_labels
        assert "C" in dimension_labels
        assert "S" in dimension_labels
        assert "M" in dimension_labels


class TestParetoVisualization:
    """Tests for automatic visualization selection."""

    def test_selects_2d_plot_for_2_objectives(self, sample_2d_data):
        """Test that 2D plot is selected for 2 objectives."""
        fig = create_pareto_visualization(**sample_2d_data)
        assert isinstance(fig, go.Figure)
        # 2D plot should have Scatter traces
        assert any(isinstance(trace, go.Scatter) for trace in fig.data)

    def test_selects_3d_plot_for_3_objectives(self, sample_3d_data):
        """Test that 3D plot is selected for 3 objectives."""
        fig = create_pareto_visualization(**sample_3d_data)
        assert isinstance(fig, go.Figure)
        # 3D plot should have Scatter3d traces
        assert any(isinstance(trace, go.Scatter3d) for trace in fig.data)

    def test_selects_parallel_coords_for_4_objectives(self, sample_4d_data):
        """Test that parallel coordinates is selected for 4+ objectives."""
        fig = create_pareto_visualization(**sample_4d_data)
        assert isinstance(fig, go.Figure)
        # Parallel coordinates should have Parcoords trace
        assert any(isinstance(trace, go.Parcoords) for trace in fig.data)

    def test_rejects_single_objective(self):
        """Test that error is raised for single objective."""
        data = {
            "approach_names": ["A", "B"],
            "objectives": {"quality": np.array([1.0, 2.0])},
        }
        with pytest.raises(ValueError, match="at least 2 objectives"):
            create_pareto_visualization(**data)

    def test_rejects_empty_objectives(self):
        """Test that error is raised for empty objectives."""
        data = {"approach_names": ["A", "B"], "objectives": {}}
        with pytest.raises(ValueError, match="at least 2 objectives"):
            create_pareto_visualization(**data)


class TestSaveVisualization:
    """Tests for saving visualizations."""

    def test_saves_html_format(self, sample_2d_data):
        """Test that HTML format can be saved."""
        fig = create_pareto_plot_2d(**sample_2d_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.html"
            save_visualization(fig, str(output_path), format="html")
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_html_format_is_default(self, sample_2d_data):
        """Test that HTML is the default format."""
        fig = create_pareto_plot_2d(**sample_2d_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.html"
            save_visualization(fig, str(output_path))  # No format specified
            assert output_path.exists()

    def test_rejects_unsupported_format(self, sample_2d_data):
        """Test that unsupported format raises error."""
        fig = create_pareto_plot_2d(**sample_2d_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.xyz"
            with pytest.raises(ValueError, match="Unsupported format"):
                save_visualization(fig, str(output_path), format="xyz")

    def test_format_case_insensitive(self, sample_2d_data):
        """Test that format parameter is case-insensitive."""
        fig = create_pareto_plot_2d(**sample_2d_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.html"
            save_visualization(fig, str(output_path), format="HTML")
            assert output_path.exists()


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_single_approach(self):
        """Test with single approach (trivial Pareto front)."""
        data = {
            "approach_names": ["A"],
            "objectives": {
                "quality": np.array([1.0]),
                "cost": np.array([2.0]),
            },
        }
        fig = create_pareto_plot_2d(**data)
        assert isinstance(fig, go.Figure)

    def test_all_dominated_except_one(self):
        """Test case where only one point is Pareto optimal."""
        data = {
            "approach_names": ["Best", "Worse1", "Worse2"],
            "objectives": {
                "quality": np.array([1.0, 2.0, 3.0]),
                "cost": np.array([1.0, 2.0, 3.0]),
            },
        }
        fig = create_pareto_plot_2d(**data)

        # Find Pareto optimal trace
        pareto_trace = None
        for trace in fig.data:
            if trace.name == "Pareto Optimal":
                pareto_trace = trace
                break

        assert pareto_trace is not None
        assert len(pareto_trace.x) == 1  # Only one Pareto optimal point

    def test_all_pareto_optimal(self):
        """Test case where all points are Pareto optimal (incomparable)."""
        data = {
            "approach_names": ["A", "B", "C"],
            "objectives": {
                "quality": np.array([1.0, 2.0, 3.0]),
                "cost": np.array([3.0, 2.0, 1.0]),
            },
        }
        fig = create_pareto_plot_2d(**data)

        # Find Pareto optimal trace
        pareto_trace = None
        for trace in fig.data:
            if trace.name == "Pareto Optimal":
                pareto_trace = trace
                break

        assert pareto_trace is not None
        assert len(pareto_trace.x) == 3  # All three points are Pareto optimal

    def test_empty_approach_names_raises_error(self):
        """Test that empty approach names raises error."""
        data = {
            "approach_names": [],
            "objectives": {
                "quality": np.array([]),
                "cost": np.array([]),
            },
        }
        with pytest.raises(ValueError):
            create_pareto_plot_2d(**data)

    def test_mismatched_lengths_raises_error(self):
        """Test that mismatched array lengths raise error."""
        data = {
            "approach_names": ["A", "B", "C"],
            "objectives": {
                "quality": np.array([1.0, 2.0]),  # Wrong length
                "cost": np.array([1.0, 2.0, 3.0]),
            },
        }
        with pytest.raises(ValueError):
            create_pareto_plot_2d(**data)
