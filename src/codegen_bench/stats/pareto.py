"""Pareto frontier analysis for multi-objective optimization.

This module provides functionality for identifying Pareto optimal solutions
when evaluating code generation approaches across multiple objectives
(e.g., quality, cost, speed).
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class ParetoResult:
    """Results from Pareto frontier analysis (immutable).

    Attributes:
        pareto_indices: Indices of solutions on the Pareto front
        pareto_front: Objective values of Pareto optimal solutions (n_pareto x n_objectives)
        hypervolume: Hypervolume indicator value (quality metric)
        dominated_mask: Boolean array indicating which solutions are dominated
        reference_point: Reference point used for hypervolume calculation
    """

    pareto_indices: npt.NDArray[np.int_]
    pareto_front: npt.NDArray[np.float64]
    hypervolume: float
    dominated_mask: npt.NDArray[np.bool_]
    reference_point: npt.NDArray[np.float64]


def is_dominated(point: npt.NDArray[np.float64], other_points: npt.NDArray[np.float64]) -> bool:
    """Check if a point is dominated by any point in the set.

    A point is dominated if another point is at least as good in all objectives
    and strictly better in at least one objective (for minimization).

    Args:
        point: Single point to check (n_objectives,)
        other_points: Set of points to compare against (n_points x n_objectives)

    Returns:
        True if point is dominated by any point in other_points
    """
    # Check if any point dominates (is <= in all dims and < in at least one)
    better_or_equal = np.all(other_points <= point, axis=1)
    strictly_better = np.any(other_points < point, axis=1)
    return bool(np.any(better_or_equal & strictly_better))


def find_pareto_front(
    objectives: npt.NDArray[np.float64],
) -> npt.NDArray[np.int_]:
    """Find indices of points on the Pareto front.

    Assumes minimization for all objectives.
    Complexity: O(n²) where n is the number of points.

    Args:
        objectives: Array of objective values (n_points x n_objectives)

    Returns:
        Array of indices for points on the Pareto front

    Raises:
        ValueError: If objectives is not 2D or is empty
    """
    if objectives.ndim != 2:
        raise ValueError(f"objectives must be 2D array, got shape {objectives.shape}")
    if objectives.shape[0] == 0:
        raise ValueError("objectives array cannot be empty")

    n_points = objectives.shape[0]
    pareto_mask = np.ones(n_points, dtype=bool)

    for i in range(n_points):
        if pareto_mask[i]:
            # Compare point i with all other points
            other_indices = np.arange(n_points) != i
            pareto_mask[i] = not is_dominated(objectives[i], objectives[other_indices])

    return np.where(pareto_mask)[0]


def calculate_hypervolume(
    pareto_front: npt.NDArray[np.float64],
    reference_point: npt.NDArray[np.float64],
) -> float:
    """Calculate hypervolume indicator for the Pareto front.

    The hypervolume is the volume of the space dominated by the Pareto front
    and bounded by the reference point. Larger values indicate better coverage.

    This implementation uses pymoo's proven HV indicator for correctness.

    Args:
        pareto_front: Points on the Pareto front (n_points x n_objectives)
        reference_point: Reference point (worst possible values) for each objective

    Returns:
        Hypervolume value

    Raises:
        ImportError: If pymoo is not installed
        ValueError: If reference point doesn't dominate all points
    """
    try:
        from pymoo.indicators.hv import HV
    except ImportError as e:
        raise ImportError(
            "Hypervolume calculation requires pymoo. "
            "Install with: pip install pymoo"
        ) from e

    # Validate reference point dominates all points
    if not np.all(pareto_front <= reference_point):
        raise ValueError("Reference point must dominate all points in the Pareto front")

    hv_indicator = HV(ref_point=reference_point)
    return float(hv_indicator(pareto_front))


def analyze_pareto_frontier(
    objectives: npt.NDArray[np.float64],
    reference_point: npt.NDArray[np.float64] | None = None,
) -> ParetoResult:
    """Perform complete Pareto frontier analysis.

    Args:
        objectives: Array of objective values (n_points x n_objectives)
            All objectives assumed to be minimized
        reference_point: Reference point for hypervolume (worst values)
            If None, uses max values + 10% margin

    Returns:
        ParetoResult with frontier, hypervolume, and domination info
    """
    # Find Pareto front
    pareto_indices = find_pareto_front(objectives)
    pareto_front = objectives[pareto_indices]

    # Calculate reference point if not provided
    if reference_point is None:
        max_values = np.max(objectives, axis=0)
        reference_point = max_values * 1.1  # 10% margin

    # Calculate hypervolume
    hv = calculate_hypervolume(pareto_front, reference_point)

    # Create domination mask
    dominated_mask = np.ones(len(objectives), dtype=bool)
    dominated_mask[pareto_indices] = False

    return ParetoResult(
        pareto_indices=pareto_indices,
        pareto_front=pareto_front,
        hypervolume=hv,
        dominated_mask=dominated_mask,
        reference_point=reference_point,
    )


def get_pareto_visualization_data(
    approach_names: list[str],
    objectives: dict[str, npt.NDArray[np.float64]],
    reference_point: npt.NDArray[np.float64] | None = None,
) -> dict[str, Any]:
    """Prepare data for Pareto frontier visualization.

    Args:
        approach_names: List of approach names
        objectives: Dictionary mapping objective names to arrays
            e.g., {"quality": [...], "cost": [...], "speed": [...]}
        reference_point: Optional reference point for hypervolume

    Returns:
        Dictionary with visualization data including Pareto optimal approaches

    Raises:
        ValueError: If inputs are invalid (empty, mismatched lengths, etc.)
    """
    if not objectives:
        raise ValueError("objectives dictionary cannot be empty")
    if not approach_names:
        raise ValueError("approach_names list cannot be empty")

    # Stack objectives into array (n_approaches x n_objectives)
    objective_names = list(objectives.keys())
    objective_arrays = [objectives[name] for name in objective_names]

    # Validate all arrays have same length
    lengths = [len(arr) for arr in objective_arrays]
    if len(set(lengths)) > 1:
        raise ValueError(
            f"All objective arrays must have same length, "
            f"got {dict(zip(objective_names, lengths, strict=True))}"
        )

    # Validate matches approach names
    n_approaches = len(approach_names)
    if lengths[0] != n_approaches:
        raise ValueError(
            f"Number of approaches ({n_approaches}) must match "
            f"objective array length ({lengths[0]})"
        )

    objective_matrix = np.column_stack(objective_arrays)

    # Analyze Pareto frontier
    result = analyze_pareto_frontier(objective_matrix, reference_point)

    # Get Pareto optimal approach names
    pareto_approaches = [approach_names[i] for i in result.pareto_indices]

    return {
        "objective_names": objective_names,
        "objective_matrix": objective_matrix,
        "pareto_indices": result.pareto_indices,
        "pareto_front": result.pareto_front,
        "pareto_approaches": pareto_approaches,
        "dominated_mask": result.dominated_mask,
        "hypervolume": result.hypervolume,
        "reference_point": result.reference_point,
        "approach_names": approach_names,
    }
