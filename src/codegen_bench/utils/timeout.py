"""Timeout utilities for function execution."""

import signal
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, TypeVar

from codegen_bench.exceptions import DUTTimeoutError

T = TypeVar("T")


@contextmanager
def timeout_context(seconds: int, operation: str = "operation") -> Generator[None, None, None]:
    """Context manager for timeout enforcement.

    On UNIX systems, uses signal.alarm for accurate timeout.
    On Windows, uses threading.Timer as a fallback.

    Args:
        seconds: Timeout in seconds
        operation: Description of operation for error message

    Raises:
        DUTTimeoutError: If operation exceeds timeout

    Example:
        with timeout_context(30, "API call"):
            result = expensive_api_call()
    """
    if seconds <= 0:
        raise ValueError(f"Timeout must be positive, got {seconds}")

    # Try signal-based timeout on UNIX systems
    if hasattr(signal, "SIGALRM"):
        with _signal_timeout_context(seconds, operation):
            yield
    else:
        # Fallback to threading-based timeout on Windows
        with _thread_timeout_context(seconds, operation):
            yield


@contextmanager
def _signal_timeout_context(seconds: int, operation: str) -> Generator[None, None, None]:
    """Signal-based timeout for UNIX systems."""

    def timeout_handler(signum: int, frame: Any) -> None:
        raise DUTTimeoutError(
            f"Operation '{operation}' exceeded timeout of {seconds}s",
            timeout_seconds=seconds,
        )

    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Cancel alarm and restore old handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@contextmanager
def _thread_timeout_context(seconds: int, operation: str) -> Generator[None, None, None]:
    """Thread-based timeout fallback for Windows.

    Note: This is less reliable than signal-based timeout as it cannot
    interrupt blocking system calls. The operation must check for
    interruption cooperatively.
    """
    timer = None
    timed_out = threading.Event()

    def timeout_callback() -> None:
        timed_out.set()

    try:
        timer = threading.Timer(seconds, timeout_callback)
        timer.daemon = True
        timer.start()

        # Check timed_out flag before and after yield
        if timed_out.is_set():
            raise DUTTimeoutError(
                f"Operation '{operation}' exceeded timeout of {seconds}s",
                timeout_seconds=seconds,
            )

        yield

        # Check if timeout occurred during operation
        if timed_out.is_set():
            raise DUTTimeoutError(
                f"Operation '{operation}' exceeded timeout of {seconds}s",
                timeout_seconds=seconds,
            )
    finally:
        if timer:
            timer.cancel()


def with_timeout(
    timeout_seconds: int, operation: str = "operation"
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add timeout protection to a function.

    Args:
        timeout_seconds: Timeout in seconds
        operation: Description of operation for error message

    Returns:
        Decorated function with timeout protection

    Example:
        @with_timeout(30, "solve task")
        def solve(self, task: Task, seed: int) -> Solution:
            return expensive_solve(task, seed)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with timeout_context(timeout_seconds, operation or func.__name__):
                return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
