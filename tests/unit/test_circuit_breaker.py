"""Unit tests for circuit breaker pattern."""

import time
from unittest.mock import Mock

import pytest

from codegen_bench.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_circuit_breaker_starts_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker("test", failure_threshold=3, reset_timeout=1.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_successful_calls(self):
        """Test that successful calls keep circuit closed."""
        cb = CircuitBreaker("test", failure_threshold=3)

        for _ in range(10):
            result = cb.call(lambda: "success")
            assert result == "success"

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit opens after failure threshold."""
        cb = CircuitBreaker("test", failure_threshold=3)

        # Trigger 3 failures
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        # Circuit should now be OPEN
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_circuit_breaker_blocks_when_open(self):
        """Test that circuit breaker blocks calls when OPEN."""
        cb = CircuitBreaker("test", failure_threshold=2)

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        # Next call should be blocked
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(lambda: "should not execute")

        error = exc_info.value
        assert "Circuit breaker 'test' is OPEN" in str(error)
        assert error.context.is_retryable
        assert error.context.category.value == "transient"

    def test_circuit_breaker_transitions_to_half_open(self):
        """Test that circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=0.1)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        assert cb.state == CircuitState.OPEN

        # Wait for reset timeout
        time.sleep(0.15)

        # Next call should transition to HALF_OPEN
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_after_successes_in_half_open(self):
        """Test that circuit closes after success threshold in HALF_OPEN."""
        cb = CircuitBreaker("test", failure_threshold=2, success_threshold=2, reset_timeout=0.1)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        # Wait for reset
        time.sleep(0.15)

        # Execute success threshold calls
        for _ in range(2):
            cb.call(lambda: "success")

        # Circuit should be CLOSED
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Test that circuit reopens on failure in HALF_OPEN state."""
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=0.1)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        # Wait for reset
        time.sleep(0.15)

        # Success transitions to HALF_OPEN
        cb.call(lambda: "success")
        assert cb.state == CircuitState.HALF_OPEN

        # Failure should reopen circuit
        with pytest.raises(ValueError):
            cb.call(lambda: self._failing_func())

        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_context_manager_success(self):
        """Test circuit breaker as context manager with successful operation."""
        cb = CircuitBreaker("test", failure_threshold=3)

        with cb:
            result = "success"

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_context_manager_failure(self):
        """Test circuit breaker as context manager with failed operation."""
        cb = CircuitBreaker("test", failure_threshold=2)

        for _ in range(2):
            with pytest.raises(ValueError):
                with cb:
                    raise ValueError("test error")

        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_context_manager_blocks_when_open(self):
        """Test that context manager blocks when circuit is OPEN."""
        cb = CircuitBreaker("test", failure_threshold=1)

        # Open circuit
        with pytest.raises(ValueError):
            with cb:
                raise ValueError("test error")

        # Should block next call
        with pytest.raises(CircuitBreakerOpenError):
            with cb:
                pass  # Should not reach here

    def test_circuit_breaker_reset(self):
        """Test manual reset of circuit breaker."""
        cb = CircuitBreaker("test", failure_threshold=2)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        assert cb.state == CircuitState.OPEN

        # Manually reset
        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_expected_exception_type(self):
        """Test that only expected exception types are counted as failures."""
        cb = CircuitBreaker("test", failure_threshold=2, expected_exception=ValueError)

        # ValueError should count as failure
        with pytest.raises(ValueError):
            cb.call(lambda: self._failing_func())
        assert cb.failure_count == 1

        # RuntimeError should not count as failure
        with pytest.raises(RuntimeError):
            cb.call(lambda: self._failing_func_runtime())
        assert cb.failure_count == 1  # Should not increment

    def test_circuit_breaker_state_info(self):
        """Test that get_state_info returns correct information."""
        cb = CircuitBreaker(
            "test_circuit", failure_threshold=5, success_threshold=2, reset_timeout=60.0
        )

        state_info = cb.get_state_info()

        assert state_info["name"] == "test_circuit"
        assert state_info["state"] == "closed"
        assert state_info["failure_count"] == 0
        assert state_info["success_count"] == 0
        assert state_info["config"]["failure_threshold"] == 5
        assert state_info["config"]["success_threshold"] == 2
        assert state_info["config"]["reset_timeout"] == 60.0

    def test_circuit_breaker_error_message_includes_details(self):
        """Test that CircuitBreakerOpenError includes useful details."""
        cb = CircuitBreaker("my_service", failure_threshold=3, reset_timeout=30.0)

        # Open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        # Try to call while open
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(lambda: "should not execute")

        error = exc_info.value
        assert "my_service" in str(error)
        assert "3 failures" in str(error).lower()
        assert error.context.metadata["failure_count"] == 3
        assert "reset_time" in error.context.metadata

    def test_circuit_breaker_actionable_message(self):
        """Test that CircuitBreakerOpenError provides actionable message."""
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=10.0)

        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())

        # Get error
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(lambda: "test")

        message = exc_info.value.get_actionable_message()
        assert "Category: transient" in message
        assert "Severity: warning" in message
        assert "retryable" in message.lower()
        assert "Wait" in message and "for circuit breaker to reset" in message.lower()

    def test_circuit_breaker_multiple_instances_independent(self):
        """Test that multiple circuit breaker instances are independent."""
        cb1 = CircuitBreaker("service1", failure_threshold=2)
        cb2 = CircuitBreaker("service2", failure_threshold=2)

        # Fail cb1
        for _ in range(2):
            with pytest.raises(ValueError):
                cb1.call(lambda: self._failing_func())

        # cb1 should be open, cb2 should be closed
        assert cb1.state == CircuitState.OPEN
        assert cb2.state == CircuitState.CLOSED

        # cb2 should still work
        result = cb2.call(lambda: "success")
        assert result == "success"

    def test_circuit_breaker_success_resets_failure_count_in_closed_state(self):
        """Test that successes reset failure count in CLOSED state."""
        cb = CircuitBreaker("test", failure_threshold=3)

        # One failure
        with pytest.raises(ValueError):
            cb.call(lambda: self._failing_func())
        assert cb.failure_count == 1

        # Success should reset count
        cb.call(lambda: "success")
        assert cb.failure_count == 0

        # Circuit should still be closed
        assert cb.state == CircuitState.CLOSED

    # Helper methods
    @staticmethod
    def _failing_func():
        """Helper function that always raises ValueError."""
        raise ValueError("test failure")

    @staticmethod
    def _failing_func_runtime():
        """Helper function that always raises RuntimeError."""
        raise RuntimeError("runtime failure")


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""

    def test_circuit_breaker_with_mock_api(self):
        """Test circuit breaker with mock API that fails intermittently."""
        mock_api = Mock()
        cb = CircuitBreaker("mock_api", failure_threshold=3, reset_timeout=0.1)

        # Simulate 3 API failures
        mock_api.call.side_effect = [
            ValueError("API Error 1"),
            ValueError("API Error 2"),
            ValueError("API Error 3"),
        ]

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(mock_api.call)

        # Circuit should be open
        assert cb.state == CircuitState.OPEN

        # Should block without calling API
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(mock_api.call)

        # API should have been called only 3 times (not 4)
        assert mock_api.call.call_count == 3

    def test_circuit_breaker_recovery_scenario(self):
        """Test full recovery scenario: fail -> open -> wait -> recover."""
        cb = CircuitBreaker("service", failure_threshold=2, success_threshold=2, reset_timeout=0.1)

        # Phase 1: Fail and open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: self._failing_func())
        assert cb.state == CircuitState.OPEN

        # Phase 2: Wait for reset timeout
        time.sleep(0.15)

        # Phase 3: Successful recovery
        for _ in range(2):
            result = cb.call(lambda: "recovered")
            assert result == "recovered"

        # Circuit should be closed
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

        # Phase 4: Normal operation
        result = cb.call(lambda: "normal operation")
        assert result == "normal operation"

    # Helper methods
    @staticmethod
    def _failing_func():
        """Helper function that always raises ValueError."""
        raise ValueError("test failure")
