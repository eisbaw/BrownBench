"""Custom exceptions for BrownBench."""


class BrownBenchError(Exception):
    """Base exception for all BrownBench errors."""


class WorktreeError(BrownBenchError):
    """Raised when git worktree operations fail."""


class DUTError(BrownBenchError):
    """Raised when DUT operations fail."""


class DUTConfigError(DUTError):
    """Raised when DUT configuration is invalid."""


class DUTAPIError(DUTError):
    """Raised when DUT API calls fail."""


class DUTParsingError(DUTError):
    """Raised when DUT response parsing fails."""


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
