"""Rate limiting for API calls."""

import threading
import time
from collections import deque
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API calls.

    Thread-safe rate limiter implementing the token bucket algorithm.
    Supports both requests-per-minute and tokens-per-minute limits.

    Example:
        >>> limiter = RateLimiter(max_requests_per_minute=50)
        >>> limiter.acquire()  # Blocks if rate limit exceeded
        >>> # Make API call
    """

    def __init__(
        self,
        max_requests_per_minute: int = 50,
        max_tokens_per_minute: int | None = None,
    ):
        """Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests allowed per minute (must be > 0)
            max_tokens_per_minute: Maximum tokens allowed per minute (must be > 0 if set)

        Raises:
            ValueError: If rate limits are invalid (zero or negative)
        """
        if max_requests_per_minute <= 0:
            raise ValueError(
                f"max_requests_per_minute must be positive, got {max_requests_per_minute}"
            )

        if max_tokens_per_minute is not None and max_tokens_per_minute <= 0:
            raise ValueError(
                f"max_tokens_per_minute must be positive, got {max_tokens_per_minute}"
            )

        self.max_requests_per_minute = max_requests_per_minute
        self.max_tokens_per_minute = max_tokens_per_minute

        # Request rate limiting
        self._request_times: deque[float] = deque()

        # Token rate limiting (if enabled)
        self._token_times: deque[tuple[float, int]] = deque()

        # Single lock for atomic acquire() operations
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 0) -> None:
        """Acquire permission to make an API call.

        Blocks until rate limit allows the request.
        Uses a single lock to ensure atomic operations and timestamp consistency.

        Args:
            tokens: Number of tokens this request will use (for token-based limiting)

        Raises:
            ValueError: If tokens is negative
        """
        if tokens < 0:
            raise ValueError(f"Token count must be non-negative, got {tokens}")

        with self._lock:
            # Use single timestamp for consistency across both limits
            now = time.time()
            cutoff = now - 60.0  # 1 minute ago
            max_sleep_time = 0.0

            # Check request-based rate limiting
            # Remove old timestamps
            while self._request_times and self._request_times[0] < cutoff:
                self._request_times.popleft()

            # Check if we need to wait for request limit
            if len(self._request_times) >= self.max_requests_per_minute:
                # Wait until oldest request is outside the window
                request_sleep = self._request_times[0] + 60.0 - now
                max_sleep_time = max(max_sleep_time, request_sleep)

            # Check token-based rate limiting (if enabled)
            if self.max_tokens_per_minute is not None and tokens > 0:
                # Remove old token records
                while self._token_times and self._token_times[0][0] < cutoff:
                    self._token_times.popleft()

                # Calculate current token usage
                current_tokens = sum(t[1] for t in self._token_times)

                # Check if we need to wait for token limit
                if current_tokens + tokens > self.max_tokens_per_minute:
                    # Find when we'll have enough tokens
                    needed = current_tokens + tokens - self.max_tokens_per_minute
                    freed = 0

                    for timestamp, token_count in self._token_times:
                        freed += token_count
                        if freed >= needed:
                            token_sleep = timestamp + 60.0 - now
                            max_sleep_time = max(max_sleep_time, token_sleep)
                            break

            # Sleep outside the lock if needed, then re-acquire and record
            if max_sleep_time > 0:
                logger.info(
                    "rate_limit_hit",
                    sleep_seconds=round(max_sleep_time, 2),
                    requests_in_window=len(self._request_times),
                    max_requests_per_minute=self.max_requests_per_minute,
                    tokens_requested=tokens if self.max_tokens_per_minute else None,
                    tokens_in_window=(
                        sum(t[1] for t in self._token_times) if self.max_tokens_per_minute else None
                    ),
                    max_tokens_per_minute=self.max_tokens_per_minute,
                )
                # Release lock before sleeping to allow other threads to proceed
                self._lock.release()
                try:
                    time.sleep(max_sleep_time)
                finally:
                    self._lock.acquire()

                # Re-compute timestamp and clean up after sleeping
                now = time.time()
                cutoff = now - 60.0

                # Clean up old request timestamps
                while self._request_times and self._request_times[0] < cutoff:
                    self._request_times.popleft()

                # Clean up old token records
                if self.max_tokens_per_minute is not None:
                    while self._token_times and self._token_times[0][0] < cutoff:
                        self._token_times.popleft()

            # Record this request with consistent timestamp
            self._request_times.append(now)
            if self.max_tokens_per_minute is not None and tokens > 0:
                self._token_times.append((now, tokens))

    def release(self, tokens: int = 0) -> None:
        """Release a previously acquired request slot.

        Call this when an API request fails and you want to "return" the
        rate limit slot for retry idempotency. This removes the most recent
        request from tracking.

        Args:
            tokens: Number of tokens to release (must match acquire call)

        Raises:
            ValueError: If tokens is negative or if no requests to release
        """
        if tokens < 0:
            raise ValueError(f"Token count must be non-negative, got {tokens}")

        with self._lock:
            if not self._request_times:
                raise ValueError("No requests to release")

            # Remove the most recent request
            self._request_times.pop()

            # Remove the most recent token usage if applicable
            if self.max_tokens_per_minute is not None and tokens > 0:
                if self._token_times:
                    # Verify we're releasing the right amount
                    _, recorded_tokens = self._token_times[-1]
                    if recorded_tokens == tokens:
                        self._token_times.pop()

    def reset(self) -> None:
        """Reset all rate limit counters.

        Useful for testing or manual reset scenarios.
        """
        with self._lock:
            self._request_times.clear()
            self._token_times.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with current request and token counts
        """
        with self._lock:
            now = time.time()
            cutoff = now - 60.0
            recent_requests = sum(1 for t in self._request_times if t >= cutoff)

            stats: dict[str, Any] = {
                "requests_in_last_minute": recent_requests,
                "max_requests_per_minute": self.max_requests_per_minute,
            }

            if self.max_tokens_per_minute is not None:
                recent_tokens = sum(t[1] for t in self._token_times if t[0] >= cutoff)
                stats["tokens_in_last_minute"] = recent_tokens
                stats["max_tokens_per_minute"] = self.max_tokens_per_minute

        return stats
