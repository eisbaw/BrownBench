"""Tests for solution caching."""

from datetime import UTC, datetime

import pytest

from codegen_bench.cache.store import SolutionCache
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach


class MockDUT(CodeGenerationApproach):
    """Mock DUT for testing."""

    def solve(self, task: Task, seed: int) -> Solution:
        """Not used in tests."""
        raise NotImplementedError

    def get_metadata(self) -> ApproachMetadata:
        """Return test metadata."""
        return ApproachMetadata(
            id="test-dut",
            name="Test DUT",
            description="Test device",
            version="1.0.0",
        )


@pytest.fixture
def cache_dir(tmp_path):
    """Create temporary cache directory."""
    return tmp_path / "cache"


@pytest.fixture
def solution_cache(cache_dir):
    """Create solution cache."""
    return SolutionCache(cache_dir)


@pytest.fixture
def mock_dut():
    """Create mock DUT."""
    return MockDUT(config={})


@pytest.fixture
def simple_task(tmp_path):
    """Create simple task."""
    return Task(
        id="test_task_001",
        name="Test Task",
        project="test",
        domain="test",
        difficulty="easy",
        codebase_path=tmp_path / "codebase",
        specification="Test specification",
    )


@pytest.fixture
def sample_solution(simple_task):
    """Create sample solution."""
    return Solution(
        approach_id="test-dut",
        task_id=simple_task.id,
        seed=42,
        timestamp=datetime.now(UTC),
        changed_files={"main.c": "int main() { return 0; }"},
        generation_time_seconds=1.0,
        total_tokens=100,
        prompt_tokens=50,
        completion_tokens=50,
        api_calls=1,
        cost_usd=0.001,
    )


def test_cache_init(cache_dir):
    """Test cache initialization."""
    cache = SolutionCache(cache_dir)
    assert cache.cache_dir == cache_dir
    assert cache_dir.exists()


def test_cache_key_generation(solution_cache, mock_dut, simple_task):
    """Test cache key generation."""
    key1 = solution_cache._cache_key(mock_dut, simple_task, 42)
    key2 = solution_cache._cache_key(mock_dut, simple_task, 42)
    key3 = solution_cache._cache_key(mock_dut, simple_task, 43)

    # Same inputs produce same key
    assert key1 == key2

    # Different seed produces different key
    assert key1 != key3

    # Key is 16-char hex string
    assert len(key1) == 16
    assert all(c in "0123456789abcdef" for c in key1)


def test_cache_put_and_get(solution_cache, mock_dut, simple_task, sample_solution):
    """Test storing and retrieving solution."""
    # Initially cache miss
    assert solution_cache.get(mock_dut, simple_task, 42) is None

    # Store solution
    solution_cache.put(mock_dut, simple_task, 42, sample_solution)

    # Now cache hit
    cached = solution_cache.get(mock_dut, simple_task, 42)
    assert cached is not None
    assert cached.approach_id == sample_solution.approach_id
    assert cached.task_id == sample_solution.task_id
    assert cached.seed == sample_solution.seed
    assert cached.changed_files == sample_solution.changed_files


def test_cache_miss(solution_cache, mock_dut, simple_task):
    """Test cache miss."""
    assert solution_cache.get(mock_dut, simple_task, 42) is None


def test_cache_different_seeds(solution_cache, mock_dut, simple_task, sample_solution):
    """Test caching with different seeds."""
    solution_cache.put(mock_dut, simple_task, 42, sample_solution)
    solution_cache.put(mock_dut, simple_task, 43, sample_solution)

    cached_42 = solution_cache.get(mock_dut, simple_task, 42)
    cached_43 = solution_cache.get(mock_dut, simple_task, 43)

    assert cached_42 is not None
    assert cached_43 is not None


def test_cache_size(solution_cache, mock_dut, simple_task, sample_solution):
    """Test cache size tracking."""
    assert solution_cache.size() == 0

    solution_cache.put(mock_dut, simple_task, 42, sample_solution)
    assert solution_cache.size() == 1

    solution_cache.put(mock_dut, simple_task, 43, sample_solution)
    assert solution_cache.size() == 2


def test_cache_clear(solution_cache, mock_dut, simple_task, sample_solution):
    """Test clearing cache."""
    solution_cache.put(mock_dut, simple_task, 42, sample_solution)
    solution_cache.put(mock_dut, simple_task, 43, sample_solution)
    assert solution_cache.size() == 2

    solution_cache.clear()
    assert solution_cache.size() == 0
    assert solution_cache.get(mock_dut, simple_task, 42) is None


