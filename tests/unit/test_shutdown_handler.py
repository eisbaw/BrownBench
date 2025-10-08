"""Tests for shutdown handler."""

import signal
import threading
import time

import pytest

from codegen_bench.utils.shutdown_handler import ShutdownHandler


def test_shutdown_handler_initialization():
    """Test creating shutdown handler."""
    handler = ShutdownHandler()

    assert not handler.shutdown_requested
    assert not handler.is_registered


def test_register_handlers():
    """Test registering signal handlers."""
    handler = ShutdownHandler()

    # Store original handlers
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    try:
        handler.register()

        assert handler.is_registered
        assert signal.getsignal(signal.SIGINT) != original_sigint
        assert signal.getsignal(signal.SIGTERM) != original_sigterm
    finally:
        handler.unregister()


def test_register_twice_raises():
    """Test that registering twice raises error."""
    handler = ShutdownHandler()

    try:
        handler.register()

        with pytest.raises(RuntimeError, match="already registered"):
            handler.register()
    finally:
        handler.unregister()


def test_unregister_restores_handlers():
    """Test unregistering restores original handlers."""
    handler = ShutdownHandler()

    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    handler.register()
    handler.unregister()

    assert signal.getsignal(signal.SIGINT) == original_sigint
    assert signal.getsignal(signal.SIGTERM) == original_sigterm
    assert not handler.is_registered


def test_unregister_without_register_safe():
    """Test that unregister is safe to call without register."""
    handler = ShutdownHandler()
    handler.unregister()  # Should not raise


def test_unregister_idempotent():
    """Test that unregister can be called multiple times."""
    handler = ShutdownHandler()

    handler.register()
    handler.unregister()
    handler.unregister()  # Should not raise
    assert not handler.is_registered


def test_sigint_sets_shutdown_flag():
    """Test that SIGINT sets shutdown flag."""
    handler = ShutdownHandler()

    try:
        handler.register()
        assert not handler.shutdown_requested

        # Send SIGINT to self
        signal.raise_signal(signal.SIGINT)

        # Small sleep to ensure signal is processed
        time.sleep(0.01)

        assert handler.shutdown_requested
    finally:
        handler.unregister()


def test_sigterm_sets_shutdown_flag():
    """Test that SIGTERM sets shutdown flag."""
    handler = ShutdownHandler()

    try:
        handler.register()
        assert not handler.shutdown_requested

        # Send SIGTERM to self
        signal.raise_signal(signal.SIGTERM)

        # Small sleep to ensure signal is processed
        time.sleep(0.01)

        assert handler.shutdown_requested
    finally:
        handler.unregister()


def test_reset_clears_shutdown_flag():
    """Test that reset clears shutdown flag."""
    handler = ShutdownHandler()

    try:
        handler.register()

        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)
        assert handler.shutdown_requested

        handler.reset()
        assert not handler.shutdown_requested
    finally:
        handler.unregister()


def test_context_manager():
    """Test using handler as context manager."""
    original_sigint = signal.getsignal(signal.SIGINT)

    handler = ShutdownHandler()

    with handler:
        assert handler.is_registered
        assert signal.getsignal(signal.SIGINT) != original_sigint

    # After context, handlers should be unregistered
    assert not handler.is_registered
    assert signal.getsignal(signal.SIGINT) == original_sigint


def test_context_manager_with_signal():
    """Test context manager with signal raised."""
    handler = ShutdownHandler()

    with handler:
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)
        assert handler.shutdown_requested

    # Handlers should be unregistered after context
    assert not handler.is_registered


def test_context_manager_preserves_shutdown_state():
    """Test that context manager exit preserves shutdown state."""
    handler = ShutdownHandler()

    with handler:
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)
        assert handler.shutdown_requested

    # After exit, shutdown state should be preserved
    assert handler.shutdown_requested


