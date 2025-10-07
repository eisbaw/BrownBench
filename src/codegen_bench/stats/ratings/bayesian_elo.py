"""Bayesian ELO rating system with uncertainty tracking."""

import math
from typing import Literal

# ELO Constants
# These values are from the original ELO chess rating system (Arpad Elo, 1960)
DEFAULT_RATING_MEAN = 1500.0  # Standard ELO starting rating (FIDE standard)
DEFAULT_RATING_STD = 200.0  # Initial uncertainty (chosen to give ~68% of players in 1300-1700 range)

# ELO Calculation Constants
# These define the logistic curve mapping rating differences to win probabilities
ELO_SCALE_FACTOR = 400.0  # Standard ELO scale factor (400 pts = 10x win probability)
ELO_BASE = 10.0  # Base for exponential in win probability (standard logistic curve)
K_FACTOR = 32.0  # Learning rate (FIDE uses 10-40 depending on rating; 32 is standard for established players)

# Bayesian Update Constants
# These control the Kalman filter-like update mechanism
PROCESS_NOISE = 5.0  # Uncertainty added per match (reflects skill variation over time)
MEASUREMENT_STD = 200.0  # Uncertainty in outcome measurement (same as initial std for symmetry)
CONFIDENCE_INTERVAL_SIGMA = 2.0  # 95% confidence interval (±2σ covers ~95% of normal distribution)


class BayesianELO:
    """ELO rating with Gaussian uncertainty.

    This is a simplified Bayesian version of ELO that tracks both
    the mean rating and standard deviation (uncertainty).
    """

    def __init__(
        self, prior_mean: float = DEFAULT_RATING_MEAN, prior_std: float = DEFAULT_RATING_STD
    ):
        """Initialize Bayesian ELO rating.

        Args:
            prior_mean: Initial rating mean
            prior_std: Initial rating standard deviation (uncertainty)
        """
        self.mean = prior_mean
        self.std = prior_std

    def update(self, opponent: "BayesianELO", result: Literal["win", "loss", "tie"]) -> None:
        """Update rating after a match.

        Args:
            opponent: Opponent's rating
            result: Match result ('win', 'loss', or 'tie')
        """
        # Expected win probability using logistic function
        expected = 1.0 / (1.0 + ELO_BASE ** ((opponent.mean - self.mean) / ELO_SCALE_FACTOR))

        # Actual outcome
        actual_map = {"win": 1.0, "loss": 0.0, "tie": 0.5}
        actual = actual_map[result]

        # Kalman filter-like update
        kalman_gain = (self.std**2) / (self.std**2 + MEASUREMENT_STD**2)

        # Update mean with K-factor weighted prediction error
        self.mean += kalman_gain * K_FACTOR * (actual - expected)

        # Update std (uncertainty decreases with more matches, process noise adds back some)
        self.std = math.sqrt((1.0 - kalman_gain) * self.std**2 + PROCESS_NOISE**2)

    def conservative_estimate(self) -> float:
        """Return conservative estimate (95% confidence lower bound).

        Returns:
            Rating minus 2 standard deviations
        """
        return self.mean - CONFIDENCE_INTERVAL_SIGMA * self.std

    def __str__(self) -> str:
        """String representation."""
        return f"BayesianELO(μ={self.mean:.1f}, σ={self.std:.1f})"

    def __repr__(self) -> str:
        """Repr representation."""
        return self.__str__()
