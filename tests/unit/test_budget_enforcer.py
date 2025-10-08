"""Tests for budget enforcement."""

import threading

import pytest

from codegen_bench.budget import BudgetConfig, BudgetEnforcer, BudgetStatus
from codegen_bench.budget.enforcer import BudgetExceededError


def test_budget_config_creation():
    """Test creating budget configuration."""
    config = BudgetConfig(global_limit=100.0, per_dut_limit=20.0, warning_threshold=0.8)

    assert config.global_limit == 100.0
    assert config.per_dut_limit == 20.0
    assert config.warning_threshold == 0.8


def test_budget_config_validation():
    """Test budget config validation."""
    # Warning threshold out of range
    with pytest.raises(ValueError, match="warning_threshold must be 0-1"):
        BudgetConfig(warning_threshold=1.5)

    with pytest.raises(ValueError, match="warning_threshold must be 0-1"):
        BudgetConfig(warning_threshold=-0.1)

    # Negative limits
    with pytest.raises(ValueError, match="global_limit must be positive"):
        BudgetConfig(global_limit=-10.0)

    with pytest.raises(ValueError, match="per_dut_limit must be positive"):
        BudgetConfig(per_dut_limit=-5.0)


def test_budget_enforcer_no_limits():
    """Test budget enforcer with no limits."""
    config = BudgetConfig()  # No limits
    enforcer = BudgetEnforcer(config)

    # Should accept any costs
    enforcer.record_cost("dut1", 100.0)
    enforcer.record_cost("dut2", 200.0)

    assert enforcer.get_total_cost() == 300.0
    assert enforcer.get_dut_cost("dut1") == 100.0
    assert enforcer.get_dut_cost("dut2") == 200.0


def test_record_cost_basic():
    """Test basic cost recording."""
    config = BudgetConfig(global_limit=100.0)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 10.0)
    enforcer.record_cost("dut1", 5.0)
    enforcer.record_cost("dut2", 20.0)

    assert enforcer.get_total_cost() == 35.0
    assert enforcer.get_dut_cost("dut1") == 15.0
    assert enforcer.get_dut_cost("dut2") == 20.0


def test_global_limit_exceeded():
    """Test global budget limit enforcement."""
    config = BudgetConfig(global_limit=50.0)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 30.0)
    enforcer.record_cost("dut2", 15.0)

    # This should exceed the limit
    with pytest.raises(BudgetExceededError, match="Global budget exceeded"):
        enforcer.record_cost("dut3", 10.0)

    # Total should not include the rejected cost
    assert enforcer.get_total_cost() == 45.0


def test_per_dut_limit_exceeded():
    """Test per-DUT budget limit enforcement."""
    config = BudgetConfig(per_dut_limit=20.0)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 15.0)
    enforcer.record_cost("dut2", 10.0)

    # This should exceed per-DUT limit
    with pytest.raises(BudgetExceededError, match="Per-DUT budget exceeded"):
        enforcer.record_cost("dut1", 10.0)

    # dut1 should not include rejected cost
    assert enforcer.get_dut_cost("dut1") == 15.0


def test_check_budget_ok():
    """Test budget check when well within limits."""
    config = BudgetConfig(global_limit=100.0, per_dut_limit=30.0)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 10.0)

    status = enforcer.check_budget("dut1", estimated_cost=5.0)
    assert status == BudgetStatus.OK


def test_check_budget_warning():
    """Test budget check triggers warning near limit."""
    config = BudgetConfig(global_limit=100.0, warning_threshold=0.8)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 70.0)

    # Adding 15 would bring us to 85 (85% of limit)
    status = enforcer.check_budget("dut1", estimated_cost=15.0)
    assert status == BudgetStatus.WARNING


def test_check_budget_would_exceed():
    """Test budget check raises error if operation would exceed."""
    config = BudgetConfig(global_limit=100.0)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 90.0)

    with pytest.raises(BudgetExceededError, match="would exceed global budget"):
        enforcer.check_budget("dut2", estimated_cost=20.0)


def test_get_all_dut_costs():
    """Test getting all DUT costs."""
    config = BudgetConfig()
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 10.0)
    enforcer.record_cost("dut2", 20.0)
    enforcer.record_cost("dut3", 15.0)

    costs = enforcer.get_all_dut_costs()
    assert costs == {"dut1": 10.0, "dut2": 20.0, "dut3": 15.0}


