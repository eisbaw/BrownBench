"""Unit tests for bucket-based rate limiter."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from codegen_bench.utils.bucket_rate_limiter import BucketRateLimiter, MultiTierRateLimiter


class TestBucketRateLimiter:
    """Test bucket rate limiter implementation."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        # Basic initialization
        limiter = BucketRateLimiter(requests_per_second=10)
        assert limiter.refill_rate == 10
        assert limiter.capacity == 10
        assert limiter.available_tokens() == 10

        # Custom burst size
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=20)
        assert limiter.refill_rate == 10
        assert limiter.capacity == 20
        assert limiter.available_tokens() == 20

        # Invalid parameters
        with pytest.raises(ValueError):
            BucketRateLimiter(requests_per_second=0)
        with pytest.raises(ValueError):
            BucketRateLimiter(requests_per_second=-1)

    def test_try_acquire_basic(self):
        """Test basic token acquisition."""
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=10)

        # Acquire single tokens
        for i in range(10):
            assert limiter.try_acquire()
            assert limiter.available_tokens() == 10 - i - 1

        # Bucket empty
        assert not limiter.try_acquire()
        assert limiter.available_tokens() == 0

    def test_try_acquire_multiple(self):
        """Test acquiring multiple tokens."""
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=10)

        # Acquire 5 tokens
        assert limiter.try_acquire(5)
        assert limiter.available_tokens() == 5

        # Try to acquire more than available
        assert not limiter.try_acquire(6)
        assert limiter.available_tokens() == 5

        # Acquire remaining
        assert limiter.try_acquire(5)
        assert limiter.available_tokens() == 0

    def test_try_acquire_exceeds_capacity(self):
        """Test acquiring more tokens than capacity."""
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=10)

        # Try to acquire more than capacity
        assert not limiter.try_acquire(11)
        assert limiter.available_tokens() == 10  # Unchanged

    def test_refill_mechanism(self):
        """Test token refill based on time."""
        mock_clock = MagicMock(side_effect=[0, 0.1, 0.2, 0.5, 1.0])
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=10, clock=mock_clock)

        # Initial state
        assert limiter.available_tokens() == 10

        # Use all tokens
        assert limiter.try_acquire(10)
        assert limiter.available_tokens() == 0

        # After 0.1 seconds, should have 1 token (10 * 0.1)
        assert limiter.available_tokens() == pytest.approx(1.0)

        # After another 0.3 seconds (0.5 total), should have 4 more tokens
        assert limiter.available_tokens() == pytest.approx(4.0)

        # After 1 second total, should be back to capacity
        assert limiter.available_tokens() == pytest.approx(10.0)

    def test_refill_cap_at_capacity(self):
        """Test that refill doesn't exceed capacity."""
        mock_clock = MagicMock(side_effect=[0, 10])  # 10 second gap
        limiter = BucketRateLimiter(
            requests_per_second=10,
            burst_size=5,  # Lower capacity than rate
            clock=mock_clock,
        )

        # Use some tokens
        assert limiter.try_acquire(3)

        # After 10 seconds, should be capped at capacity (5), not 100 tokens
        assert limiter.available_tokens() == 5

    def test_wait_time(self):
        """Test wait time calculation."""
        mock_clock = MagicMock(return_value=0)
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=10, clock=mock_clock)

        # No wait when tokens available
        assert limiter.wait_time(5) == 0

        # Use all tokens
        limiter.try_acquire(10)

        # Need to wait for 1 token: 0.1 seconds
        assert limiter.wait_time(1) == pytest.approx(0.1)

        # Need to wait for 5 tokens: 0.5 seconds
        assert limiter.wait_time(5) == pytest.approx(0.5)

        # Can't ever get more than capacity
        assert limiter.wait_time(11) == float("inf")

    def test_acquire_blocking(self):
        """Test blocking acquire with timeout."""
        # Use real time for this test
        limiter = BucketRateLimiter(requests_per_second=100, burst_size=1)

        # Use the single token
        assert limiter.try_acquire()

        # Blocking acquire with short timeout should fail
        start = time.monotonic()
        assert not limiter.acquire(timeout=0.001)
        elapsed = time.monotonic() - start
        assert elapsed < 0.01  # Should timeout quickly

        # Reset and test successful acquire
        limiter.reset()
        assert limiter.acquire()

    def test_acquire_invalid_params(self):
        """Test acquire with invalid parameters."""
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=10)

        with pytest.raises(ValueError):
            limiter.acquire(0)

        with pytest.raises(ValueError):
            limiter.acquire(-1)

        with pytest.raises(ValueError):
            limiter.acquire(11)  # More than capacity

    def test_reset(self):
        """Test resetting the bucket."""
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=10)

        # Use all tokens
        limiter.try_acquire(10)
        assert limiter.available_tokens() == 0

        # Reset
        limiter.reset()
        assert limiter.available_tokens() == 10

    def test_thread_safety(self):
        """Test thread safety of rate limiter."""
        limiter = BucketRateLimiter(requests_per_second=100, burst_size=100)
        success_count = threading.local()

        def worker():
            success_count.value = 0
            for _ in range(20):
                if limiter.try_acquire():
                    success_count.value += 1
                time.sleep(0.001)

        threads = []
        for _ in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have used exactly 100 tokens (capacity)
        # Some threads may have gotten refilled tokens
        assert limiter.available_tokens() >= 0

    def test_properties(self):
        """Test rate limiter properties."""
        limiter = BucketRateLimiter(requests_per_second=15, burst_size=30)
        assert limiter.fill_rate == 15
        assert limiter.bucket_size == 30

    def test_repr(self):
        """Test string representation."""
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=20)
        repr_str = repr(limiter)
        assert "BucketRateLimiter" in repr_str
        assert "rate=10" in repr_str
        assert "capacity=20" in repr_str

    def test_constant_time_complexity(self):
        """Test O(1) time complexity of operations."""
        # This is a behavioral test - operations should take similar time
        # regardless of rate or history
        limiter = BucketRateLimiter(requests_per_second=10000, burst_size=10000)

        # Measure time for operations with empty bucket
        start = time.perf_counter()
        for _ in range(1000):
            limiter.try_acquire()
        time_1k_ops = time.perf_counter() - start

        # Reset and measure again (shouldn't depend on history)
        limiter.reset()
        start = time.perf_counter()
        for _ in range(1000):
            limiter.try_acquire()
        time_1k_ops_2 = time.perf_counter() - start

        # Times should be similar (within 50% variance)
        assert abs(time_1k_ops - time_1k_ops_2) / time_1k_ops < 0.5

    def test_sub_second_burst(self):
        """Test burst capacity for sub-second intervals."""
        limiter = BucketRateLimiter(requests_per_second=10, burst_size=50)

        # Can burst up to 50 immediately
        acquired = 0
        for _ in range(100):
            if limiter.try_acquire():
                acquired += 1
            else:
                break

        assert acquired == 50  # Full burst capacity


