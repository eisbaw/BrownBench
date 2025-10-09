"""TTL-based solution caching with automatic expiration."""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import structlog

from codegen_bench.cache.store import SolutionCache
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.exceptions import CacheError

logger = structlog.get_logger(__name__)


class TTLSolutionCache(SolutionCache):
    """Solution cache with Time-To-Live (TTL) expiration.

    Extends SolutionCache to add automatic expiration of cached entries
    based on age, preventing unbounded cache growth and stale data accumulation.

    Features:
    - Automatic expiration of entries older than TTL
    - Lazy expiration on access (no background threads)
    - Optional periodic cleanup for proactive eviction
    - Backward compatible with existing cache files
    - Configurable TTL per cache instance
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl_seconds: int = 86400 * 7,  # Default: 7 days
        fail_on_corruption: bool = False,
        auto_cleanup: bool = True,
        cleanup_interval_seconds: int = 3600,  # Default: 1 hour
    ):
        """Initialize TTL solution cache.

        Args:
            cache_dir: Directory to store cached solutions
            ttl_seconds: Time-to-live in seconds (default: 7 days)
            fail_on_corruption: If True, raise CacheError on corrupted cache files
            auto_cleanup: If True, perform periodic cleanup of expired entries
            cleanup_interval_seconds: Interval between cleanup runs (default: 1 hour)
        """
        super().__init__(cache_dir, fail_on_corruption)
        self.ttl_seconds = ttl_seconds
        self.auto_cleanup = auto_cleanup
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._last_cleanup_time = time.time()
        self._expired_count = 0  # Track expiration frequency

        # Store metadata file for TTL information
        self.metadata_dir = cache_dir / ".cache_metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "ttl_cache_initialized",
            cache_dir=str(cache_dir),
            ttl_hours=ttl_seconds / 3600,
            auto_cleanup=auto_cleanup,
        )

    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get metadata file path for a cache key.

        Args:
            cache_key: Cache key

        Returns:
            Path to metadata file
        """
        return self.metadata_dir / f"{cache_key}.meta"

    def _save_metadata(self, cache_key: str) -> None:
        """Save metadata for a cache entry.

        Args:
            cache_key: Cache key
        """
        metadata = {
            "created_at": time.time(),
            "ttl_seconds": self.ttl_seconds,
        }

        metadata_file = self._get_metadata_path(cache_key)

        # Atomic write for metadata
        fd, temp_path = tempfile.mkstemp(dir=self.metadata_dir, suffix=".tmp", text=True)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(metadata, f)
            os.replace(temp_path, metadata_file)
        except Exception as e:
            logger.warning(
                "metadata_save_failed",
                cache_key=cache_key,
                error=str(e),
            )
            # Don't fail the cache operation if metadata fails
            try:
                if Path(temp_path).exists():
                    os.unlink(temp_path)
            except OSError:
                pass

    def _is_expired(self, cache_key: str) -> bool:
        """Check if a cache entry is expired.

        Args:
            cache_key: Cache key

        Returns:
            True if expired, False otherwise
        """
        metadata_file = self._get_metadata_path(cache_key)

        # If no metadata, check file modification time as fallback
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                created_at = metadata.get("created_at", 0)
            elif cache_file.exists():
                # Fallback to file modification time for backward compatibility
                created_at = cache_file.stat().st_mtime
            else:
                # File doesn't exist
                return True

            age = time.time() - created_at
            return age > self.ttl_seconds

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "ttl_check_failed",
                cache_key=cache_key,
                error=str(e),
            )
            # If we can't determine age, consider it expired for safety
            return True

    def _cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        removed = 0
        failed = 0

        for cache_file in self.cache_dir.glob("*.json"):
            cache_key = cache_file.stem

            if self._is_expired(cache_key):
                try:
                    # Remove cache file
                    cache_file.unlink()

                    # Remove metadata file
                    metadata_file = self._get_metadata_path(cache_key)
                    if metadata_file.exists():
                        metadata_file.unlink()

                    removed += 1
                    self._expired_count += 1

                    logger.debug(
                        "expired_entry_removed",
                        cache_key=cache_key,
                        total_expired=self._expired_count,
                    )
                except OSError as e:
                    failed += 1
                    logger.warning(
                        "expired_cleanup_failed",
                        cache_file=str(cache_file),
                        error=str(e),
                    )

        if removed > 0 or failed > 0:
            logger.info(
                "ttl_cleanup_completed",
                removed=removed,
                failed=failed,
                total_expired=self._expired_count,
            )

        return removed

    def _maybe_cleanup(self) -> None:
        """Perform cleanup if enough time has passed since last cleanup."""
        if not self.auto_cleanup:
            return

        current_time = time.time()
        if current_time - self._last_cleanup_time > self.cleanup_interval_seconds:
            self._cleanup_expired()
            self._last_cleanup_time = current_time

    def get(self, dut: CodeGenerationApproach, task: Task, seed: int) -> Optional[Solution]:
        """Retrieve cached solution if not expired.

        Args:
            dut: Device under test
            task: Task being solved
            seed: Random seed

        Returns:
            Cached solution if found and not expired, None otherwise
        """
        # Periodic cleanup check
        self._maybe_cleanup()

        key = self._cache_key(dut, task, seed)

        # Check if expired before attempting to load
        if self._is_expired(key):
            cache_file = self.cache_dir / f"{key}.json"
            metadata_file = self._get_metadata_path(key)

            # Clean up expired entry
            try:
                if cache_file.exists():
                    cache_file.unlink()
                if metadata_file.exists():
                    metadata_file.unlink()

                self._expired_count += 1

                logger.debug(
                    "cache_expired",
                    dut=dut.get_metadata().id,
                    task_id=task.id,
                    seed=seed,
                    cache_key=key,
                    total_expired=self._expired_count,
                )
            except OSError as e:
                logger.warning(
                    "expired_removal_failed",
                    cache_key=key,
                    error=str(e),
                )

            return None

        # Use parent class to get the solution
        return super().get(dut, task, seed)

    def put(self, dut: CodeGenerationApproach, task: Task, seed: int, solution: Solution) -> None:
        """Store solution in cache with TTL metadata.

        Args:
            dut: Device under test
            task: Task being solved
            seed: Random seed
            solution: Solution to cache
        """
        # Store the solution using parent class
        super().put(dut, task, seed, solution)

        # Save TTL metadata (but don't fail if metadata save fails)
        key = self._cache_key(dut, task, seed)
        try:
            self._save_metadata(key)
        except Exception as e:
            # Metadata save failed, but solution is already stored
            logger.warning(
                "metadata_save_exception",
                cache_key=key,
                error=str(e),
            )

    def clear(self) -> None:
        """Clear all cached solutions and metadata."""
        # Clear cache files
        super().clear()

        # Clear metadata files
        count = 0
        failed = 0
        for meta_file in self.metadata_dir.glob("*.meta"):
            try:
                meta_file.unlink()
                count += 1
            except OSError as e:
                failed += 1
                logger.warning(
                    "metadata_clear_failed",
                    file=str(meta_file),
                    error=str(e),
                )

        logger.info(
            "ttl_cache_cleared",
            cache_dir=str(self.cache_dir),
            metadata_removed=count,
            metadata_failed=failed,
        )

    def cleanup_all_expired(self) -> int:
        """Manually trigger cleanup of all expired entries.

        Returns:
            Number of entries removed
        """
        logger.info("manual_ttl_cleanup_started")
        removed = self._cleanup_expired()
        self._last_cleanup_time = time.time()
        return removed

    def get_stats(self) -> dict:
        """Get cache statistics including TTL information.

        Returns:
            Dictionary with cache statistics
        """
        total_entries = self.size()
        expired_entries = 0

        for cache_file in self.cache_dir.glob("*.json"):
            if self._is_expired(cache_file.stem):
                expired_entries += 1

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "valid_entries": total_entries - expired_entries,
            "ttl_seconds": self.ttl_seconds,
            "ttl_hours": self.ttl_seconds / 3600,
            "auto_cleanup": self.auto_cleanup,
            "cleanup_interval_seconds": self.cleanup_interval_seconds,
            "total_expired_removed": self._expired_count,
            "corruption_count": self._corruption_count,
        }

    def set_ttl(self, ttl_seconds: int) -> None:
        """Update TTL for new cache entries.

        Args:
            ttl_seconds: New TTL in seconds
        """
        old_ttl = self.ttl_seconds
        self.ttl_seconds = ttl_seconds
        logger.info(
            "ttl_updated",
            old_ttl_hours=old_ttl / 3600,
            new_ttl_hours=ttl_seconds / 3600,
        )
