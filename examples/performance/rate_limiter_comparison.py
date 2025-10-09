#!/usr/bin/env python
"""Comparison of sliding window vs bucket rate limiters.

This script demonstrates the performance and behavior differences between
the two rate limiter implementations.
"""

import random
import threading
import time
from typing import Dict, List, Tuple

from codegen_bench.utils.bucket_rate_limiter import BucketRateLimiter
from codegen_bench.utils.rate_limiter import RateLimiter


def benchmark_single_threaded(requests: int = 10000) -> Dict[str, float]:
    """Benchmark single-threaded performance.

    Args:
        requests: Number of requests to simulate

    Returns:
        Timing results for each implementation
    """
    print(f"\nSingle-threaded benchmark ({requests:,} requests)")
    print("-" * 50)

    results = {}

    # Test sliding window
    limiter = RateLimiter(requests_per_second=1000, window_seconds=1)
    start = time.perf_counter()
    success_count = 0

    for _ in range(requests):
        if limiter.should_allow():
            success_count += 1

    elapsed = time.perf_counter() - start
    results["sliding_window"] = {
        "time": elapsed,
        "success": success_count,
        "ops_per_sec": requests / elapsed,
    }

    print(f"Sliding Window: {elapsed:.3f}s ({requests/elapsed:.0f} ops/sec)")
    print(f"  Successful: {success_count:,} / {requests:,}")

    # Test bucket
    limiter = BucketRateLimiter(requests_per_second=1000, burst_size=1000)
    start = time.perf_counter()
    success_count = 0

    for _ in range(requests):
        if limiter.try_acquire():
            success_count += 1

    elapsed = time.perf_counter() - start
    results["bucket"] = {
        "time": elapsed,
        "success": success_count,
        "ops_per_sec": requests / elapsed,
    }

    print(f"Bucket:         {elapsed:.3f}s ({requests/elapsed:.0f} ops/sec)")
    print(f"  Successful: {success_count:,} / {requests:,}")

    # Calculate speedup
    speedup = results["sliding_window"]["time"] / results["bucket"]["time"]
    print(f"\nBucket is {speedup:.1f}x faster")

    return results


def benchmark_multi_threaded(threads: int = 10, requests_per_thread: int = 1000) -> Dict[str, float]:
    """Benchmark multi-threaded performance.

    Args:
        threads: Number of concurrent threads
        requests_per_thread: Requests per thread

    Returns:
        Timing results for each implementation
    """
    print(f"\nMulti-threaded benchmark ({threads} threads, {requests_per_thread:,} requests each)")
    print("-" * 50)

    results = {}

    # Test sliding window
    limiter = RateLimiter(requests_per_second=1000, window_seconds=1)
    success_counts = []
    thread_list = []

    def sliding_worker():
        count = 0
        for _ in range(requests_per_thread):
            if limiter.should_allow():
                count += 1
            # Small random delay to simulate real workload
            if random.random() < 0.1:
                time.sleep(0.0001)
        success_counts.append(count)

    start = time.perf_counter()

    for _ in range(threads):
        t = threading.Thread(target=sliding_worker)
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join()

    elapsed = time.perf_counter() - start
    total_success = sum(success_counts)
    total_requests = threads * requests_per_thread

    results["sliding_window"] = {
        "time": elapsed,
        "success": total_success,
        "ops_per_sec": total_requests / elapsed,
    }

    print(f"Sliding Window: {elapsed:.3f}s ({total_requests/elapsed:.0f} ops/sec)")
    print(f"  Successful: {total_success:,} / {total_requests:,}")

    # Test bucket
    limiter = BucketRateLimiter(requests_per_second=1000, burst_size=1000)
    success_counts = []
    thread_list = []

    def bucket_worker():
        count = 0
        for _ in range(requests_per_thread):
            if limiter.try_acquire():
                count += 1
            # Small random delay to simulate real workload
            if random.random() < 0.1:
                time.sleep(0.0001)
        success_counts.append(count)

    start = time.perf_counter()

    for _ in range(threads):
        t = threading.Thread(target=bucket_worker)
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join()

    elapsed = time.perf_counter() - start
    total_success = sum(success_counts)

    results["bucket"] = {
        "time": elapsed,
        "success": total_success,
        "ops_per_sec": total_requests / elapsed,
    }

    print(f"Bucket:         {elapsed:.3f}s ({total_requests/elapsed:.0f} ops/sec)")
    print(f"  Successful: {total_success:,} / {total_requests:,}")

    # Calculate speedup
    speedup = results["sliding_window"]["time"] / results["bucket"]["time"]
    print(f"\nBucket is {speedup:.1f}x faster")

    return results


