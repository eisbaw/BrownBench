"""Custom exceptions for BrownBench."""


class BrownBenchError(Exception):
    """Base exception for all BrownBench errors."""


class WorktreeError(BrownBenchError):
    """Raised when git worktree operations fail."""


class DUTError(BrownBenchError):
    """Raised when DUT operations fail."""
