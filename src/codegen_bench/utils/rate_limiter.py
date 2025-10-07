"""Rate limiting for API calls."""

import threading
import time
from collections import deque
from typing import Any


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
        self._request_lock = threading.Lock()

        # Token rate limiting (if enabled)
        self._token_times: deque[tuple[float, int]] = deque()
        self._token_lock = threading.Lock()

    def acquire(self, tokens: int = 0) -> None:
        """Acquire permission to make an API call.

        Blocks until rate limit allows the request.

        Args:
            tokens: Number of tokens this request will use (for token-based limiting)

        Raises:
            ValueError: If tokens is negative
        """
        if tokens < 0:
            raise ValueError(f"Token count must be non-negative, got {tokens}")
        # Request-based rate limiting
        with self._request_lock:
            now = time.time()
            cutoff = now - 60.0  # 1 minute ago

            # Remove old timestamps
            while self._request_times and self._request_times[0] < cutoff:
                self._request_times.popleft()

            # Check if we need to wait
            if len(self._request_times) >= self.max_requests_per_minute:
                # Wait until oldest request is outside the window
                sleep_time = self._request_times[0] + 60.0 - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    now = time.time()
                    cutoff = now - 60.0
                    # Clean up again after sleeping
                    while self._request_times and self._request_times[0] < cutoff:
                        self._request_times.popleft()

            # Record this request
            self._request_times.append(time.time())

        # Token-based rate limiting (if enabled)
        if self.max_tokens_per_minute is not None and tokens > 0:
            with self._token_lock:
                now = time.time()
                cutoff = now - 60.0

                # Remove old token records
                while self._token_times and self._token_times[0][0] < cutoff:
                    self._token_times.popleft()

                # Calculate current token usage
                current_tokens = sum(t[1] for t in self._token_times)

                # Check if we need to wait
                if current_tokens + tokens > self.max_tokens_per_minute:
                    # Wait until enough tokens are available
                    # Find when we'll have enough tokens
                    needed = current_tokens + tokens - self.max_tokens_per_minute
                    freed = 0
                    wait_until = now

                    for timestamp, token_count in self._token_times:
                        freed += token_count
                        if freed >= needed:
                            wait_until = timestamp + 60.0
                            break

                    sleep_time = wait_until - now
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        now = time.time()
                        cutoff = now - 60.0
                        # Clean up again after sleeping
                        while self._token_times and self._token_times[0][0] < cutoff:
                            self._token_times.popleft()

                # Record this token usage
                self._token_times.append((time.time(), tokens))

    def reset(self) -> None:
        """Reset all rate limit counters.

        Useful for testing or manual reset scenarios.
        """
        with self._request_lock:
            self._request_times.clear()

        with self._token_lock:
            self._token_times.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with current request and token counts
        """
        with self._request_lock:
            now = time.time()
            cutoff = now - 60.0
            recent_requests = sum(1 for t in self._request_times if t >= cutoff)

        stats: dict[str, Any] = {
            "requests_in_last_minute": recent_requests,
            "max_requests_per_minute": self.max_requests_per_minute,
        }

        if self.max_tokens_per_minute is not None:
            with self._token_lock:
                recent_tokens = sum(t[1] for t in self._token_times if t[0] >= cutoff)
                stats["tokens_in_last_minute"] = recent_tokens
                stats["max_tokens_per_minute"] = self.max_tokens_per_minute

        return stats
