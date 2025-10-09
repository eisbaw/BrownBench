"""Graceful shutdown handler for long-running operations.

This module provides signal handling for SIGINT (Ctrl+C) and SIGTERM to enable
graceful shutdown with checkpoint saving.

IMPORTANT LIMITATIONS AND DESIGN DECISIONS:

1. Signal Handler Safety:
   - Signal handlers can only safely perform atomic operations
   - NO I/O, NO locks, NO complex operations in signal handlers
   - We ONLY set a threading.Event flag in the signal handler
   - All logging, cleanup, etc. happens in application code

2. Process-Global Nature:
   - Signal handlers are process-global resources
   - Only ONE ShutdownHandler should be registered at a time
   - Multiple instances will overwrite each other's handlers

3. Thread Safety:
   - Uses threading.Event for thread-safe shutdown flag
   - Safe to check shutdown_requested from any thread
   - Signal can arrive on any thread

4. Platform Differences:
   - SIGTERM not available on Windows (only SIGINT)
   - Signal delivery timing is unpredictable

5. No Callbacks:
   - Previous versions had callbacks, but these are UNSAFE in signal handlers
   - Callbacks can acquire locks, perform I/O, causing deadlocks
   - Application code must check shutdown_requested and handle cleanup

Data Design:
- Single source of truth: threading.Event for shutdown state
- No derived state: registration tracked by dict presence
- Idempotent operations: multiple signals safe, multiple unregister safe

Example:
    >>> import logging
    >>> logger = logging.getLogger(__name__)
    >>>
    >>> handler = ShutdownHandler()
    >>> handler.register()
    >>>
    >>> for item in items:
    ...     if handler.shutdown_requested:
    ...         logger.info("Shutdown requested, saving checkpoint")
    ...         save_checkpoint()
    ...         break
    ...     process(item)
    >>>
    >>> handler.unregister()

Context Manager Example:
    >>> with ShutdownHandler() as handler:
    ...     for item in items:
    ...         if handler.shutdown_requested:
    ...             save_checkpoint()
    ...             break
    ...         process(item)
"""

import logging
import signal
import threading
from collections.abc import Callable
from types import FrameType
from typing import Any

logger = logging.getLogger(__name__)


class ShutdownHandler:
    """Handle shutdown signals gracefully.

    Registers signal handlers for SIGINT and SIGTERM that set a thread-safe
    shutdown flag. Long-running operations can check this flag and perform
    cleanup before exiting.

    The signal handler performs ONLY atomic operations (setting threading.Event).
    All I/O, logging, and cleanup must happen in application code, not in
    signal handlers.
    """

    def __init__(self) -> None:
        """Initialize shutdown handler.

        Creates an Event for thread-safe shutdown signaling.
        Does not register signal handlers yet - call register() or use
        as context manager.
        """
        self._shutdown_event = threading.Event()
        self._original_handlers: dict[int, Callable[[int, FrameType | None], Any] | int | None] = {}
        self._logged_shutdown = False  # Track if we've logged shutdown

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested.

        Thread-safe: can be called from any thread.
        Safe to call frequently in tight loops.

        Returns:
            True if SIGINT or SIGTERM was received, False otherwise
        """
        is_shutdown = self._shutdown_event.is_set()

        # Log once when shutdown first detected (not in signal handler!)
        if is_shutdown and not self._logged_shutdown:
            self._logged_shutdown = True
            logger.info("Shutdown requested via signal, initiating graceful shutdown")

        return is_shutdown

    @property
    def is_registered(self) -> bool:
        """Check if signal handlers are currently registered.

        Returns:
            True if signal handlers are active, False otherwise
        """
        return bool(self._original_handlers)

    def register(self) -> None:
        """Register signal handlers.

        Registers handlers for SIGINT (Ctrl+C) and SIGTERM.
        On Windows, SIGTERM may not be available.

        Raises:
            RuntimeError: If handlers are already registered
        """
        if self.is_registered:
            raise RuntimeError(
                "Shutdown handlers already registered. "
                "Only one handler should be active at a time."
            )

        # Register handlers and save originals
        self._original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self._handle_signal)

        # SIGTERM might not be available on Windows
        if hasattr(signal, "SIGTERM"):
            self._original_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM, self._handle_signal
            )

        logger.debug("Shutdown handlers registered for SIGINT and SIGTERM")

    def unregister(self) -> None:
        """Restore original signal handlers.

        Safe to call even if handlers were never registered.
        Idempotent: safe to call multiple times.
        """
        if not self.is_registered:
            return

        # Restore all original handlers
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)

        self._original_handlers.clear()
        logger.debug("Shutdown handlers unregistered")

    def reset(self) -> None:
        """Reset shutdown flag.

        Clears the shutdown event, allowing the handler to be reused.
        Useful for testing or reusing the handler after a shutdown.

        Note: Does not unregister signal handlers.
        """
        self._shutdown_event.clear()
        self._logged_shutdown = False
        logger.debug("Shutdown flag reset")

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signal.

        CRITICAL: This runs in signal handler context with severe restrictions.
        - NO I/O (no print, no logging, no file operations)
        - NO locks (no threading.Lock, no queue operations)
        - NO memory allocation (keep it simple)
        - ONLY atomic operations

        We ONLY set the Event flag here. All other work happens in main thread
        when shutdown_requested is checked.

        Args:
            signum: Signal number (SIGINT or SIGTERM)
            frame: Current stack frame (unused)
        """
        # ONLY atomic operation: set the event
        # threading.Event.set() is implemented with atomic primitives
        self._shutdown_event.set()

    def __enter__(self) -> "ShutdownHandler":
        """Context manager entry.

        Automatically registers signal handlers when entering context.

        Returns:
            Self for use in with statement
        """
        self.register()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Context manager exit.

        Always unregisters handlers, even if shutdown was requested or
        an exception occurred. This means shutdown state is preserved
        but signal handling stops.

        Does not suppress exceptions (returns None).

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
        """
        self.unregister()
        # Return None (implicit) to propagate any exception