def demonstrate_burst_behavior():
    """Demonstrate burst handling differences."""
    print("\nBurst Behavior Comparison")
    print("-" * 50)

    # Sliding window allows precise tracking
    sliding = RateLimiter(requests_per_second=10, window_seconds=1)

    # Bucket allows configurable burst
    bucket_small = BucketRateLimiter(requests_per_second=10, burst_size=10)
    bucket_large = BucketRateLimiter(requests_per_second=10, burst_size=30)

    print("Attempting 20 rapid requests...")

    # Sliding window
    sliding_success = 0
    for _ in range(20):
        if sliding.should_allow():
            sliding_success += 1

    print(f"Sliding Window (10/sec):     {sliding_success} succeeded")

    # Small bucket
    bucket_small_success = 0
    for _ in range(20):
        if bucket_small.try_acquire():
            bucket_small_success += 1

    print(f"Bucket (10/sec, burst=10):   {bucket_small_success} succeeded")

    # Large bucket
    bucket_large_success = 0
    for _ in range(20):
        if bucket_large.try_acquire():
            bucket_large_success += 1

    print(f"Bucket (10/sec, burst=30):   {bucket_large_success} succeeded (allows burst)")


def demonstrate_memory_usage():
    """Demonstrate memory usage differences."""
    print("\nMemory Usage Comparison")
    print("-" * 50)

    import sys

    # Sliding window stores timestamp history
    sliding = RateLimiter(requests_per_second=1000, window_seconds=60)

    # Fill sliding window with requests
    for _ in range(1000):
        sliding.should_allow()

    sliding_size = sys.getsizeof(sliding.requests) + sys.getsizeof(sliding)

    # Bucket has fixed memory
    bucket = BucketRateLimiter(requests_per_second=1000, burst_size=1000)

    # Use some tokens
    for _ in range(1000):
        bucket.try_acquire()

    bucket_size = sys.getsizeof(bucket)

    print(f"Sliding Window after 1000 requests: ~{sliding_size:,} bytes")
    print(f"Bucket after 1000 requests:         ~{bucket_size:,} bytes")
    print(f"Memory ratio: {sliding_size/bucket_size:.1f}x")


def demonstrate_accuracy_tradeoff():
    """Demonstrate accuracy vs performance tradeoff."""
    print("\nAccuracy Comparison")
    print("-" * 50)

    # Set up a specific rate
    target_rate = 10  # requests per second
    test_duration = 5  # seconds

    print(f"Target rate: {target_rate} requests/second for {test_duration} seconds")
    print(f"Expected total: {target_rate * test_duration} requests\n")

    # Test sliding window
    sliding = RateLimiter(requests_per_second=target_rate, window_seconds=1)
    sliding_count = 0
    start = time.time()

    while time.time() - start < test_duration:
        if sliding.should_allow():
            sliding_count += 1
        time.sleep(0.01)  # 100Hz checking

    print(f"Sliding Window: {sliding_count} requests allowed")
    print(f"  Error: {abs(sliding_count - target_rate*test_duration)} requests")

    # Test bucket
    bucket = BucketRateLimiter(requests_per_second=target_rate, burst_size=target_rate)
    bucket_count = 0
    start = time.time()

    while time.time() - start < test_duration:
        if bucket.try_acquire():
            bucket_count += 1
        time.sleep(0.01)  # 100Hz checking

    print(f"Bucket:         {bucket_count} requests allowed")
    print(f"  Error: {abs(bucket_count - target_rate*test_duration)} requests")


def main():
    """Run all comparisons."""
    print("=" * 60)
    print(" RATE LIMITER COMPARISON: SLIDING WINDOW vs BUCKET")
    print("=" * 60)

    # Performance benchmarks
    benchmark_single_threaded(requests=10000)
    benchmark_multi_threaded(threads=10, requests_per_thread=1000)

    # Behavioral comparisons
    demonstrate_burst_behavior()
    demonstrate_memory_usage()
    demonstrate_accuracy_tradeoff()

    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    print("""
Sliding Window (O(n) complexity):
  ✓ Perfect accuracy within window
  ✓ No "burst debt" issues
  ✗ Higher CPU usage (2-5x slower)
  ✗ Growing memory usage with request rate
  ✗ Can have thundering herd issues

Bucket (O(1) complexity):
  ✓ Constant time operations
  ✓ Fixed memory usage
  ✓ Configurable burst capacity
  ✓ Better for high-throughput scenarios
  ✗ Allows bursts that might exceed average rate
  ✗ Less precise for exact windowed counts

Recommendation:
- Use Bucket for high-throughput APIs (>100 req/s)
- Use Sliding Window when exact precision matters
- Consider MultiTierRateLimiter for complex policies
""")
    print("=" * 60)


if __name__ == "__main__":
    main()