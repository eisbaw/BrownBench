"""Tests for TrueSkill rating system."""

import pytest

from codegen_bench.stats.ratings.trueskill_rating import TrueSkillRating


def test_trueskill_init() -> None:
    """Test default initialization."""
    rating = TrueSkillRating()
    assert rating.mu == pytest.approx(25.0, abs=0.01)
    assert rating.sigma == pytest.approx(8.33, abs=0.01)
    assert rating.elo_equivalent == pytest.approx(1500, abs=1)


def test_trueskill_init_custom() -> None:
    """Test custom initialization."""
    rating = TrueSkillRating(mu=30.0, sigma=5.0)
    assert rating.mu == 30.0
    assert rating.sigma == 5.0
    assert rating.elo_equivalent == pytest.approx(1500 + 5 * 20, abs=1)


def test_trueskill_update_win() -> None:
    """Test rating update after win."""
    player_a = TrueSkillRating()
    player_b = TrueSkillRating()

    initial_mu_a = player_a.mu

    player_a.update(player_b, "win")

    # Winner's μ should increase
    assert player_a.mu > initial_mu_a
    # Loser's μ should decrease
    assert player_b.mu < 25.0
    # Both uncertainties should decrease
    assert player_a.sigma < 8.33
    assert player_b.sigma < 8.33


def test_trueskill_update_loss() -> None:
    """Test rating update after loss."""
    player_a = TrueSkillRating()
    player_b = TrueSkillRating()

    initial_mu_a = player_a.mu

    player_a.update(player_b, "loss")

    # Loser's μ should decrease
    assert player_a.mu < initial_mu_a
    # Winner's μ should increase
    assert player_b.mu > 25.0


def test_trueskill_update_tie() -> None:
    """Test rating update after tie."""
    player_a = TrueSkillRating(mu=30.0)
    player_b = TrueSkillRating(mu=20.0)

    initial_mu_a = player_a.mu
    initial_mu_b = player_b.mu

    player_a.update(player_b, "tie")

    # Higher rated player's μ should decrease (expected to win)
    assert player_a.mu < initial_mu_a
    # Lower rated player's μ should increase (expected to lose)
    assert player_b.mu > initial_mu_b
    # Uncertainties decrease
    assert player_a.sigma < 8.33
    assert player_b.sigma < 8.33


def test_trueskill_stronger_beats_weaker() -> None:
    """Test that stronger player beats weaker player as expected."""
    strong = TrueSkillRating(mu=30.0, sigma=3.0)
    weak = TrueSkillRating(mu=20.0, sigma=3.0)

    initial_strong_mu = strong.mu
    initial_weak_mu = weak.mu

    strong.update(weak, "win")

    # Strong player gains some μ (less than if it were an upset)
    # Weak player loses some μ
    # Rating changes are symmetric when σ is equal
    assert strong.mu > initial_strong_mu
    assert weak.mu < initial_weak_mu
    assert abs(strong.mu - initial_strong_mu) == pytest.approx(
        abs(weak.mu - initial_weak_mu), abs=0.01
    )


def test_trueskill_weaker_beats_stronger() -> None:
    """Test upset: weaker player beats stronger player."""
    strong = TrueSkillRating(mu=30.0, sigma=3.0)
    weak = TrueSkillRating(mu=20.0, sigma=3.0)

    initial_weak_mu = weak.mu
    initial_strong_mu = strong.mu

    weak.update(strong, "win")

    # Weak player gains μ
    # Strong player loses μ
    # Rating changes are symmetric when σ is equal
    assert weak.mu > initial_weak_mu
    assert strong.mu < initial_strong_mu
    assert abs(weak.mu - initial_weak_mu) == pytest.approx(
        abs(strong.mu - initial_strong_mu), abs=0.01
    )
    # Verify significant change (upset)
    assert weak.mu > initial_weak_mu + 1.0
    assert strong.mu < initial_strong_mu - 1.0


def test_trueskill_conservative_estimate() -> None:
    """Test conservative skill estimate."""
    rating = TrueSkillRating(mu=25.0, sigma=5.0)
    conservative = rating.conservative_estimate()

    # Should be μ - 2σ
    assert conservative == pytest.approx(25.0 - 2 * 5.0, abs=0.01)
    assert conservative == 15.0


def test_trueskill_uncertainty_decreases() -> None:
    """Test that uncertainty decreases with matches."""
    player_a = TrueSkillRating()
    player_b = TrueSkillRating()

    initial_sigma_a = player_a.sigma

    # Play multiple matches
    for _ in range(10):
        player_a.update(player_b, "win")

    # Uncertainty should decrease significantly
    assert player_a.sigma < initial_sigma_a
    assert player_a.sigma < 5.0  # Should converge


def test_trueskill_match_quality() -> None:
    """Test match quality prediction."""
    player_a = TrueSkillRating(mu=25.0, sigma=3.0)
    player_b = TrueSkillRating(mu=25.0, sigma=3.0)

    # Evenly matched players = high quality
    quality = player_a.match_quality(player_b)
    assert quality > 0.5
    assert quality <= 1.0


def test_trueskill_match_quality_mismatch() -> None:
    """Test match quality for mismatched players."""
    strong = TrueSkillRating(mu=35.0, sigma=3.0)
    weak = TrueSkillRating(mu=15.0, sigma=3.0)

    # Mismatched players = lower quality
    quality = strong.match_quality(weak)
    assert quality < 0.5


def test_trueskill_elo_conversion() -> None:
    """Test conversion to approximate ELO."""
    rating = TrueSkillRating(mu=30.0, sigma=5.0)

    # μ=30 -> ELO ≈ 1500 + (30-25)*20 = 1600
    assert rating.elo_equivalent == pytest.approx(1600, abs=1)

    rating_low = TrueSkillRating(mu=20.0, sigma=5.0)
    # μ=20 -> ELO ≈ 1500 + (20-25)*20 = 1400
    assert rating_low.elo_equivalent == pytest.approx(1400, abs=1)


def test_trueskill_string_representation() -> None:
    """Test string representation."""
    rating = TrueSkillRating(mu=25.0, sigma=5.0)
    s = str(rating)

    assert "TrueSkill" in s
    assert "25.0" in s
    assert "5.0" in s
    assert "conservative" in s


def test_trueskill_repr() -> None:
    """Test detailed representation."""
    rating = TrueSkillRating(mu=25.0, sigma=5.0)
    r = repr(rating)

    assert "TrueSkillRating" in r
    assert "mu=25.0" in r
    assert "sigma=5.0" in r


def test_trueskill_symmetry() -> None:
    """Test that win/loss are symmetric."""
    player_a1 = TrueSkillRating()
    player_b1 = TrueSkillRating()

    player_a2 = TrueSkillRating()
    player_b2 = TrueSkillRating()

    # A wins vs B
    player_a1.update(player_b1, "win")

    # B loses to A (same as above)
    player_b2.update(player_a2, "loss")

    # Results should be identical
    assert player_a1.mu == pytest.approx(player_a2.mu, abs=0.01)
    assert player_b1.mu == pytest.approx(player_b2.mu, abs=0.01)
    assert player_a1.sigma == pytest.approx(player_a2.sigma, abs=0.01)
    assert player_b1.sigma == pytest.approx(player_b2.sigma, abs=0.01)


def test_trueskill_properties() -> None:
    """Test property accessors."""
    rating = TrueSkillRating(mu=27.5, sigma=6.2)

    assert rating.mu == 27.5
    assert rating.sigma == 6.2
    assert rating.conservative_estimate() == pytest.approx(27.5 - 2 * 6.2, abs=0.01)
