"""Disk-based solution caching."""

import hashlib
import json
from pathlib import Path

import structlog

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import CodeGenerationApproach

logger = structlog.get_logger(__name__)


class SolutionCache:
    """Disk-based cache for generated solutions.

    Caches solutions to avoid regenerating identical results.
    Cache keys are SHA-256 hashes of (dut_id, dut_version, task_id, seed).
    """

    def __init__(self, cache_dir: Path):
        """Initialize solution cache.

        Args:
            cache_dir: Directory to store cached solutions
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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
            # Cache file corrupted - delete and fail fast
            logger.error(
                "cache_corrupted_deleting",
                dut=dut.get_metadata().id,
                task_id=task.id,
                seed=seed,
                cache_key=key,
                cache_file=str(cache_file),
                error=str(e),
            )
            # Delete corrupt cache file
            try:
                cache_file.unlink()
            except OSError as unlink_error:
                logger.warning("cache_deletion_failed", cache_file=str(cache_file), error=str(unlink_error))

            # Import CacheError
            from codegen_bench.exceptions import CacheError
            raise CacheError(f"Corrupted cache file {cache_file}: {e}") from e

    def put(self, dut: CodeGenerationApproach, task: Task, seed: int, solution: Solution) -> None:
        """Store solution in cache.

        Args:
            dut: Device under test
            task: Task being solved
            seed: Random seed
            solution: Solution to cache
        """
        key = self._cache_key(dut, task, seed)
        cache_file = self.cache_dir / f"{key}.json"

        with open(cache_file, "w") as f:
            json.dump(solution.to_dict(), f, indent=2)

        logger.debug(
            "cache_store",
            dut=dut.get_metadata().id,
            task_id=task.id,
            seed=seed,
            cache_key=key,
        )

    def clear(self) -> None:
        """Clear all cached solutions."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

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
        return False