def test_cache_invalidate(solution_cache, mock_dut, simple_task, sample_solution):
    """Test invalidating specific cache entry."""
    solution_cache.put(mock_dut, simple_task, 42, sample_solution)
    solution_cache.put(mock_dut, simple_task, 43, sample_solution)
    assert solution_cache.size() == 2

    # Invalidate one entry
    result = solution_cache.invalidate(mock_dut, simple_task, 42)
    assert result is True
    assert solution_cache.size() == 1
    assert solution_cache.get(mock_dut, simple_task, 42) is None
    assert solution_cache.get(mock_dut, simple_task, 43) is not None


def test_cache_invalidate_nonexistent(solution_cache, mock_dut, simple_task):
    """Test invalidating nonexistent entry."""
    result = solution_cache.invalidate(mock_dut, simple_task, 42)
    assert result is False


def test_cache_corrupted_file(solution_cache, mock_dut, simple_task, sample_solution, cache_dir):
    """Test handling of corrupted cache file - should raise CacheError and delete corrupt file."""
    from codegen_bench.exceptions import CacheError

    # Store valid solution
    solution_cache.put(mock_dut, simple_task, 42, sample_solution)

    # Corrupt the cache file
    key = solution_cache._cache_key(mock_dut, simple_task, 42)
    cache_file = cache_dir / f"{key}.json"
    with open(cache_file, "w") as f:
        f.write("{ invalid json }")

    # Should raise CacheError for corrupted cache
    with pytest.raises(CacheError, match="Corrupted cache file"):
        solution_cache.get(mock_dut, simple_task, 42)

    # Cache file should have been deleted
    assert not cache_file.exists()


def test_cache_file_format(solution_cache, mock_dut, simple_task, sample_solution, cache_dir):
    """Test cache file format is valid JSON."""
    import json

    solution_cache.put(mock_dut, simple_task, 42, sample_solution)

    key = solution_cache._cache_key(mock_dut, simple_task, 42)
    cache_file = cache_dir / f"{key}.json"

    with open(cache_file) as f:
        data = json.load(f)

    assert "approach_id" in data
    assert "task_id" in data
    assert "seed" in data
    assert data["seed"] == 42


def test_cache_concurrent_writes(solution_cache, mock_dut, simple_task, sample_solution):
    """Test that concurrent writes don't corrupt the cache using atomic writes."""
    import concurrent.futures

    # Create multiple solutions with different data
    solutions = []
    for i in range(10):
        sol = Solution(
            approach_id="test-dut",
            task_id=simple_task.id,
            seed=100 + i,
            timestamp=datetime.now(UTC),
            changed_files={"main.c": f"int main() {{ return {i}; }}"},
            generation_time_seconds=float(i),
            total_tokens=100 + i,
            prompt_tokens=50 + i,
            completion_tokens=50,
            api_calls=1,
            cost_usd=0.001 * i,
        )
        solutions.append((100 + i, sol))

    # Write all solutions concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(solution_cache.put, mock_dut, simple_task, seed, sol)
            for seed, sol in solutions
        ]
        concurrent.futures.wait(futures)

    # All writes should succeed and be readable
    for seed, original_sol in solutions:
        cached = solution_cache.get(mock_dut, simple_task, seed)
        assert cached is not None
        assert cached.seed == seed
        assert cached.generation_time_seconds == original_sol.generation_time_seconds


def test_cache_put_exception_during_write(
    solution_cache, mock_dut, simple_task, sample_solution, monkeypatch
):
    """Test that temp file is cleaned up when an exception occurs during write."""
    import os

    from codegen_bench.exceptions import CacheError

    # Mock os.replace to raise an exception
    def mock_replace(*args, **kwargs):
        raise OSError("Simulated disk full")

    monkeypatch.setattr(os, "replace", mock_replace)

    # Attempt to cache a solution - should raise CacheError (wrapped) and clean up temp file
    with pytest.raises(CacheError, match="Failed to write cache file"):
        solution_cache.put(mock_dut, simple_task, 42, sample_solution)

    # Verify temp file was cleaned up (no .tmp files left)
    temp_files = list(solution_cache.cache_dir.glob("*.tmp"))
    assert len(temp_files) == 0

    # Verify the final cache file was not created
    key = solution_cache._cache_key(mock_dut, simple_task, 42)
    cache_file = solution_cache.cache_dir / f"{key}.json"
    assert not cache_file.exists()
