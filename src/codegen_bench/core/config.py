"""Configuration dataclasses for tournament execution."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrueSkillConfig:
    """Configuration for TrueSkill rating system.

    TrueSkill is a Bayesian skill rating system that models player skill
    as a Gaussian distribution (μ, σ²).

    Attributes:
        initial_mu: Initial mean skill rating for new players.
                   Standard TrueSkill uses 25.0.
                   Default: 25.0
        initial_sigma: Initial uncertainty (standard deviation) for new players.
                      Standard TrueSkill uses 8.33 (roughly 1/3 of skill range).
                      Default: 8.33
        beta: Distance that guarantees about 76% chance of winning.
              Controls how much randomness affects match outcomes.
              Default: 4.17 (initial_sigma / 2)
        tau: Dynamics factor - additional uncertainty per game.
             Models skill drift over time. Use 0 for static skills.
             Default: 0.08333 (initial_sigma / 100)
        draw_probability: Expected probability of draws.
                         Affects how conservatively skills are updated.
                         Default: 0.1 (10% draws expected)

    Example:
        >>> config = TrueSkillConfig(initial_mu=30.0, initial_sigma=10.0)
        >>> config.initial_mu
        30.0
        >>> config.initial_sigma
        10.0

        # For environments with no draws:
        >>> no_draw_config = TrueSkillConfig(draw_probability=0.0)

        # For more volatile environments:
        >>> volatile_config = TrueSkillConfig(tau=0.5)
    """

    initial_mu: float = 25.0
    initial_sigma: float = 8.33
    beta: float | None = None  # Will default to initial_sigma / 2
    tau: float | None = None   # Will default to initial_sigma / 100
    draw_probability: float = 0.1

    def __post_init__(self) -> None:
        """Validate configuration and set defaults."""
        if self.initial_mu < 0:
            raise ValueError(f"initial_mu must be non-negative, got {self.initial_mu}")
        if self.initial_sigma <= 0:
            raise ValueError(f"initial_sigma must be positive, got {self.initial_sigma}")
        if self.draw_probability < 0 or self.draw_probability > 1:
            raise ValueError(f"draw_probability must be in [0, 1], got {self.draw_probability}")

        # Set defaults based on initial_sigma if not provided
        if self.beta is None:
            object.__setattr__(self, 'beta', self.initial_sigma / 2)
        elif self.beta <= 0:
            raise ValueError(f"beta must be positive, got {self.beta}")

        if self.tau is None:
            object.__setattr__(self, 'tau', self.initial_sigma / 100)
        elif self.tau < 0:
            raise ValueError(f"tau must be non-negative, got {self.tau}")


@dataclass(frozen=True)
class TournamentConfig:
    """Configuration for tournament execution.

    This dataclass consolidates tournament-level configuration parameters
    that were previously hardcoded or scattered across the codebase.

    Attributes:
        base_seed: Base seed for deterministic random number generation.
                  Sample seeds are derived as base_seed + sample_index.
                  Default: 42
        samples_per_pairing: Number of solution samples to generate per
                           (DUT, task) pairing. Higher values increase
                           statistical power but also increase cost.
                           Default: 3
        checkpoint_interval: Save checkpoint every N comparisons.
                           Default: 10

    Example:
        >>> config = TournamentConfig(base_seed=123, samples_per_pairing=5)
        >>> config.base_seed
        123
        >>> config.samples_per_pairing
        5

        # Immutable - this will fail:
        >>> config.base_seed = 456  # doctest: +SKIP
        FrozenInstanceError
    """

    base_seed: int = 42
    samples_per_pairing: int = 3
    checkpoint_interval: int = 10

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.base_seed < 0:
            raise ValueError(f"base_seed must be non-negative, got {self.base_seed}")
        if self.samples_per_pairing < 1:
            raise ValueError(f"samples_per_pairing must be >= 1, got {self.samples_per_pairing}")
        if self.checkpoint_interval < 1:
            raise ValueError(f"checkpoint_interval must be >= 1, got {self.checkpoint_interval}")
