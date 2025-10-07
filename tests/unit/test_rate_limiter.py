"""Tests for rate limiter."""

import threading
import time

import pytest

from codegen_bench.utils.rate_limiter import RateLimiter


def test_rate_limiter_basic() -> None:
    """Test basic rate limiting."""
    limiter = RateLimiter(max_requests_per_minute=5)

    # Should allow 5 requests immediately
    for _ in range(5):
        limiter.acquire()

    # 6th request should be delayed
    start = time.time()
    limiter.acquire()
    elapsed = time.time() - start

    # Should have waited close to 60 seconds (with some tolerance)
    assert elapsed > 58, f"Expected wait of ~60s, got {elapsed}s"


def test_rate_limiter_reset() -> None:
    """Test rate limiter reset."""
    limiter = RateLimiter(max_requests_per_minute=2)

    # Use up the quota
    limiter.acquire()
    limiter.acquire()

    # Reset
    limiter.reset()

    # Should allow immediate requests again
    start = time.time()
    limiter.acquire()
    elapsed = time.time() - start

    assert elapsed < 0.1, f"Expected immediate acquire, got {elapsed}s delay"


def test_rate_limiter_stats() -> None:
    """Test rate limiter statistics."""
    limiter = RateLimiter(max_requests_per_minute=10)

    stats = limiter.get_stats()
    assert stats["requests_in_last_minute"] == 0
    assert stats["max_requests_per_minute"] == 10

    limiter.acquire()
    limiter.acquire()

    stats = limiter.get_stats()
    assert stats["requests_in_last_minute"] == 2


def test_rate_limiter_token_based() -> None:
    """Test token-based rate limiting."""
    limiter = RateLimiter(max_requests_per_minute=100, max_tokens_per_minute=1000)

    # Use 900 tokens
    limiter.acquire(tokens=900)

    # Should allow 100 more tokens
    start = time.time()
    limiter.acquire(tokens=100)
    elapsed = time.time() - start
    assert elapsed < 0.1, "Should allow within token limit"

    # Next request should be delayed
    start = time.time()
    limiter.acquire(tokens=1)
    elapsed = time.time() - start
    assert elapsed > 58, f"Expected wait of ~60s for token limit, got {elapsed}s"


def test_rate_limiter_concurrent() -> None:
    """Test rate limiter with concurrent requests."""
    limiter = RateLimiter(max_requests_per_minute=10)
    results: list[float] = []
    lock = threading.Lock()

    def make_request() -> None:
        start = time.time()
        limiter.acquire()
        with lock:
            results.append(time.time() - start)

    # Launch 15 concurrent requests
    threads = [threading.Thread(target=make_request) for _ in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # First 10 should be immediate, last 5 should wait
    assert len(results) == 15
    immediate = sum(1 for r in results if r < 1.0)
    delayed = sum(1 for r in results if r > 55.0)

    assert immediate == 10, f"Expected 10 immediate requests, got {immediate}"
    assert delayed == 5, f"Expected 5 delayed requests, got {delayed}"


def test_rate_limiter_token_stats() -> None:
    """Test token statistics."""
    limiter = RateLimiter(max_requests_per_minute=100, max_tokens_per_minute=5000)

    limiter.acquire(tokens=100)
    limiter.acquire(tokens=200)

    stats = limiter.get_stats()
    assert stats["tokens_in_last_minute"] == 300
    assert stats["max_tokens_per_minute"] == 5000


def test_rate_limiter_no_token_limit() -> None:
    """Test rate limiter without token limiting."""
    limiter = RateLimiter(max_requests_per_minute=10)

    # Should not track tokens when max_tokens_per_minute is None
    limiter.acquire(tokens=1000)
    limiter.acquire(tokens=5000)

    stats = limiter.get_stats()
    assert "tokens_in_last_minute" not in stats
    assert "max_tokens_per_minute" not in stats


def test_rate_limiter_invalid_config() -> None:
    """Test rate limiter with invalid configuration."""
    # Zero requests per minute
    with pytest.raises(ValueError, match="max_requests_per_minute must be positive"):
        RateLimiter(max_requests_per_minute=0)

    # Negative requests per minute
    with pytest.raises(ValueError, match="max_requests_per_minute must be positive"):
        RateLimiter(max_requests_per_minute=-1)

    # Zero tokens per minute
    with pytest.raises(ValueError, match="max_tokens_per_minute must be positive"):
        RateLimiter(max_requests_per_minute=10, max_tokens_per_minute=0)

    # Negative tokens per minute
    with pytest.raises(ValueError, match="max_tokens_per_minute must be positive"):
        RateLimiter(max_requests_per_minute=10, max_tokens_per_minute=-100)


def test_rate_limiter_invalid_tokens() -> None:
    """Test rate limiter with invalid token count."""
    limiter = RateLimiter(max_requests_per_minute=10)

    # Negative tokens
    with pytest.raises(ValueError, match="Token count must be non-negative"):
        limiter.acquire(tokens=-1)


def test_rate_limiter_timestamp_consistency() -> None:
    """Test that timestamps are consistent after sleeping."""
    limiter = RateLimiter(max_requests_per_minute=2, max_tokens_per_minute=100)

    # Fill up both rate limits
    limiter.acquire(tokens=50)
    limiter.acquire(tokens=50)

    # This should trigger a sleep for request limit
    start = time.time()
    limiter.acquire(tokens=1)
    elapsed = time.time() - start

    # Verify we actually slept
    assert elapsed > 58, f"Expected wait of ~60s, got {elapsed}s"

    # Check that the timestamp recorded is consistent (within the minute window)
    stats = limiter.get_stats()
    # After sleeping ~60s, old requests should have aged out
    # We should see exactly 1 request in the last minute (the one just made)
    assert stats["requests_in_last_minute"] == 1, (
        f"Expected 1 request after sleep, got {stats['requests_in_last_minute']}"
    )
