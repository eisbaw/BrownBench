"""Unit tests for TTL-based solution cache."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codegen_bench.cache.ttl_store import TTLSolutionCache
from codegen_bench.core.solution import Solution


class TestTTLSolutionCache:
    """Test TTL solution cache functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_dut(self):
        """Create mock DUT."""
        dut = MagicMock()
        metadata = MagicMock()
        metadata.id = "test-dut"
        metadata.version = "1.0.0"
        dut.get_metadata.return_value = metadata
        return dut

    @pytest.fixture
    def mock_task(self):
        """Create mock task."""
        task = MagicMock()
        task.id = "test-task"
        return task

    @pytest.fixture
    def mock_solution(self):
        """Create mock solution."""
        solution = MagicMock(spec=Solution)
        solution.to_dict.return_value = {
            "task_id": "test-task",
            "dut_id": "test-dut",
            "changed_files": {"test.py": "print('hello')"},
            "total_tokens": 100,
            "cost_usd": 0.01,
        }
        return solution

    def test_initialization(self, temp_cache_dir):
        """Test cache initialization with TTL."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        assert cache.cache_dir == temp_cache_dir
        assert cache.ttl_seconds == 3600
        assert cache.auto_cleanup is True
        assert cache.metadata_dir == temp_cache_dir / ".cache_metadata"
        assert cache.metadata_dir.exists()

    def test_put_and_get_within_ttl(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test storing and retrieving within TTL."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        # Store solution
        cache.put(mock_dut, mock_task, 42, mock_solution)

        # Mock Solution.from_dict for retrieval
        with patch("codegen_bench.cache.ttl_store.Solution.from_dict") as mock_from_dict:
            mock_from_dict.return_value = mock_solution

            # Retrieve solution (should be found)
            result = cache.get(mock_dut, mock_task, 42)
            assert result == mock_solution

    def test_expiration(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test that expired entries are not returned."""
        # Create cache with 1 second TTL
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=1)

        # Store solution
        cache.put(mock_dut, mock_task, 42, mock_solution)

        # Mock time to simulate expiration
        with patch("codegen_bench.cache.ttl_store.time.time") as mock_time:
            # First call during put
            mock_time.return_value = 1000

            # Store the solution
            cache.put(mock_dut, mock_task, 42, mock_solution)

            # Second call during get (2 seconds later, past TTL)
            mock_time.return_value = 1002

            # Try to retrieve (should be expired)
            result = cache.get(mock_dut, mock_task, 42)
            assert result is None

            # Check that expired count increased
            assert cache._expired_count > 0

    def test_metadata_storage(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test that metadata is correctly stored."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=7200)

        cache.put(mock_dut, mock_task, 42, mock_solution)

        # Check metadata file exists
        cache_key = cache._cache_key(mock_dut, mock_task, 42)
        metadata_file = cache._get_metadata_path(cache_key)
        assert metadata_file.exists()

        # Check metadata content
        with open(metadata_file) as f:
            metadata = json.load(f)
            assert "created_at" in metadata
            assert metadata["ttl_seconds"] == 7200

    def test_cleanup_expired(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test manual cleanup of expired entries."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=1)

        # Store multiple solutions
        for i in range(5):
            task = MagicMock()
            task.id = f"task-{i}"
            cache.put(mock_dut, task, i, mock_solution)

        # Initially should have 5 entries
        assert cache.size() == 5

        # Wait for expiration
        time.sleep(1.1)

        # Run cleanup
        removed = cache.cleanup_all_expired()
        assert removed == 5
        assert cache.size() == 0

    def test_auto_cleanup(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test automatic cleanup on access."""
        cache = TTLSolutionCache(
            temp_cache_dir,
            ttl_seconds=1,
            auto_cleanup=True,
            cleanup_interval_seconds=0,  # Always cleanup
        )

        # Store solution
        cache.put(mock_dut, mock_task, 42, mock_solution)

        # Mock time for expiration
        with patch("codegen_bench.cache.ttl_store.time.time") as mock_time:
            # Initial time
            mock_time.return_value = 1000

            cache.put(mock_dut, mock_task, 42, mock_solution)

            # After TTL expires
            mock_time.return_value = 1002

            # Access cache (should trigger cleanup)
            cache.get(mock_dut, mock_task, 99)  # Different key to trigger cleanup

            # Original entry should be gone
            result = cache.get(mock_dut, mock_task, 42)
            assert result is None

    def test_get_stats(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test cache statistics."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        # Store solutions
        for i in range(3):
            task = MagicMock()
            task.id = f"task-{i}"
            cache.put(mock_dut, task, i, mock_solution)

        stats = cache.get_stats()
        assert stats["total_entries"] == 3
        assert stats["valid_entries"] == 3
        assert stats["expired_entries"] == 0
        assert stats["ttl_seconds"] == 3600
        assert stats["ttl_hours"] == 1.0

    def test_backward_compatibility(self, temp_cache_dir, mock_dut, mock_task):
        """Test compatibility with cache files without metadata."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        # Manually create a cache file without metadata
        cache_key = cache._cache_key(mock_dut, mock_task, 42)
        cache_file = cache.cache_dir / f"{cache_key}.json"

        solution_data = {
            "task_id": "test-task",
            "dut_id": "test-dut",
            "changed_files": {"test.py": "print('hello')"},
            "total_tokens": 100,
            "cost_usd": 0.01,
        }

        with open(cache_file, "w") as f:
            json.dump(solution_data, f)

        # Should still be able to check if expired (using file mtime)
        is_expired = cache._is_expired(cache_key)
        assert not is_expired  # Just created, should not be expired

    def test_clear_with_metadata(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test that clear removes both cache and metadata."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        # Store solutions
        cache.put(mock_dut, mock_task, 42, mock_solution)

        # Verify files exist
        assert cache.size() == 1
        assert len(list(cache.metadata_dir.glob("*.meta"))) == 1

        # Clear cache
        cache.clear()

        # Verify all files removed
        assert cache.size() == 0
        assert len(list(cache.metadata_dir.glob("*.meta"))) == 0

    def test_set_ttl(self, temp_cache_dir):
        """Test updating TTL."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        assert cache.ttl_seconds == 3600

        # Update TTL
        cache.set_ttl(7200)
        assert cache.ttl_seconds == 7200

    def test_expired_removal_error_handling(self, temp_cache_dir, mock_dut, mock_task):
        """Test error handling during expired entry removal."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=1)

        # Create a cache entry
        cache_key = cache._cache_key(mock_dut, mock_task, 42)
        cache_file = cache.cache_dir / f"{cache_key}.json"
        cache_file.write_text("{}")

        # Mock is_expired to return True
        with patch.object(cache, "_is_expired", return_value=True):
            # Mock unlink to raise an error
            with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
                # Should handle the error gracefully
                result = cache.get(mock_dut, mock_task, 42)
                assert result is None

    def test_metadata_save_error_handling(self, temp_cache_dir, mock_dut, mock_task, mock_solution):
        """Test that metadata save errors don't fail the cache operation."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        # Mock metadata save to fail
        with patch.object(cache, "_save_metadata", side_effect=Exception("Metadata error")):
            # Should still successfully store the solution
            cache.put(mock_dut, mock_task, 42, mock_solution)

            # Solution should be stored
            assert cache.size() == 1

    def test_ttl_check_error_handling(self, temp_cache_dir, mock_dut, mock_task):
        """Test error handling in TTL check."""
        cache = TTLSolutionCache(temp_cache_dir, ttl_seconds=3600)

        cache_key = cache._cache_key(mock_dut, mock_task, 42)

        # Create corrupted metadata file
        metadata_file = cache._get_metadata_path(cache_key)
        metadata_file.write_text("not json")

        # Should consider it expired when can't read metadata
        assert cache._is_expired(cache_key) is True
