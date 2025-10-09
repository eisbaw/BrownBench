"""Integration tests for TrueSkillConfig and TrueSkillRating."""

import pytest

from codegen_bench.core.config import TrueSkillConfig
from codegen_bench.stats.ratings.trueskill_rating import TrueSkillRating


def test_trueskill_with_custom_config_integration():
    """Test TrueSkillRating with custom configuration in a realistic scenario."""
    # Create a custom config for a high-variance environment
    config = TrueSkillConfig(
        initial_mu=30.0, initial_sigma=12.0, beta=6.0, tau=0.5, draw_probability=0.15
    )

    # Set as default config
    TrueSkillRating.set_default_config(config)

    # Create players - should use new default
    player1 = TrueSkillRating()
    player2 = TrueSkillRating()
    player3 = TrueSkillRating()

    assert player1.mu == 30.0
    assert player1.sigma == 12.0

    # Simulate a mini tournament
    # Player 1 beats Player 2
    player1.update(player2, "win")
    assert player1.mu > 30.0  # Winner's mu increases
    assert player2.mu < 30.0  # Loser's mu decreases
    assert player1.sigma < 12.0  # Both uncertainties decrease
    assert player2.sigma < 12.0

    # Player 2 beats Player 3
    initial_p2_mu = player2.mu
    player2.update(player3, "win")
    assert player2.mu > initial_p2_mu  # P2 recovers some rating

    # Player 1 ties with Player 3
    initial_p1_mu = player1.mu
    initial_p3_mu = player3.mu
    player1.update(player3, "tie")
    # In a tie, ratings converge
    assert abs(player1.mu - initial_p1_mu) < abs(initial_p1_mu - initial_p3_mu)

    # Check match quality predictions
    quality_1_2 = player1.match_quality(player2)
    quality_1_3 = player1.match_quality(player3)
    quality_2_3 = player2.match_quality(player3)

    # All should be between 0 and 1
    assert 0 <= quality_1_2 <= 1
    assert 0 <= quality_1_3 <= 1
    assert 0 <= quality_2_3 <= 1

    # Conservative estimates should be lower than mean
    assert player1.conservative_estimate() < player1.mu
    assert player2.conservative_estimate() < player2.mu
    assert player3.conservative_estimate() < player3.mu


def test_trueskill_rating_persistence():
    """Test that TrueSkillRating config persists across operations."""
    config = TrueSkillConfig(initial_mu=25.0, initial_sigma=8.0)

    # Create rating with explicit values and config
    rating = TrueSkillRating(mu=30.0, sigma=5.0, config=config)

    # Config should be preserved
    assert rating.config == config
    assert rating.mu == 30.0  # Explicit values override config defaults
    assert rating.sigma == 5.0

    # ELO conversion should use config's initial_mu
    expected_elo = 1500 + (30.0 - 25.0) * 20  # 1600
    assert abs(rating.elo_equivalent - expected_elo) < 1


def test_multiple_trueskill_configs():
    """Test using different configs for different rating pools."""
    # Config for competitive environment (low uncertainty)
    competitive_config = TrueSkillConfig(
        initial_mu=25.0,
        initial_sigma=4.0,
        tau=0.01,  # Very low skill drift
        draw_probability=0.05,
    )

    # Config for casual environment (high uncertainty)
    casual_config = TrueSkillConfig(
        initial_mu=25.0,
        initial_sigma=10.0,
        tau=0.5,  # High skill drift
        draw_probability=0.25,
    )

    # Create players in different pools
    competitive_player = TrueSkillRating(config=competitive_config)
    casual_player = TrueSkillRating(config=casual_config)

    assert competitive_player.sigma == 4.0
    assert casual_player.sigma == 10.0

    # Create opponents
    comp_opponent = TrueSkillRating(config=competitive_config)
    casual_opponent = TrueSkillRating(config=casual_config)

    # Simulate matches
    competitive_player.update(comp_opponent, "win")
    casual_player.update(casual_opponent, "win")

    # Competitive environment should have smaller rating changes
    # due to lower beta and sigma
    assert competitive_player.sigma < casual_player.sigma


def test_trueskill_round_robin_tournament():
    """Test TrueSkillRating in a round-robin tournament scenario."""
    # Use default config
    config = TrueSkillConfig()

    # Create 4 players with known skill levels
    # Simulate by giving them different starting ratings
    expert = TrueSkillRating(mu=35.0, sigma=3.0, config=config)
    intermediate1 = TrueSkillRating(mu=28.0, sigma=4.0, config=config)
    intermediate2 = TrueSkillRating(mu=27.0, sigma=4.0, config=config)
    beginner = TrueSkillRating(mu=20.0, sigma=5.0, config=config)

    players = {
        "expert": expert,
        "intermediate1": intermediate1,
        "intermediate2": intermediate2,
        "beginner": beginner,
    }

    # Simulate realistic tournament results
    matches = [
        ("expert", "intermediate1", "win"),
        ("expert", "intermediate2", "win"),
        ("expert", "beginner", "win"),
        ("intermediate1", "intermediate2", "win"),
        ("intermediate1", "beginner", "win"),
        ("intermediate2", "beginner", "win"),
    ]

    # Play matches
    for p1_name, p2_name, result in matches:
        p1 = players[p1_name]
        p2 = players[p2_name]
        p1.update(p2, result)

    # Check final rankings (by conservative estimate)
    rankings = sorted(players.items(), key=lambda x: x[1].conservative_estimate(), reverse=True)

    # Expert should still be highest
    assert rankings[0][0] == "expert"
    # Beginner should be lowest
    assert rankings[-1][0] == "beginner"

    # All uncertainties should have decreased
    assert expert.sigma < 3.0
    assert intermediate1.sigma < 4.0
    assert intermediate2.sigma < 4.0
    assert beginner.sigma < 5.0

    # Check match qualities
    # Expert vs beginner should have low quality (mismatch)
    expert_beginner_quality = expert.match_quality(beginner)
    # Intermediates should have high quality (close match)
    inter_quality = intermediate1.match_quality(intermediate2)

    assert expert_beginner_quality < inter_quality


def test_trueskill_elo_conversion():
    """Test ELO conversion with different configs."""
    # Config with non-standard initial_mu
    config1 = TrueSkillConfig(initial_mu=30.0)
    rating1 = TrueSkillRating(mu=35.0, config=config1)
    # ELO = 1500 + (35 - 30) * 20 = 1600
    assert abs(rating1.elo_equivalent - 1600) < 1

    # Config with standard initial_mu
    config2 = TrueSkillConfig(initial_mu=25.0)
    rating2 = TrueSkillRating(mu=35.0, config=config2)
    # ELO = 1500 + (35 - 25) * 20 = 1700
    assert abs(rating2.elo_equivalent - 1700) < 1

    # Same mu, different configs = different ELO
    assert abs(rating1.elo_equivalent - rating2.elo_equivalent) > 50
