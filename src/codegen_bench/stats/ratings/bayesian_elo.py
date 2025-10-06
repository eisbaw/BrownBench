"""Bayesian ELO rating system with uncertainty tracking."""

import math
from typing import Literal


class BayesianELO:
    """ELO rating with Gaussian uncertainty.

    This is a simplified Bayesian version of ELO that tracks both
    the mean rating and standard deviation (uncertainty).
    """

    def __init__(self, prior_mean: float = 1500.0, prior_std: float = 200.0):
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
        # Expected win probability
        expected = 1.0 / (1.0 + 10 ** ((opponent.mean - self.mean) / 400.0))

        # Actual outcome
        actual_map = {"win": 1.0, "loss": 0.0, "tie": 0.5}
        actual = actual_map[result]

        # K-factor (learning rate)
        k = 32.0

        # Kalman filter-like update
        # Increase uncertainty slightly based on match variance
        process_noise = 5.0  # Small constant added to std each match
        measurement_std = 200.0  # Uncertainty in outcome measurement

        # Kalman gain
        kalman_gain = (self.std**2) / (self.std**2 + measurement_std**2)

        # Update mean
        self.mean += kalman_gain * k * (actual - expected)

        # Update std (uncertainty decreases with more matches)
        self.std = math.sqrt((1.0 - kalman_gain) * self.std**2 + process_noise**2)

    def conservative_estimate(self) -> float:
        """Return conservative estimate (95% confidence lower bound).

        Returns:
            Rating minus 2 standard deviations
        """
        return self.mean - 2.0 * self.std

    def __str__(self) -> str:
        """String representation."""
        return f"BayesianELO(μ={self.mean:.1f}, σ={self.std:.1f})"

    def __repr__(self) -> str:
        """Repr representation."""
        return self.__str__()
