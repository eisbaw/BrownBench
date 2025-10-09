"""Bucket-based O(1) rate limiter implementation.

This module provides a token bucket rate limiter with O(1) time complexity
for all operations, offering better performance than sliding window approaches
for high-throughput scenarios.
"""

import threading
import time
from typing import Optional


class BucketRateLimiter:
    """Token bucket rate limiter with O(1) operations.

    This implementation offers constant-time complexity for all operations,
    making it more efficient than sliding window approaches for high-throughput
    scenarios. It trades perfect accuracy for performance.

    Attributes:
        capacity: Maximum tokens in bucket
        refill_rate: Tokens added per second
        tokens: Current available tokens
        last_refill: Last refill timestamp

    Example:
        >>> limiter = BucketRateLimiter(requests_per_second=10, burst_size=20)
        >>> if limiter.try_acquire():
        ...     # Process request
        ...     pass
        >>> else:
        ...     # Rate limited, wait or reject
        ...     pass
    """

    def __init__(
        self,
        requests_per_second: float,
        burst_size: Optional[int] = None,
        clock: Optional[callable] = None,
    ):
        """Initialize bucket rate limiter.

        Args:
            requests_per_second: Sustained rate limit
            burst_size: Maximum burst capacity (defaults to requests_per_second)
            clock: Optional clock function for testing
        """
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        self.refill_rate = requests_per_second
        self.capacity = burst_size if burst_size is not None else int(requests_per_second)

        if self.capacity < 1:
            self.capacity = 1

        # Start with full bucket
        self.tokens = float(self.capacity)
        self.clock = clock or time.monotonic
        self.last_refill = self.clock()

        # Thread safety
        self.lock = threading.Lock()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from bucket.

        O(1) operation - constant time regardless of rate or history.

        Args:
            tokens: Number of tokens to acquire (default 1)

        Returns:
            True if tokens acquired, False if rate limited
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        if tokens > self.capacity:
            # Can never satisfy this request
            return False

        with self.lock:
            # Refill bucket based on elapsed time
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens, blocking if necessary.

        O(1) per attempt, may make multiple attempts if blocking.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum seconds to wait (None = no timeout)

        Returns:
            True if tokens acquired, False if timeout
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        if tokens > self.capacity:
            raise ValueError(f"Cannot acquire {tokens} tokens, capacity is {self.capacity}")

        start_time = self.clock() if timeout is not None else None
        sleep_time = 0.001  # Start with 1ms sleep

        while True:
            if self.try_acquire(tokens):
                return True

            if timeout is not None:
                elapsed = self.clock() - start_time
                if elapsed >= timeout:
                    return False
                remaining = timeout - elapsed
                sleep_time = min(sleep_time, remaining)

            # Exponential backoff with cap
            time.sleep(sleep_time)
            sleep_time = min(sleep_time * 1.5, 0.1)  # Cap at 100ms

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time until tokens available.

        O(1) operation.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds until tokens will be available (0 if available now)
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        if tokens > self.capacity:
            return float("inf")  # Can never satisfy

        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                return 0.0

            # Calculate time needed to accumulate enough tokens
            tokens_needed = tokens - self.tokens
            wait_seconds = tokens_needed / self.refill_rate

            return wait_seconds

    def reset(self) -> None:
        """Reset bucket to full capacity.

        O(1) operation.
        """
        with self.lock:
            self.tokens = float(self.capacity)
            self.last_refill = self.clock()

    def available_tokens(self) -> float:
        """Get current available tokens.

        O(1) operation.

        Returns:
            Current token count
        """
        with self.lock:
            self._refill()
            return self.tokens

    def _refill(self) -> None:
        """Refill tokens based on elapsed time.

        O(1) operation - single calculation regardless of elapsed time.
        """
        now = self.clock()
        elapsed = now - self.last_refill

        if elapsed > 0:
            # Add tokens based on elapsed time
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.tokens + tokens_to_add, self.capacity)
            self.last_refill = now

    @property
    def fill_rate(self) -> float:
        """Get fill rate in tokens per second."""
        return self.refill_rate

    @property
    def bucket_size(self) -> int:
        """Get bucket capacity."""
        return self.capacity

    def __repr__(self) -> str:
        """String representation."""
        with self.lock:
            self._refill()
            return (
                f"BucketRateLimiter("
                f"rate={self.refill_rate}/s, "
                f"capacity={self.capacity}, "
                f"available={self.tokens:.1f})"
            )


class MultiTierRateLimiter:
    """Multi-tier rate limiter combining multiple bucket limiters.

    Useful for implementing different rate limits at different time scales,
    e.g., 100 requests per second AND 5000 requests per minute.

    Example:
        >>> limiter = MultiTierRateLimiter()
        >>> limiter.add_tier("second", requests_per_second=100)
        >>> limiter.add_tier("minute", requests_per_second=5000/60, burst_size=5000)
        >>> if limiter.try_acquire():
        ...     # All tiers passed
        ...     pass
    """

    def __init__(self):
        """Initialize multi-tier rate limiter."""
        self.tiers = {}
        self.lock = threading.Lock()

    def add_tier(
        self,
        name: str,
        requests_per_second: float,
        burst_size: Optional[int] = None,
    ) -> None:
        """Add a rate limit tier.

        Args:
            name: Tier identifier
            requests_per_second: Rate limit for this tier
            burst_size: Burst capacity for this tier
        """
        with self.lock:
            self.tiers[name] = BucketRateLimiter(requests_per_second, burst_size)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from all tiers.

        O(n) where n is number of tiers (typically small, e.g., 2-3).

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired from all tiers, False otherwise
        """
        with self.lock:
            # Check all tiers first
            for tier in self.tiers.values():
                if tier.available_tokens() < tokens:
                    return False

            # Acquire from all tiers
            for tier in self.tiers.values():
                if not tier.try_acquire(tokens):
                    # Shouldn't happen after check above, but be safe
                    return False

            return True

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate maximum wait time across all tiers.

        Args:
            tokens: Number of tokens needed

        Returns:
            Maximum wait time across all tiers
        """
        with self.lock:
            if not self.tiers:
                return 0.0

            return max(tier.wait_time(tokens) for tier in self.tiers.values())

    def reset(self) -> None:
        """Reset all tiers."""
        with self.lock:
            for tier in self.tiers.values():
                tier.reset()