"""TrueSkill rating system with uncertainty quantification.

TrueSkill is a Bayesian rating system developed by Microsoft Research.
It models player skill as a Gaussian distribution (μ, σ²).

Key advantages over ELO:
- Tracks uncertainty (σ) which decreases with more matches
- Supports multi-player matches (not just 1v1)
- Provides match quality predictions

References:
- Herbrich et al. (2006): "TrueSkill: A Bayesian Skill Rating System"
"""

from typing import Literal

import trueskill
from trueskill import Rating, quality, rate

from codegen_bench.core.config import TrueSkillConfig


class TrueSkillRating:
    """TrueSkill rating wrapper with uncertainty tracking.

    Attributes:
        rating: TrueSkill Rating object (μ, σ)
        config: TrueSkill configuration
    """

    # Class-level default config (can be overridden per instance)
    _default_config = TrueSkillConfig()

    @classmethod
    def set_default_config(cls, config: TrueSkillConfig) -> None:
        """Set the default configuration for new TrueSkillRating instances.

        Args:
            config: TrueSkillConfig to use as default
        """
        cls._default_config = config
        # Also configure the underlying trueskill library globals
        trueskill.setup(
            mu=config.initial_mu,
            sigma=config.initial_sigma,
            beta=config.beta,
            tau=config.tau,
            draw_probability=config.draw_probability
        )

    def __init__(
        self,
        mu: float | None = None,
        sigma: float | None = None,
        config: TrueSkillConfig | None = None
    ) -> None:
        """Initialize TrueSkill rating.

        Args:
            mu: Mean skill estimate (uses config default if None)
            sigma: Skill uncertainty (uses config default if None)
            config: TrueSkillConfig to use (uses class default if None)
        """
        self.config = config or self._default_config

        # Use provided values or fall back to config defaults
        if mu is None:
            mu = self.config.initial_mu
        if sigma is None:
            sigma = self.config.initial_sigma

        self.rating = Rating(mu, sigma)

    def update(self, opponent: "TrueSkillRating", outcome: Literal["win", "loss", "tie"]) -> None:
        """Update rating after a match.

        Args:
            opponent: Opponent's rating
            outcome: Match result ('win', 'loss', 'tie')
        """
        # Convert outcome to ranks (0 is best)
        if outcome == "win":
            ranks = [0, 1]  # self wins
        elif outcome == "loss":
            ranks = [1, 0]  # opponent wins
        else:  # tie
            ranks = [0, 0]  # equal ranks

        # Update both ratings
        new_ratings = rate([[self.rating], [opponent.rating]], ranks=ranks)
        self.rating = new_ratings[0][0]
        opponent.rating = new_ratings[1][0]

    def conservative_estimate(self) -> float:
        """Conservative skill estimate (95% confidence lower bound).

        Returns:
            μ - 2σ (approximately 95% confidence interval lower bound)
        """
        return float(self.rating.mu - 2 * self.rating.sigma)

    def match_quality(self, opponent: "TrueSkillRating") -> float:
        """Predict match quality (0-1, higher = more informative).

        A value close to 1 means evenly matched players,
        providing maximum information about true skill.

        Args:
            opponent: Opponent's rating

        Returns:
            Match quality between 0 and 1
        """
        return float(quality([[self.rating], [opponent.rating]]))

    @property
    def mu(self) -> float:
        """Mean skill estimate."""
        return float(self.rating.mu)

    @property
    def sigma(self) -> float:
        """Skill uncertainty."""
        return float(self.rating.sigma)

    @property
    def elo_equivalent(self) -> float:
        """Convert to approximate ELO rating.

        TrueSkill default: μ=25, σ=8.33
        ELO range: typically 1000-2000

        Conversion: ELO ≈ 1500 + (μ - initial_mu) * 20
        """
        return 1500 + (self.mu - self.config.initial_mu) * 20

    def __str__(self) -> str:
        """String representation."""
        return f"TrueSkill(μ={self.mu:.1f}, σ={self.sigma:.1f}, conservative={self.conservative_estimate():.1f})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"TrueSkillRating(mu={self.mu}, sigma={self.sigma})"