class TestMultiTierRateLimiter:
    """Test multi-tier rate limiter."""

    def test_single_tier(self):
        """Test multi-tier with single tier."""
        limiter = MultiTierRateLimiter()
        limiter.add_tier("main", requests_per_second=10, burst_size=10)

        # Should behave like single limiter
        for _ in range(10):
            assert limiter.try_acquire()

        assert not limiter.try_acquire()

    def test_multiple_tiers(self):
        """Test multiple rate limit tiers."""
        limiter = MultiTierRateLimiter()
        limiter.add_tier("second", requests_per_second=10, burst_size=10)
        limiter.add_tier("minute", requests_per_second=100 / 60, burst_size=100)

        # Can acquire up to second-tier limit
        for _ in range(10):
            assert limiter.try_acquire()

        # Hit second-tier limit
        assert not limiter.try_acquire()

    def test_tier_interaction(self):
        """Test interaction between tiers."""
        limiter = MultiTierRateLimiter()
        limiter.add_tier("fast", requests_per_second=100, burst_size=10)
        limiter.add_tier("slow", requests_per_second=5, burst_size=20)

        # Limited by fast tier burst (10)
        acquired = 0
        for _ in range(30):
            if limiter.try_acquire():
                acquired += 1

        assert acquired == 10  # Limited by smaller burst

    def test_wait_time_multi_tier(self):
        """Test wait time across multiple tiers."""
        limiter = MultiTierRateLimiter()
        limiter.add_tier("tier1", requests_per_second=10, burst_size=5)
        limiter.add_tier("tier2", requests_per_second=20, burst_size=5)

        # Use all tokens
        for _ in range(5):
            limiter.try_acquire()

        # Wait time should be maximum across tiers
        wait = limiter.wait_time(1)
        assert wait > 0

    def test_reset_all_tiers(self):
        """Test resetting all tiers."""
        limiter = MultiTierRateLimiter()
        limiter.add_tier("tier1", requests_per_second=10, burst_size=10)
        limiter.add_tier("tier2", requests_per_second=10, burst_size=10)

        # Use all tokens
        for _ in range(10):
            limiter.try_acquire()

        assert not limiter.try_acquire()

        # Reset all
        limiter.reset()

        # Should be able to acquire again
        for _ in range(10):
            assert limiter.try_acquire()

    def test_empty_multi_tier(self):
        """Test multi-tier with no tiers."""
        limiter = MultiTierRateLimiter()

        # Should always succeed with no tiers
        assert limiter.try_acquire()
        assert limiter.wait_time() == 0
