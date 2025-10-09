"""Visualization module for tournament results using Plotly.

This module provides interactive visualizations for:
- Pareto frontiers for multi-objective optimization
- Leaderboard comparisons
- Cost-effectiveness analysis
"""

from typing import Any

import numpy as np
import numpy.typing as npt
import plotly.graph_objects as go

from codegen_bench.stats.pareto import get_pareto_visualization_data


def create_pareto_plot_2d(
    approach_names: list[str],
    objectives: dict[str, npt.NDArray[np.float64]],
    objective_labels: dict[str, str] | None = None,
    title: str = "Pareto Frontier Analysis",
    reference_point: npt.NDArray[np.float64] | None = None,
    show_dominated: bool = True,
) -> go.Figure:
    """Create interactive 2D Pareto frontier visualization.

    Args:
        approach_names: List of approach names
        objectives: Dictionary with exactly 2 objectives (e.g., {"quality": [...], "cost": [...]})
        objective_labels: Optional display labels for axes (default uses objective names)
        title: Plot title
        reference_point: Optional reference point for hypervolume calculation
        show_dominated: Whether to show dominated solutions (default True)

    Returns:
        Plotly Figure object

    Raises:
        ValueError: If objectives doesn't contain exactly 2 dimensions
    """
    if len(objectives) != 2:
        raise ValueError(f"2D Pareto plot requires exactly 2 objectives, got {len(objectives)}")

    # Get visualization data
    viz_data = get_pareto_visualization_data(
        approach_names=approach_names,
        objectives=objectives,
        reference_point=reference_point,
    )

    obj_names = viz_data["objective_names"]
    obj_matrix = viz_data["objective_matrix"]
    pareto_indices = viz_data["pareto_indices"]
    dominated_mask = viz_data["dominated_mask"]

    # Set up labels
    if objective_labels is None:
        objective_labels = {name: name.replace("_", " ").title() for name in obj_names}

    x_label = objective_labels.get(obj_names[0], obj_names[0])
    y_label = objective_labels.get(obj_names[1], obj_names[1])

    # Create figure
    fig = go.Figure()

    # Add dominated points
    if show_dominated:
        dominated_indices = np.where(dominated_mask)[0]
        if len(dominated_indices) > 0:
            fig.add_trace(
                go.Scatter(
                    x=obj_matrix[dominated_indices, 0],
                    y=obj_matrix[dominated_indices, 1],
                    mode="markers",
                    name="Dominated",
                    marker={
                        "size": 8,
                        "color": "lightgray",
                        "symbol": "circle",
                    },
                    text=[approach_names[i] for i in dominated_indices],
                    hovertemplate="<b>%{text}</b><br>"
                    + f"{x_label}: %{{x:.3f}}<br>"
                    + f"{y_label}: %{{y:.3f}}<br>"
                    + "<extra></extra>",
                )
            )

    # Add Pareto optimal points
    fig.add_trace(
        go.Scatter(
            x=obj_matrix[pareto_indices, 0],
            y=obj_matrix[pareto_indices, 1],
            mode="markers",
            name="Pareto Optimal",
            marker={
                "size": 12,
                "color": "red",
                "symbol": "star",
                "line": {"width": 1, "color": "darkred"},
            },
            text=[approach_names[i] for i in pareto_indices],
            hovertemplate="<b>%{text}</b><br>"
            + f"{x_label}: %{{x:.3f}}<br>"
            + f"{y_label}: %{{y:.3f}}<br>"
            + "<i>Pareto Optimal</i><br>"
            + "<extra></extra>",
        )
    )

    # Add Pareto frontier line (connect optimal points in sorted order)
    if len(pareto_indices) > 1:
        # Sort by first objective
        sorted_idx = np.argsort(obj_matrix[pareto_indices, 0])
        sorted_pareto = pareto_indices[sorted_idx]

        fig.add_trace(
            go.Scatter(
                x=obj_matrix[sorted_pareto, 0],
                y=obj_matrix[sorted_pareto, 1],
                mode="lines",
                name="Pareto Front",
                line={"color": "red", "width": 2, "dash": "dash"},
                hoverinfo="skip",
                showlegend=True,
            )
        )

    # Update layout
    fig.update_layout(
        title={
            "text": f"{title}<br><sub>Hypervolume: {viz_data['hypervolume']:.3f}</sub>",
            "x": 0.5,
            "xanchor": "center",
        },
        xaxis_title=f"{x_label} (minimize)",
        yaxis_title=f"{y_label} (minimize)",
        hovermode="closest",
        legend={"yanchor": "top", "y": 0.99, "xanchor": "right", "x": 0.99},
        template="plotly_white",
        width=800,
        height=600,
    )

    return fig


