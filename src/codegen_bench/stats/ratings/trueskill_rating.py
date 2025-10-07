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

from trueskill import Rating, rate, quality


class TrueSkillRating:
    """TrueSkill rating wrapper with uncertainty tracking.

    Attributes:
        rating: TrueSkill Rating object (μ, σ)
    """

    # Default TrueSkill parameters
    DEFAULT_MU = 25.0  # Initial mean skill
    DEFAULT_SIGMA = 8.33  # Initial uncertainty (1/3 of skill range)

    def __init__(self, mu: float = DEFAULT_MU, sigma: float = DEFAULT_SIGMA) -> None:
        """Initialize TrueSkill rating.

        Args:
            mu: Mean skill estimate (default: 25.0)
            sigma: Skill uncertainty (default: 8.33)
        """
        self.rating = Rating(mu, sigma)

    def update(
        self, opponent: "TrueSkillRating", outcome: Literal["win", "loss", "tie"]
    ) -> None:
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
        return self.rating.mu - 2 * self.rating.sigma

    def match_quality(self, opponent: "TrueSkillRating") -> float:
        """Predict match quality (0-1, higher = more informative).

        A value close to 1 means evenly matched players,
        providing maximum information about true skill.

        Args:
            opponent: Opponent's rating

        Returns:
            Match quality between 0 and 1
        """
        return quality([[self.rating], [opponent.rating]])

    @property
    def mu(self) -> float:
        """Mean skill estimate."""
        return self.rating.mu

    @property
    def sigma(self) -> float:
        """Skill uncertainty."""
        return self.rating.sigma

    @property
    def elo_equivalent(self) -> float:
        """Convert to approximate ELO rating.

        TrueSkill default: μ=25, σ=8.33
        ELO range: typically 1000-2000

        Conversion: ELO ≈ 1500 + (μ - 25) * 20
        """
        return 1500 + (self.mu - self.DEFAULT_MU) * 20

    def __str__(self) -> str:
        """String representation."""
        return f"TrueSkill(μ={self.mu:.1f}, σ={self.sigma:.1f}, conservative={self.conservative_estimate():.1f})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"TrueSkillRating(mu={self.mu}, sigma={self.sigma})"
