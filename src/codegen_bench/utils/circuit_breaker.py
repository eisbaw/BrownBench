"""Circuit breaker pattern for fault tolerance.

Implements the circuit breaker pattern to prevent cascading failures
when external services (like API endpoints) are experiencing issues.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit breaker is tripped, requests fail fast
- HALF_OPEN: Testing if service has recovered

The circuit breaker transitions:
1. CLOSED -> OPEN: After failure_threshold consecutive failures
2. OPEN -> HALF_OPEN: After reset_timeout seconds
3. HALF_OPEN -> CLOSED: After success_threshold consecutive successes
4. HALF_OPEN -> OPEN: On any failure
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from codegen_bench.exceptions import TransientError

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, block requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(TransientError):
    """Raised when circuit breaker is open and blocking requests."""

    def __init__(
        self,
        message: str,
        failure_count: int,
        reset_time: float,
        **kwargs: Any,
    ):
        """Initialize CircuitBreakerOpenError.

        Args:
            message: Error message
            failure_count: Number of consecutive failures
            reset_time: When circuit will attempt to close (unix timestamp)
            **kwargs: Additional error context
        """
        wait_seconds = max(0, int(reset_time - time.time()))
        # Circuit breaker errors are transient - they will automatically recover
        # Override TransientError's retry_suggestion with circuit-breaker specific message
        kwargs["retry_suggestion"] = f"Wait {wait_seconds}s for circuit breaker to reset and retry"
        kwargs["failure_count"] = failure_count
        kwargs["reset_time"] = reset_time
        super().__init__(
            message,
            retry_after_seconds=wait_seconds,
            **kwargs,
        )


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open to close circuit
    reset_timeout: float = 60.0  # Seconds before trying half-open from open
    expected_exception: type[Exception] = Exception  # What exceptions to count as failures


@dataclass
class CircuitBreakerState:
    """Internal state of circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Example:
        cb = CircuitBreaker(
            name="anthropic_api",
            failure_threshold=5,
            reset_timeout=60
        )

        def call_api():
            with cb:
                return expensive_api_call()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        reset_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker
            failure_threshold: Consecutive failures before opening circuit
            success_threshold: Consecutive successes to close circuit from half-open
            reset_timeout: Seconds to wait before trying half-open from open
            expected_exception: Exception types to count as failures
        """
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            reset_timeout=reset_timeout,
            expected_exception=expected_exception,
        )
        self._state = CircuitBreakerState()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._state.failure_count

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset from OPEN to HALF_OPEN."""
        if self._state.state != CircuitState.OPEN:
            return False

        time_since_failure = time.time() - self._state.last_failure_time
        return time_since_failure >= self.config.reset_timeout

    def _record_success(self) -> None:
        """Record successful operation."""
        if self._state.state == CircuitState.HALF_OPEN:
            self._state.success_count += 1
            if self._state.success_count >= self.config.success_threshold:
                # Enough successes in half-open, transition to closed
                self._state.state = CircuitState.CLOSED
                self._state.failure_count = 0
                self._state.success_count = 0
                self._state.last_state_change = time.time()
        elif self._state.state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._state.failure_count = 0

    def _record_failure(self) -> None:
        """Record failed operation."""
        self._state.last_failure_time = time.time()

        if self._state.state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens circuit
            self._state.state = CircuitState.OPEN
            self._state.failure_count += 1
            self._state.success_count = 0
            self._state.last_state_change = time.time()
        elif self._state.state == CircuitState.CLOSED:
            self._state.failure_count += 1
            if self._state.failure_count >= self.config.failure_threshold:
                # Threshold exceeded, open circuit
                self._state.state = CircuitState.OPEN
                self._state.success_count = 0
                self._state.last_state_change = time.time()

    def call(self, func: Callable[[], T]) -> T:
        """Execute function through circuit breaker.

        Args:
            func: Function to execute

        Returns:
            Result of function execution

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception raised by func
        """
        # Check if should attempt reset
        if self._should_attempt_reset():
            self._state.state = CircuitState.HALF_OPEN
            self._state.success_count = 0
            self._state.last_state_change = time.time()

        # Block requests if circuit is open
        if self._state.state == CircuitState.OPEN:
            reset_time = self._state.last_failure_time + self.config.reset_timeout
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN after {self._state.failure_count} failures",
                failure_count=self._state.failure_count,
                reset_time=reset_time,
                component=f"CircuitBreaker[{self.name}]",
            )

        # Attempt to execute function
        try:
            result = func()
            self._record_success()
            return result
        except self.config.expected_exception:
            self._record_failure()
            raise

    def __enter__(self) -> "CircuitBreaker":
        """Context manager entry - check circuit state."""
        # Check if should attempt reset
        if self._should_attempt_reset():
            self._state.state = CircuitState.HALF_OPEN
            self._state.success_count = 0
            self._state.last_state_change = time.time()

        # Block requests if circuit is open
        if self._state.state == CircuitState.OPEN:
            reset_time = self._state.last_failure_time + self.config.reset_timeout
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN after {self._state.failure_count} failures",
                failure_count=self._state.failure_count,
                reset_time=reset_time,
                component=f"CircuitBreaker[{self.name}]",
            )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - record success or failure."""
        if exc_type is None:
            # Success
            self._record_success()
        elif isinstance(exc_val, self.config.expected_exception):
            # Expected failure
            self._record_failure()
        # else: Unexpected exception - don't count as failure
        # Always return None to re-raise exceptions

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self._state = CircuitBreakerState()

    def get_state_info(self) -> dict[str, Any]:
        """Get current state information for debugging/monitoring.

        Returns:
            Dictionary with state details
        """
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure_time": self._state.last_failure_time,
            "time_since_last_failure": time.time() - self._state.last_failure_time
            if self._state.last_failure_time > 0
            else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "reset_timeout": self.config.reset_timeout,
            },
        }