def create_pareto_plot_3d(
    approach_names: list[str],
    objectives: dict[str, npt.NDArray[np.float64]],
    objective_labels: dict[str, str] | None = None,
    title: str = "3D Pareto Frontier Analysis",
    reference_point: npt.NDArray[np.float64] | None = None,
    show_dominated: bool = True,
) -> go.Figure:
    """Create interactive 3D Pareto frontier visualization.

    Args:
        approach_names: List of approach names
        objectives: Dictionary with exactly 3 objectives
        objective_labels: Optional display labels for axes
        title: Plot title
        reference_point: Optional reference point for hypervolume calculation
        show_dominated: Whether to show dominated solutions

    Returns:
        Plotly Figure object

    Raises:
        ValueError: If objectives doesn't contain exactly 3 dimensions
    """
    if len(objectives) != 3:
        raise ValueError(f"3D Pareto plot requires exactly 3 objectives, got {len(objectives)}")

    # Get visualization data
    viz_data = get_pareto_visualization_data(
        approach_names=approach_names,
        objectives=objectives,
        reference_point=reference_point,
    )

    obj_names = viz_data["objective_names"]
    obj_matrix = viz_data["objective_matrix"]
    pareto_indices = viz_data["pareto_indices"]
    dominated_mask = viz_data["dominated_mask"]

    # Set up labels
    if objective_labels is None:
        objective_labels = {name: name.replace("_", " ").title() for name in obj_names}

    x_label = objective_labels.get(obj_names[0], obj_names[0])
    y_label = objective_labels.get(obj_names[1], obj_names[1])
    z_label = objective_labels.get(obj_names[2], obj_names[2])

    # Create figure
    fig = go.Figure()

    # Add dominated points
    if show_dominated:
        dominated_indices = np.where(dominated_mask)[0]
        if len(dominated_indices) > 0:
            fig.add_trace(
                go.Scatter3d(
                    x=obj_matrix[dominated_indices, 0],
                    y=obj_matrix[dominated_indices, 1],
                    z=obj_matrix[dominated_indices, 2],
                    mode="markers",
                    name="Dominated",
                    marker={"size": 4, "color": "lightgray", "symbol": "circle"},
                    text=[approach_names[i] for i in dominated_indices],
                    hovertemplate="<b>%{text}</b><br>"
                    + f"{x_label}: %{{x:.3f}}<br>"
                    + f"{y_label}: %{{y:.3f}}<br>"
                    + f"{z_label}: %{{z:.3f}}<br>"
                    + "<extra></extra>",
                )
            )

    # Add Pareto optimal points
    fig.add_trace(
        go.Scatter3d(
            x=obj_matrix[pareto_indices, 0],
            y=obj_matrix[pareto_indices, 1],
            z=obj_matrix[pareto_indices, 2],
            mode="markers",
            name="Pareto Optimal",
            marker={
                "size": 8,
                "color": "red",
                "symbol": "diamond",
                "line": {"width": 1, "color": "darkred"},
            },
            text=[approach_names[i] for i in pareto_indices],
            hovertemplate="<b>%{text}</b><br>"
            + f"{x_label}: %{{x:.3f}}<br>"
            + f"{y_label}: %{{y:.3f}}<br>"
            + f"{z_label}: %{{z:.3f}}<br>"
            + "<i>Pareto Optimal</i><br>"
            + "<extra></extra>",
        )
    )

    # Update layout
    fig.update_layout(
        title={
            "text": f"{title}<br><sub>Hypervolume: {viz_data['hypervolume']:.3f}</sub>",
            "x": 0.5,
            "xanchor": "center",
        },
        scene={
            "xaxis_title": f"{x_label} (minimize)",
            "yaxis_title": f"{y_label} (minimize)",
            "zaxis_title": f"{z_label} (minimize)",
        },
        hovermode="closest",
        template="plotly_white",
        width=900,
        height=700,
    )

    return fig


