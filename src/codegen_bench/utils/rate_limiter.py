"""Rate limiting for API calls.

Implementation Notes
--------------------
This rate limiter uses a sliding window approach with deque-based timestamp
tracking. Each acquire() call:
1. Removes timestamps older than 60 seconds: O(k) where k = expired entries
2. Checks if limit is exceeded: O(1)
3. If over limit, calculates sleep time: O(1) for requests, O(n) for tokens

Time Complexity per acquire():
- Best case: O(1) when no cleanup needed and limit not exceeded
- Average case: O(k) where k = timestamps that expired since last call
- Worst case: O(n) where n = max_requests_per_minute (full window scan)

Alternative: Bucket-Based O(1) Rate Limiter
--------------------------------------------
A true O(1) rate limiter can be implemented using the token bucket algorithm
with continuous token refill:

Concept:
    - Maintain a bucket with a maximum capacity of tokens
    - Tokens refill continuously at a constant rate
    - Each request consumes tokens from the bucket
    - If insufficient tokens, request waits until enough tokens refill

Implementation sketch:
    class O1RateLimiter:
        def __init__(self, rate_per_second):
            self.capacity = rate_per_second
            self.tokens = rate_per_second
            self.rate = rate_per_second
            self.last_refill = time.time()
            self.lock = threading.Lock()

        def acquire(self, tokens=1):
            with self.lock:
                now = time.time()
                # Refill tokens based on elapsed time
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_refill = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                else:
                    # Wait for sufficient tokens
                    wait_time = (tokens - self.tokens) / self.rate
                    time.sleep(wait_time)
                    self.tokens = 0

Trade-offs:
    Current (Sliding Window):
        + Precise: Enforces exact limit over any 60-second window
        + Simple: Easy to reason about and debug
        - O(n) worst case: Must scan/cleanup old timestamps
        - Memory: Stores timestamp for every request in window

    Bucket-Based O(1):
        + Constant time: Always O(1) regardless of request rate
        + Memory efficient: Fixed memory (just token count + timestamp)
        - Less precise: Allows bursts up to bucket capacity
        - Refill artifacts: Behavior changes based on refill granularity

The sliding window approach was chosen for BrownBench because:
    1. Precision matters: API providers enforce strict per-minute limits
    2. Scale is moderate: max_requests_per_minute typically 50-100
    3. Debuggability: Easier to inspect/verify exact request history
    4. Safety: Conservative approach preferred for API cost control

Thundering Herd Consideration:
    When multiple threads are waiting on the rate limit and it resets, they may
    all wake up simultaneously and compete for available slots. The current
    implementation partially mitigates this by:
    1. Using a single lock for atomic operations
    2. Re-verifying limits after sleep (lines 217-268)
    3. Releasing lock before sleep to allow other threads to proceed

    However, a true thundering herd could still occur when:
    - Many threads wait for the 60-second window to expire
    - All wake when the oldest timestamp ages out
    - All compete for the newly available slots

    Mitigation strategies if this becomes an issue:
    - Add random jitter to sleep times (e.g., +0-100ms)
    - Use a priority queue or fair scheduling
    - Implement exponential backoff for retries
    - Consider the O(1) bucket approach which naturally spreads wakeups
"""

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
            raise ValueError(f"max_tokens_per_minute must be positive, got {max_tokens_per_minute}")

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

                # Re-verify limits after sleep (race condition: another thread may have consumed slots)
                # If still over limit, wait again
                while True:
                    # ALWAYS update timestamp and cleanup at start of each iteration
                    now = time.time()
                    cutoff = now - 60.0

                    # Clean up ALL old records
                    while self._request_times and self._request_times[0] < cutoff:
                        self._request_times.popleft()

                    if self.max_tokens_per_minute is not None:
                        while self._token_times and self._token_times[0][0] < cutoff:
                            self._token_times.popleft()

                    # Check request limit
                    if len(self._request_times) >= self.max_requests_per_minute:
                        wait_time = self._request_times[0] + 60.0 - now
                        if wait_time > 0:
                            logger.debug("rate_limit_race_detected", reason="request_limit")
                            self._lock.release()
                            try:
                                time.sleep(wait_time)
                            finally:
                                self._lock.acquire()
                            continue  # Re-check from top with fresh timestamp

                    # Check token limit
                    if self.max_tokens_per_minute is not None and tokens > 0:
                        current_tokens = sum(t[1] for t in self._token_times)
                        if current_tokens + tokens > self.max_tokens_per_minute:
                            # Find when we'll have enough tokens
                            needed = current_tokens + tokens - self.max_tokens_per_minute
                            freed = 0
                            wait_time = 0.0

                            for timestamp, token_count in self._token_times:
                                freed += token_count
                                if freed >= needed:
                                    wait_time = timestamp + 60.0 - now
                                    break

                            if wait_time > 0:
                                logger.debug("rate_limit_race_detected", reason="token_limit")
                                self._lock.release()
                                try:
                                    time.sleep(wait_time)
                                finally:
                                    self._lock.acquire()
                                continue  # Re-check from top with fresh timestamp

                    # Both limits satisfied, break out
                    break

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
            ValueError: If tokens is negative, no requests to release,
                       or token mismatch
        """
        if tokens < 0:
            raise ValueError(f"Token count must be non-negative, got {tokens}")

        with self._lock:
            if not self._request_times:
                raise ValueError("No requests to release")

            # Remove the most recent request
            self._request_times.pop()

            # Remove the most recent token usage if applicable
            # Only validate/release tokens if token limiting is enabled AND tokens were used
            if tokens > 0:
                if self.max_tokens_per_minute is None:
                    # Token limiting not enabled but caller tried to release tokens
                    raise ValueError(
                        f"Cannot release {tokens} tokens: token limiting is not enabled"
                    )

                if not self._token_times:
                    raise ValueError("No token requests to release")

                # Verify we're releasing the right amount
                _, recorded_tokens = self._token_times[-1]
                if recorded_tokens != tokens:
                    raise ValueError(
                        f"Token mismatch: tried to release {tokens} tokens, "
                        f"but last request used {recorded_tokens} tokens"
                    )

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
