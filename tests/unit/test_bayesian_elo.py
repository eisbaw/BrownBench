"""Tests for Bayesian ELO rating system."""

import pytest

from codegen_bench.stats.ratings.bayesian_elo import BayesianELO


def test_bayesian_elo_init():
    """Test initialization."""
    rating = BayesianELO()
    assert rating.mean == 1500.0
    assert rating.std == 200.0


def test_bayesian_elo_init_custom():
    """Test initialization with custom parameters."""
    rating = BayesianELO(prior_mean=1600.0, prior_std=150.0)
    assert rating.mean == 1600.0
    assert rating.std == 150.0


def test_bayesian_elo_update_win():
    """Test rating update after a win."""
    rating_a = BayesianELO()
    rating_b = BayesianELO()

    initial_mean = rating_a.mean

    rating_a.update(rating_b, "win")

    # Winner's rating should increase
    assert rating_a.mean > initial_mean
    # Uncertainty should decrease (slightly)
    assert rating_a.std < 200.0


def test_bayesian_elo_update_loss():
    """Test rating update after a loss."""
    rating_a = BayesianELO()
    rating_b = BayesianELO()

    initial_mean = rating_a.mean

    rating_a.update(rating_b, "loss")

    # Loser's rating should decrease
    assert rating_a.mean < initial_mean


def test_bayesian_elo_update_tie():
    """Test rating update after a tie."""
    rating_a = BayesianELO()
    rating_b = BayesianELO()

    initial_mean_a = rating_a.mean

    rating_a.update(rating_b, "tie")

    # Against equal opponent, tie shouldn't change much
    assert abs(rating_a.mean - initial_mean_a) < 1.0


def test_bayesian_elo_stronger_beats_weaker():
    """Test that stronger player beating weaker gains less."""
    strong = BayesianELO(prior_mean=1800.0, prior_std=100.0)
    weak = BayesianELO(prior_mean=1200.0, prior_std=100.0)

    initial_strong = strong.mean

    strong.update(weak, "win")

    # Strong player should gain very little
    gain = strong.mean - initial_strong
    assert 0 < gain < 5.0  # Small gain expected


def test_bayesian_elo_weaker_beats_stronger():
    """Test that weaker player beating stronger gains more."""
    strong = BayesianELO(prior_mean=1800.0, prior_std=100.0)
    weak = BayesianELO(prior_mean=1200.0, prior_std=100.0)

    initial_weak = weak.mean

    weak.update(strong, "win")

    # Weak player should gain something (upset victory)
    gain = weak.mean - initial_weak
    assert gain > 5.0  # Expect notable gain


def test_bayesian_elo_conservative_estimate():
    """Test conservative estimate calculation."""
    rating = BayesianELO(prior_mean=1600.0, prior_std=100.0)

    conservative = rating.conservative_estimate()

    # Should be mean - 2*std
    assert conservative == pytest.approx(1600.0 - 2 * 100.0)
    assert conservative == pytest.approx(1400.0)


def test_bayesian_elo_uncertainty_decreases():
    """Test that uncertainty decreases with matches."""
    rating_a = BayesianELO()
    rating_b = BayesianELO()

    initial_std = rating_a.std

    # Play several matches
    for _ in range(10):
        rating_a.update(rating_b, "win")

    # Uncertainty should decrease (though process noise adds some back)
    assert rating_a.std < initial_std


def test_bayesian_elo_string_representation():
    """Test string representation."""
    rating = BayesianELO(prior_mean=1550.5, prior_std=125.3)

    str_repr = str(rating)
    assert "1550.5" in str_repr
    assert "125.3" in str_repr
    assert "BayesianELO" in str_repr


def test_bayesian_elo_symmetry():
    """Test that wins and losses are symmetric."""
    rating_a = BayesianELO(prior_mean=1500.0, prior_std=100.0)
    rating_b = BayesianELO(prior_mean=1500.0, prior_std=100.0)

    # A wins
    initial_a = rating_a.mean

    rating_a.update(rating_b, "win")
    a_gain = rating_a.mean - initial_a

    # Reset
    rating_a.mean = initial_a
    rating_a.std = 100.0

    # A loses (equivalent to B winning)
    rating_a.update(rating_b, "loss")
    a_loss = initial_a - rating_a.mean

    # Gain and loss should be similar magnitude
    assert abs(a_gain - a_loss) < 0.1