def test_shutdown_in_loop():
    """Test typical usage pattern in a loop."""
    handler = ShutdownHandler()

    try:
        handler.register()

        processed = []
        items = list(range(10))

        for item in items:
            if handler.shutdown_requested:
                break
            processed.append(item)

            # Simulate shutdown after 3 items
            if item == 2:
                signal.raise_signal(signal.SIGINT)
                time.sleep(0.01)

        # Should have processed 0, 1, 2, then stopped
        assert processed == [0, 1, 2]
        assert handler.shutdown_requested
    finally:
        handler.unregister()


def test_multiple_handlers_independent():
    """Test that multiple handler instances are independent."""
    handler1 = ShutdownHandler()
    handler2 = ShutdownHandler()

    try:
        handler1.register()

        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)

        assert handler1.shutdown_requested
        assert not handler2.shutdown_requested  # handler2 not registered

        handler1.reset()
        assert not handler1.shutdown_requested
    finally:
        handler1.unregister()


def test_thread_safety_multiple_threads():
    """Test that shutdown flag is thread-safe across multiple threads."""
    handler = ShutdownHandler()
    shutdown_detected = []

    def worker(worker_id: int):
        """Worker thread that checks shutdown flag."""
        while not handler.shutdown_requested:
            time.sleep(0.001)
        shutdown_detected.append(worker_id)

    try:
        handler.register()

        # Start multiple worker threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)

        # Give threads time to start
        time.sleep(0.05)

        # Trigger shutdown
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.05)

        # Wait for all threads to detect shutdown
        for t in threads:
            t.join(timeout=2.0)

        # All threads should have detected shutdown
        assert len(shutdown_detected) == 5, f"Expected 5 threads to detect shutdown, got {len(shutdown_detected)}"
        assert handler.shutdown_requested
    finally:
        handler.unregister()


def test_thread_safety_signal_from_different_thread():
    """Test receiving signal while checking from multiple threads."""
    handler = ShutdownHandler()
    check_results = []

    def checker():
        """Thread that repeatedly checks shutdown flag."""
        for _ in range(1000):
            if handler.shutdown_requested:
                check_results.append(True)
                break
            time.sleep(0.0001)

    try:
        handler.register()

        # Start checker threads
        threads = [threading.Thread(target=checker) for _ in range(3)]
        for t in threads:
            t.start()

        # Give threads time to start checking
        time.sleep(0.01)

        # Send signal
        signal.raise_signal(signal.SIGINT)

        # Wait for threads
        for t in threads:
            t.join(timeout=2.0)

        # All threads should have detected shutdown
        assert len(check_results) == 3
        assert all(check_results)
    finally:
        handler.unregister()


def test_multiple_signals_idempotent():
    """Test that multiple signals are handled safely."""
    handler = ShutdownHandler()

    try:
        handler.register()

        # Send multiple signals
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)
        signal.raise_signal(signal.SIGTERM)
        time.sleep(0.01)

        # Should still work correctly
        assert handler.shutdown_requested
    finally:
        handler.unregister()


def test_is_registered_property():
    """Test is_registered property."""
    handler = ShutdownHandler()

    assert not handler.is_registered

    handler.register()
    assert handler.is_registered

    handler.unregister()
    assert not handler.is_registered


def test_shutdown_requested_logs_once(caplog):
    """Test that shutdown logging happens only once."""
    import logging

    caplog.set_level(logging.INFO)
    handler = ShutdownHandler()

    try:
        handler.register()
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)

        # Check multiple times
        _ = handler.shutdown_requested
        _ = handler.shutdown_requested
        _ = handler.shutdown_requested

        # Should only log once
        log_messages = [r.message for r in caplog.records if "Shutdown requested" in r.message]
        assert len(log_messages) == 1
    finally:
        handler.unregister()


def test_reset_clears_logged_flag():
    """Test that reset allows logging again."""
    import logging

    handler = ShutdownHandler()

    try:
        handler.register()

        # First shutdown
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)
        _ = handler.shutdown_requested  # Triggers logging

        # Reset
        handler.reset()
        assert not handler._logged_shutdown

        # Second shutdown after reset
        signal.raise_signal(signal.SIGINT)
        time.sleep(0.01)
        _ = handler.shutdown_requested  # Should log again

    finally:
        handler.unregister()