def create_pareto_parallel_coordinates(
    approach_names: list[str],
    objectives: dict[str, npt.NDArray[np.float64]],
    objective_labels: dict[str, str] | None = None,
    title: str = "Multi-Objective Parallel Coordinates",
    reference_point: npt.NDArray[np.float64] | None = None,
) -> go.Figure:
    """Create parallel coordinates plot for multi-objective analysis (works for any number of objectives).

    Args:
        approach_names: List of approach names
        objectives: Dictionary of objectives (can have 2+ objectives)
        objective_labels: Optional display labels
        title: Plot title
        reference_point: Optional reference point for hypervolume calculation

    Returns:
        Plotly Figure object
    """
    # Get visualization data
    viz_data = get_pareto_visualization_data(
        approach_names=approach_names,
        objectives=objectives,
        reference_point=reference_point,
    )

    obj_names = viz_data["objective_names"]
    obj_matrix = viz_data["objective_matrix"]
    pareto_indices = viz_data["pareto_indices"]

    # Set up labels
    if objective_labels is None:
        objective_labels = {name: name.replace("_", " ").title() for name in obj_names}

    # Create color array (Pareto optimal = 1, dominated = 0)
    colors = np.zeros(len(approach_names))
    colors[pareto_indices] = 1

    # Build dimensions for parallel coordinates
    dimensions = []
    for i, obj_name in enumerate(obj_names):
        dimensions.append(
            {
                "label": objective_labels.get(obj_name, obj_name),
                "values": obj_matrix[:, i],
            }
        )

    # Create figure
    fig = go.Figure(
        data=go.Parcoords(
            line={
                "color": colors,
                "colorscale": [[0, "lightgray"], [1, "red"]],
                "showscale": True,
                "cmin": 0,
                "cmax": 1,
                "colorbar": {
                    "title": "Status",
                    "tickvals": [0.25, 0.75],
                    "ticktext": ["Dominated", "Pareto Optimal"],
                },
            },
            dimensions=dimensions,
            labelangle=-45,
        )
    )

    fig.update_layout(
        title={
            "text": f"{title}<br><sub>Hypervolume: {viz_data['hypervolume']:.3f}</sub>",
            "x": 0.5,
            "xanchor": "center",
        },
        template="plotly_white",
        width=900,
        height=600,
    )

    return fig


def create_pareto_visualization(
    approach_names: list[str],
    objectives: dict[str, npt.NDArray[np.float64]],
    objective_labels: dict[str, str] | None = None,
    title: str = "Pareto Frontier Analysis",
    reference_point: npt.NDArray[np.float64] | None = None,
    show_dominated: bool = True,
) -> go.Figure:
    """Create appropriate Pareto visualization based on number of objectives.

    Automatically selects:
    - 2D scatter plot for 2 objectives
    - 3D scatter plot for 3 objectives
    - Parallel coordinates for 4+ objectives

    Args:
        approach_names: List of approach names
        objectives: Dictionary of objectives
        objective_labels: Optional display labels
        title: Plot title
        reference_point: Optional reference point for hypervolume
        show_dominated: Whether to show dominated solutions (2D/3D only)

    Returns:
        Plotly Figure object

    Raises:
        ValueError: If objectives is empty or has only 1 objective
    """
    n_objectives = len(objectives)

    if n_objectives < 2:
        raise ValueError(f"Pareto analysis requires at least 2 objectives, got {n_objectives}")
    elif n_objectives == 2:
        return create_pareto_plot_2d(
            approach_names=approach_names,
            objectives=objectives,
            objective_labels=objective_labels,
            title=title,
            reference_point=reference_point,
            show_dominated=show_dominated,
        )
    elif n_objectives == 3:
        return create_pareto_plot_3d(
            approach_names=approach_names,
            objectives=objectives,
            objective_labels=objective_labels,
            title=title,
            reference_point=reference_point,
            show_dominated=show_dominated,
        )
    else:
        # Use parallel coordinates for 4+ objectives
        return create_pareto_parallel_coordinates(
            approach_names=approach_names,
            objectives=objectives,
            objective_labels=objective_labels,
            title=title,
            reference_point=reference_point,
        )


def save_visualization(
    fig: go.Figure,
    output_path: str,
    format: str = "html",
    **kwargs: Any,
) -> None:
    """Save Plotly figure to file.

    Args:
        fig: Plotly Figure object
        output_path: Path to save file
        format: Output format ("html", "png", "svg", "pdf")
        **kwargs: Additional arguments passed to write_* methods

    Raises:
        ValueError: If format is not supported
    """
    format = format.lower()

    if format == "html":
        fig.write_html(output_path, **kwargs)
    elif format in ("png", "svg", "pdf"):
        # These require kaleido or orca
        try:
            if format == "png":
                fig.write_image(output_path, format="png", **kwargs)
            elif format == "svg":
                fig.write_image(output_path, format="svg", **kwargs)
            elif format == "pdf":
                fig.write_image(output_path, format="pdf", **kwargs)
        except ImportError as e:
            raise ImportError(
                "Image export requires kaleido. Install with: pip install kaleido"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to export image to {format} format: {e}") from e
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'html', 'png', 'svg', or 'pdf'")