def test_get_remaining_budget():
    """Test getting remaining budget."""
    config = BudgetConfig(global_limit=100.0, per_dut_limit=30.0)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 25.0)
    enforcer.record_cost("dut2", 20.0)

    global_remaining, per_dut_remaining = enforcer.get_remaining_budget()

    assert global_remaining == 55.0  # 100 - 45
    assert per_dut_remaining == 5.0  # 30 - 25 (dut1 highest)


def test_get_remaining_budget_no_limits():
    """Test getting remaining budget when no limits set."""
    config = BudgetConfig()
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 50.0)

    global_remaining, per_dut_remaining = enforcer.get_remaining_budget()

    assert global_remaining is None
    assert per_dut_remaining is None


def test_reset():
    """Test resetting budget enforcer."""
    config = BudgetConfig(global_limit=100.0)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 30.0)
    enforcer.record_cost("dut2", 20.0)

    assert enforcer.get_total_cost() == 50.0

    enforcer.reset()

    assert enforcer.get_total_cost() == 0.0
    assert enforcer.get_all_dut_costs() == {}


def test_record_negative_cost_raises():
    """Test that negative costs are rejected."""
    config = BudgetConfig()
    enforcer = BudgetEnforcer(config)

    with pytest.raises(ValueError, match="Cost must be non-negative"):
        enforcer.record_cost("dut1", -10.0)


def test_thread_safety():
    """Test thread-safe cost recording."""
    config = BudgetConfig(global_limit=1000.0)
    enforcer = BudgetEnforcer(config)

    def record_costs(dut_id: str, num_operations: int):
        for _ in range(num_operations):
            enforcer.record_cost(dut_id, 1.0)

    # Create multiple threads recording costs concurrently
    threads = []
    for i in range(5):
        thread = threading.Thread(target=record_costs, args=(f"dut{i}", 20))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Total should be exactly 100 (5 DUTs * 20 operations * $1)
    assert enforcer.get_total_cost() == 100.0

    # Each DUT should have $20
    for i in range(5):
        assert enforcer.get_dut_cost(f"dut{i}") == 20.0


def test_per_dut_warning_threshold():
    """Test per-DUT warning threshold."""
    config = BudgetConfig(per_dut_limit=100.0, warning_threshold=0.9)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 85.0)

    # Adding 6 would bring dut1 to 91 (91% of limit)
    status = enforcer.check_budget("dut1", estimated_cost=6.0)
    assert status == BudgetStatus.WARNING


def test_check_budget_without_dut_id():
    """Test budget check with only global limit."""
    config = BudgetConfig(global_limit=100.0, warning_threshold=0.8)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 70.0)

    # Check without DUT ID (global only)
    status = enforcer.check_budget(dut_id=None, estimated_cost=15.0)
    assert status == BudgetStatus.WARNING


def test_get_dut_cost_unknown_dut():
    """Test getting cost for unknown DUT returns 0."""
    config = BudgetConfig()
    enforcer = BudgetEnforcer(config)

    assert enforcer.get_dut_cost("unknown_dut") == 0.0


def test_both_limits_enforced():
    """Test that both global and per-DUT limits are enforced."""
    config = BudgetConfig(global_limit=100.0, per_dut_limit=30.0)
    enforcer = BudgetEnforcer(config)

    # Record costs within limits
    enforcer.record_cost("dut1", 25.0)
    enforcer.record_cost("dut2", 25.0)
    enforcer.record_cost("dut3", 25.0)

    # Try to exceed per-DUT limit
    with pytest.raises(BudgetExceededError, match="Per-DUT budget exceeded"):
        enforcer.record_cost("dut1", 10.0)

    # Try to exceed global limit
    with pytest.raises(BudgetExceededError, match="Global budget exceeded"):
        enforcer.record_cost("dut4", 30.0)


def test_warning_threshold_boundaries():
    """Test warning threshold at exact boundaries."""
    config = BudgetConfig(global_limit=100.0, warning_threshold=0.8)
    enforcer = BudgetEnforcer(config)

    enforcer.record_cost("dut1", 79.9)
    status = enforcer.check_budget("dut1", estimated_cost=0.0)
    assert status == BudgetStatus.OK

    # At exactly 80%, should trigger warning
    enforcer.record_cost("dut1", 0.1)
    status = enforcer.check_budget("dut1", estimated_cost=0.0)
    assert status == BudgetStatus.WARNING
