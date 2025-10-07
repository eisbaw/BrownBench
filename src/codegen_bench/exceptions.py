"""Custom exceptions for BrownBench."""


class BrownBenchError(Exception):
    """Base exception for all BrownBench errors."""

    pass


class ValidationError(BrownBenchError):
    """Raised when solution validation fails."""

    pass


class WorktreeError(BrownBenchError):
    """Raised when git worktree operations fail."""

    pass


class CacheError(BrownBenchError):
    """Raised when cache operations fail."""

    pass


class TaskError(BrownBenchError):
    """Raised when task loading or validation fails."""

    pass


class DUTError(BrownBenchError):
    """Raised when DUT operations fail."""

    pass


class JudgeError(BrownBenchError):
    """Raised when judge evaluation fails."""

    pass


class TournamentError(BrownBenchError):
    """Raised when tournament execution fails."""

    pass
