"""Disk-based solution caching."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import structlog

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.exceptions import CacheError

logger = structlog.get_logger(__name__)


class SolutionCache:
    """Disk-based cache for generated solutions.

    Caches solutions to avoid regenerating identical results.
    Cache keys are SHA-256 hashes of (dut_id, dut_version, task_id, seed).
    """

    def __init__(self, cache_dir: Path, fail_on_corruption: bool = False):
        """Initialize solution cache.

        Args:
            cache_dir: Directory to store cached solutions
            fail_on_corruption: If True, raise CacheError on corrupted cache files.
                               If False (default), treat corruption as cache miss.
                               Set to True for debugging cache issues.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fail_on_corruption = fail_on_corruption
        self._corruption_count = 0  # Track corruption frequency for observability

    def _cache_key(self, dut: CodeGenerationApproach, task: Task, seed: int) -> str:
        """Generate unique cache key.

        Args:
            dut: Device under test
            task: Task being solved
            seed: Random seed

        Returns:
            16-character hex string (first 16 chars of SHA-256 hash)
        """
        metadata = dut.get_metadata()
        key_data = f"{metadata.id}_{metadata.version}_{task.id}_{seed}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(self, dut: CodeGenerationApproach, task: Task, seed: int) -> Solution | None:
        """Retrieve cached solution.

        Args:
            dut: Device under test
            task: Task being solved
            seed: Random seed

        Returns:
            Cached solution if found, None otherwise
        """
        key = self._cache_key(dut, task, seed)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            logger.debug(
                "cache_miss",
                dut=dut.get_metadata().id,
                task_id=task.id,
                seed=seed,
                cache_key=key,
            )
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)
            solution = Solution.from_dict(data)
            logger.info(
                "cache_hit",
                dut=dut.get_metadata().id,
                task_id=task.id,
                seed=seed,
                cache_key=key,
            )
            return solution
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
            # Track corruption for observability
            self._corruption_count += 1

            # Log corruption with metrics
            logger.warning(
                "cache_corrupted",
                dut=dut.get_metadata().id,
                task_id=task.id,
                seed=seed,
                cache_key=key,
                cache_file=str(cache_file),
                error=str(e),
                error_type=type(e).__name__,
                corruption_count=self._corruption_count,
                fail_on_corruption=self.fail_on_corruption,
            )

            # Attempt to delete corrupt cache file for cleanup
            try:
                cache_file.unlink()
                logger.info("cache_corrupted_file_deleted", cache_file=str(cache_file))
            except OSError as unlink_error:
                logger.warning(
                    "cache_deletion_failed", cache_file=str(cache_file), error=str(unlink_error)
                )

            # Fail-fast mode for debugging - raise error instead of treating as miss
            if self.fail_on_corruption:
                raise CacheError(
                    f"Corrupted cache file {cache_file}: {e} "
                    f"(fail_on_corruption=True, total corruptions: {self._corruption_count})"
                ) from e

            # Default: treat as cache miss for production resilience
            return None

    def put(self, dut: CodeGenerationApproach, task: Task, seed: int, solution: Solution) -> None:
        """Store solution in cache using atomic write.

        Uses atomic write with temp file + rename to prevent race conditions
        and corruption from concurrent writes.

        Args:
            dut: Device under test
            task: Task being solved
            seed: Random seed
            solution: Solution to cache
        """
        key = self._cache_key(dut, task, seed)
        cache_file = self.cache_dir / f"{key}.json"

        # Atomic write: write to temp file, then rename
        # This ensures that concurrent processes don't corrupt the cache
        fd, temp_path = tempfile.mkstemp(dir=self.cache_dir, suffix=".tmp", text=True)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(solution.to_dict(), f, indent=2)

            # Atomic rename (POSIX guarantees atomicity)
            os.replace(temp_path, cache_file)

            logger.debug(
                "cache_store",
                dut=dut.get_metadata().id,
                task_id=task.id,
                seed=seed,
                cache_key=key,
            )
        except Exception as e:
            # Log the specific exception type for observability
            logger.error(
                "cache_write_failed",
                cache_file=str(cache_file),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise CacheError(f"Failed to write cache file '{cache_file}': {e}") from e
        finally:
            # Always attempt cleanup of temp file if it still exists
            # This ensures no temp file leaks even for unexpected exceptions
            try:
                if Path(temp_path).exists():
                    os.unlink(temp_path)
                    logger.debug("cache_temp_file_cleanup", temp_file=temp_path, status="removed")
            except OSError as cleanup_err:
                # Rationale for log-and-continue behavior:
                # The cache write succeeded (os.replace completed), so the cache entry is valid.
                # Temp file cleanup is best-effort housekeeping. If it fails (e.g., permissions),
                # we log the failure for observability but don't raise an error because:
                # 1. The cache operation itself succeeded
                # 2. Temp files will be cleaned up by OS eventually
                # 3. Raising here would incorrectly signal cache write failure
                logger.warning(
                    "cache_temp_file_cleanup_failed",
                    temp_file=temp_path,
                    error=str(cleanup_err),
                    error_type=type(cleanup_err).__name__,
                )

    def clear(self) -> None:
        """Clear all cached solutions."""
        count = 0
        failed = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except (OSError, FileNotFoundError) as e:
                failed += 1
                logger.warning(
                    "cache_clear_file_failed",
                    cache_file=str(cache_file),
                    error=str(e),
                    error_type=type(e).__name__,
                )
        logger.info(
            "cache_cleared",
            cache_dir=str(self.cache_dir),
            files_removed=count,
            files_failed=failed,
        )

    def size(self) -> int:
        """Get number of cached solutions.

        Returns:
            Number of cached solutions
        """
        return len(list(self.cache_dir.glob("*.json")))

    def invalidate(self, dut: CodeGenerationApproach, task: Task, seed: int) -> bool:
        """Invalidate specific cached solution.

        Args:
            dut: Device under test
            task: Task being solved
            seed: Random seed

        Returns:
            True if cache entry was removed, False if it didn't exist
        """
        key = self._cache_key(dut, task, seed)
        cache_file = self.cache_dir / f"{key}.json"

        if cache_file.exists():
            cache_file.unlink()
            logger.info(
                "cache_invalidated",
                dut=dut.get_metadata().id,
                task_id=task.id,
                seed=seed,
                cache_key=key,
            )
            return True
        logger.debug(
            "cache_invalidate_miss",
            dut=dut.get_metadata().id,
            task_id=task.id,
            seed=seed,
            cache_key=key,
        )
        return False
