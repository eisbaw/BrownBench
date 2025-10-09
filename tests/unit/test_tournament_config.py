"""Unit tests for TournamentConfig and TrueSkillConfig dataclasses."""

import pytest

from codegen_bench.core.config import TournamentConfig, TrueSkillConfig
from codegen_bench.stats.ratings.trueskill_rating import TrueSkillRating


def test_tournament_config_defaults():
    """Test default configuration values."""
    config = TournamentConfig()
    assert config.base_seed == 42
    assert config.samples_per_pairing == 3
    assert config.checkpoint_interval == 10


def test_tournament_config_custom_values():
    """Test custom configuration values."""
    config = TournamentConfig(
        base_seed=123,
        samples_per_pairing=5,
        checkpoint_interval=20,
    )
    assert config.base_seed == 123
    assert config.samples_per_pairing == 5
    assert config.checkpoint_interval == 20


def test_tournament_config_immutable():
    """Test that TournamentConfig is immutable (frozen)."""
    config = TournamentConfig()
    with pytest.raises(AttributeError):
        config.base_seed = 999  # type: ignore[misc]


def test_tournament_config_negative_base_seed():
    """Test validation: base_seed must be non-negative."""
    with pytest.raises(ValueError, match="base_seed must be non-negative"):
        TournamentConfig(base_seed=-1)


def test_tournament_config_zero_samples():
    """Test validation: samples_per_pairing must be >= 1."""
    with pytest.raises(ValueError, match="samples_per_pairing must be >= 1"):
        TournamentConfig(samples_per_pairing=0)


def test_tournament_config_negative_samples():
    """Test validation: samples_per_pairing must be >= 1."""
    with pytest.raises(ValueError, match="samples_per_pairing must be >= 1"):
        TournamentConfig(samples_per_pairing=-5)


def test_tournament_config_invalid_checkpoint_interval():
    """Test validation: checkpoint_interval must be >= 1."""
    with pytest.raises(ValueError, match="checkpoint_interval must be >= 1"):
        TournamentConfig(checkpoint_interval=0)


def test_tournament_config_boundary_values():
    """Test configuration with boundary values."""
    # Minimum valid values
    config_min = TournamentConfig(
        base_seed=0,
        samples_per_pairing=1,
        checkpoint_interval=1,
    )
    assert config_min.base_seed == 0
    assert config_min.samples_per_pairing == 1
    assert config_min.checkpoint_interval == 1


def test_tournament_config_large_values():
    """Test configuration with large values."""
    config = TournamentConfig(
        base_seed=999999,
        samples_per_pairing=100,
        checkpoint_interval=1000,
    )
    assert config.base_seed == 999999
    assert config.samples_per_pairing == 100
    assert config.checkpoint_interval == 1000


# Tests for TrueSkillConfig


def test_trueskill_config_defaults():
    """Test default TrueSkillConfig values."""
    config = TrueSkillConfig()
    assert config.initial_mu == 25.0
    assert config.initial_sigma == 8.33
    assert config.beta == pytest.approx(8.33 / 2, abs=0.01)
    assert config.tau == pytest.approx(8.33 / 100, abs=0.001)
    assert config.draw_probability == 0.1


def test_trueskill_config_custom_values():
    """Test custom TrueSkillConfig values."""
    config = TrueSkillConfig(
        initial_mu=30.0, initial_sigma=10.0, beta=5.0, tau=0.1, draw_probability=0.05
    )
    assert config.initial_mu == 30.0
    assert config.initial_sigma == 10.0
    assert config.beta == 5.0
    assert config.tau == 0.1
    assert config.draw_probability == 0.05


def test_trueskill_config_auto_beta_tau():
    """Test that beta and tau are auto-calculated from sigma."""
    config = TrueSkillConfig(initial_sigma=10.0)
    assert config.beta == pytest.approx(5.0, abs=0.01)  # sigma / 2
    assert config.tau == pytest.approx(0.1, abs=0.001)  # sigma / 100


def test_trueskill_config_immutable():
    """Test that TrueSkillConfig is immutable."""
    config = TrueSkillConfig()
    with pytest.raises(AttributeError):
        config.initial_mu = 30.0  # type: ignore[misc]


def test_trueskill_config_validation_negative_mu():
    """Test validation for negative mu."""
    with pytest.raises(ValueError, match="initial_mu must be non-negative"):
        TrueSkillConfig(initial_mu=-1.0)


def test_trueskill_config_validation_invalid_sigma():
    """Test validation for zero/negative sigma."""
    with pytest.raises(ValueError, match="initial_sigma must be positive"):
        TrueSkillConfig(initial_sigma=0.0)

    with pytest.raises(ValueError, match="initial_sigma must be positive"):
        TrueSkillConfig(initial_sigma=-1.0)


def test_trueskill_config_validation_invalid_draw_probability():
    """Test validation for invalid draw probability."""
    with pytest.raises(ValueError, match="draw_probability must be in"):
        TrueSkillConfig(draw_probability=-0.1)

    with pytest.raises(ValueError, match="draw_probability must be in"):
        TrueSkillConfig(draw_probability=1.1)


def test_trueskill_config_validation_invalid_beta():
    """Test validation for invalid beta."""
    with pytest.raises(ValueError, match="beta must be positive"):
        TrueSkillConfig(beta=0.0)

    with pytest.raises(ValueError, match="beta must be positive"):
        TrueSkillConfig(beta=-1.0)


def test_trueskill_config_validation_invalid_tau():
    """Test validation for invalid tau."""
    with pytest.raises(ValueError, match="tau must be non-negative"):
        TrueSkillConfig(tau=-0.1)


def test_trueskill_rating_with_config():
    """Test TrueSkillRating uses provided config."""
    config = TrueSkillConfig(initial_mu=30.0, initial_sigma=10.0)
    rating = TrueSkillRating(config=config)

    assert rating.mu == 30.0
    assert rating.sigma == 10.0
    assert rating.config == config


def test_trueskill_rating_config_override():
    """Test TrueSkillRating with both config and explicit values."""
    config = TrueSkillConfig(initial_mu=30.0, initial_sigma=10.0)
    # Explicit values should override config
    rating = TrueSkillRating(mu=25.0, sigma=5.0, config=config)

    assert rating.mu == 25.0
    assert rating.sigma == 5.0
    assert rating.config == config


def test_trueskill_rating_default_config():
    """Test TrueSkillRating.set_default_config class method."""
    # Save original config
    original_config = TrueSkillRating._default_config

    try:
        # Set new default
        new_config = TrueSkillConfig(initial_mu=35.0, initial_sigma=12.0)
        TrueSkillRating.set_default_config(new_config)

        # New instances should use new default
        rating = TrueSkillRating()
        assert rating.mu == 35.0
        assert rating.sigma == 12.0

    finally:
        # Restore original config
        TrueSkillRating.set_default_config(original_config)


def test_trueskill_elo_conversion_with_config():
    """Test ELO conversion uses config's initial_mu."""
    config = TrueSkillConfig(initial_mu=30.0)
    rating = TrueSkillRating(mu=35.0, config=config)

    # ELO = 1500 + (35 - 30) * 20 = 1600
    assert rating.elo_equivalent == pytest.approx(1600, abs=1)
