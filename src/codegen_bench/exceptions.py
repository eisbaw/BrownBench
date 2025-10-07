"""Custom exceptions for BrownBench."""


class BrownBenchError(Exception):
    """Base exception for all BrownBench errors."""


class WorktreeError(BrownBenchError):
    """Raised when git worktree operations fail."""


class DUTError(BrownBenchError):
    """Raised when DUT operations fail."""


class ValidationError(BrownBenchError):
    """Raised when solution validation fails."""


class TaskError(BrownBenchError):
    """Raised when task loading or validation fails."""


class CacheError(BrownBenchError):
    """Raised when cache operations fail."""


class JudgeError(BrownBenchError):
    """Raised when judge evaluation fails."""


class TournamentError(BrownBenchError):
    """Raised when tournament execution fails."""
