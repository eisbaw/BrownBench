"""Custom exceptions for BrownBench.

Error Taxonomy:
--------------
All errors inherit from BrownBenchError and include:
1. Detailed error messages with context
2. Actionable suggestions for resolution
3. Error metadata for reporting and analysis
4. Retry capability indication

Error Categories:
- Configuration Errors: Invalid config, missing dependencies (not retryable)
- Transient Errors: Network issues, rate limits (retryable)
- Data Errors: Invalid task data, parsing failures (not retryable)
- Infrastructure Errors: Git, Docker, filesystem issues (may be retryable)
- API Errors: External API failures (retryable with backoff)
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    INFO = "info"  # Informational, e.g., graceful degradation
    WARNING = "warning"  # Non-fatal, operation continues with reduced functionality
    ERROR = "error"  # Fatal to current operation, but system can continue
    CRITICAL = "critical"  # Fatal to entire system


class ErrorCategory(Enum):
    """High-level categorization of errors."""

    CONFIGURATION = "configuration"  # Invalid config, missing keys, bad parameters
    TRANSIENT = "transient"  # Network timeouts, rate limits, temporary API issues
    DATA = "data"  # Invalid task YAML, malformed responses, parsing failures
    INFRASTRUCTURE = "infrastructure"  # Git errors, Docker failures, filesystem issues
    API = "api"  # External API errors (Claude, etc.)
    RESOURCE = "resource"  # Out of budget, disk space, memory
    VALIDATION = "validation"  # Solution validation failures, test failures
    INTERNAL = "internal"  # Unexpected internal errors, programming bugs


@dataclass
class ErrorContext:
    """Contextual information about an error."""

    timestamp: str
    category: ErrorCategory
    severity: ErrorSeverity
    is_retryable: bool
    retry_suggestion: str | None = None
    component: str | None = (
        None  # Which component raised the error (e.g., "SimpleChatDUT", "TournamentRunner")
    )
    operation: str | None = None  # What operation failed (e.g., "solve", "compare")
    task_id: str | None = None
    dut_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "category": self.category.value,
            "severity": self.severity.value,
            "is_retryable": self.is_retryable,
            "retry_suggestion": self.retry_suggestion,
            "component": self.component,
            "operation": self.operation,
            "task_id": self.task_id,
            "dut_id": self.dut_id,
            "metadata": self.metadata,
        }


class BrownBenchError(Exception):
    """Base exception for all BrownBench errors.

    All BrownBench exceptions include:
    - Rich context about the error
    - Actionable suggestions for resolution
    - Metadata for error reporting and analysis
    """

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        is_retryable: bool = False,
        retry_suggestion: str | None = None,
        component: str | None = None,
        operation: str | None = None,
        task_id: str | None = None,
        dut_id: str | None = None,
        **metadata: Any,
    ):
        """Initialize BrownBenchError.

        Args:
            message: Human-readable error message
            category: Error category
            severity: Error severity level
            is_retryable: Whether this error can be retried
            retry_suggestion: How to retry (if retryable)
            component: Component that raised the error
            operation: Operation that failed
            task_id: Task ID if applicable
            dut_id: DUT ID if applicable
            **metadata: Additional metadata
        """
        super().__init__(message)
        self.context = ErrorContext(
            timestamp=datetime.now(UTC).isoformat(),
            category=category,
            severity=severity,
            is_retryable=is_retryable,
            retry_suggestion=retry_suggestion,
            component=component,
            operation=operation,
            task_id=task_id,
            dut_id=dut_id,
            metadata=metadata,
        )

    def get_actionable_message(self) -> str:
        """Get error message with actionable suggestions.

        Returns:
            Formatted error message with resolution steps
        """
        msg = f"{self}\n"
        msg += f"Category: {self.context.category.value}\n"
        msg += f"Severity: {self.context.severity.value}\n"

        if self.context.component:
            msg += f"Component: {self.context.component}\n"
        if self.context.operation:
            msg += f"Operation: {self.context.operation}\n"

        if self.context.is_retryable:
            msg += "\nThis error is retryable.\n"
        else:
            msg += "\nThis error is not retryable. Manual intervention required.\n"

        # Show suggestion regardless of retryability (e.g., "increase timeout" is actionable advice)
        if self.context.retry_suggestion:
            msg += f"Suggestion: {self.context.retry_suggestion}\n"

        return msg


# ============================================================================
# Configuration Errors (not retryable)
# ============================================================================


class ConfigurationError(BrownBenchError):
    """Base class for configuration errors."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.ERROR,
            is_retryable=False,
            **kwargs,
        )


class DUTError(BrownBenchError):
    """Base class for DUT-related errors (for backward compatibility)."""

    def __init__(self, message: str, **kwargs: Any):
        # Default to API category since most DUT errors are API-related
        if "category" not in kwargs:
            kwargs["category"] = ErrorCategory.API
        super().__init__(message, **kwargs)


class DUTTimeoutError(DUTError):
    """Raised when DUT.solve() exceeds timeout limit.

    Examples:
    - API call hangs
    - DUT takes too long to generate solution
    - Processing timeout
    """

    def __init__(self, message: str, timeout_seconds: int, **kwargs: Any):
        if "category" not in kwargs:
            kwargs["category"] = ErrorCategory.RESOURCE
        if "component" not in kwargs:
            kwargs["component"] = "DUT"
        if "operation" not in kwargs:
            kwargs["operation"] = "solve"
        if "is_retryable" not in kwargs:
            kwargs["is_retryable"] = False
        if "retry_suggestion" not in kwargs:
            kwargs["retry_suggestion"] = (
                f"Increase timeout limit (currently {timeout_seconds}s) or optimize DUT implementation."
            )
        super().__init__(message, timeout_seconds=timeout_seconds, **kwargs)


class DUTConfigError(DUTError):
    """Raised when DUT configuration is invalid.

    Examples:
    - Missing API key
    - Invalid model name
    - Out-of-range parameters (temperature, max_tokens)
    """

    def __init__(self, message: str, **kwargs: Any):
        # Set defaults if not provided for backward compatibility
        if "category" not in kwargs:
            kwargs["category"] = ErrorCategory.CONFIGURATION
        if "component" not in kwargs:
            kwargs["component"] = "DUT"
        if "operation" not in kwargs:
            kwargs["operation"] = "configuration"
        if "is_retryable" not in kwargs:
            kwargs["is_retryable"] = False
        super().__init__(message, **kwargs)


class TaskConfigError(ConfigurationError):
    """Raised when task configuration is invalid.

    Examples:
    - Missing required YAML fields
    - Invalid task specification
    - Malformed constraints
    """

    def __init__(self, message: str, **kwargs: Any):
        if "component" not in kwargs:
            kwargs["component"] = "TaskLoader"
        if "operation" not in kwargs:
            kwargs["operation"] = "load_task"
        super().__init__(message, **kwargs)


# ============================================================================
# Transient Errors (retryable)
# ============================================================================


class TransientError(BrownBenchError):
    """Base class for transient errors that should be retried."""

    def __init__(self, message: str, retry_after_seconds: int = 60, **kwargs: Any):
        # Only set default retry_suggestion if not already provided
        if "retry_suggestion" not in kwargs:
            kwargs["retry_suggestion"] = (
                f"Retry after {retry_after_seconds} seconds with exponential backoff"
            )

        super().__init__(
            message,
            category=ErrorCategory.TRANSIENT,
            severity=ErrorSeverity.WARNING,
            is_retryable=True,
            **kwargs,
        )


class RateLimitError(TransientError):
    """Raised when API rate limit is hit.

    Should be retried after backoff period.
    """

    def __init__(self, message: str, retry_after_seconds: int = 60, **kwargs: Any):
        super().__init__(
            message,
            retry_after_seconds=retry_after_seconds,
            retry_suggestion=f"Wait {retry_after_seconds}s before retrying. Consider reducing max_requests_per_minute.",
            **kwargs,
        )


class NetworkError(TransientError):
    """Raised when network operations fail.

    Examples:
    - Connection timeout
    - DNS resolution failure
    - Socket errors
    """


# ============================================================================
# API Errors (may be retryable)
# ============================================================================


class APIError(BrownBenchError):
    """Base class for external API errors."""

    def __init__(
        self,
        message: str,
        is_retryable: bool = True,
        http_status: int | None = None,
        **kwargs: Any,
    ):
        # Only set default retry_suggestion if not already provided
        if "retry_suggestion" not in kwargs and is_retryable:
            kwargs["retry_suggestion"] = "Retry with exponential backoff (1s, 2s, 4s, 8s, 16s)"

        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.ERROR,
            is_retryable=is_retryable,
            http_status=http_status,
            **kwargs,
        )


class DUTAPIError(DUTError):
    """Raised when DUT API calls fail.

    Examples:
    - Anthropic API errors
    - HTTP 500 errors
    - Authentication failures
    """

    def __init__(self, message: str, **kwargs: Any):
        # Determine if retryable based on HTTP status
        http_status = kwargs.get("http_status")
        if "is_retryable" not in kwargs:
            # Non-retryable status codes
            kwargs["is_retryable"] = (
                http_status not in (400, 401, 403, 404) if http_status else True
            )

        if "category" not in kwargs:
            kwargs["category"] = ErrorCategory.API
        if "component" not in kwargs:
            kwargs["component"] = "DUT"
        if "operation" not in kwargs:
            kwargs["operation"] = "api_call"
        if "retry_suggestion" not in kwargs and kwargs.get("is_retryable"):
            kwargs["retry_suggestion"] = "Retry with exponential backoff (1s, 2s, 4s, 8s, 16s)"

        super().__init__(message, **kwargs)


class JudgeAPIError(APIError):
    """Raised when judge API calls fail."""

    def __init__(self, message: str, **kwargs: Any):
        if "component" not in kwargs:
            kwargs["component"] = "Judge"
        if "operation" not in kwargs:
            kwargs["operation"] = "compare"
        super().__init__(message, **kwargs)


# ============================================================================
# Data Errors (not retryable)
# ============================================================================


class DataError(BrownBenchError):
    """Base class for data-related errors."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.ERROR,
            is_retryable=False,
            **kwargs,
        )


class DUTParsingError(DUTError):
    """Raised when DUT response parsing fails.

    Examples:
    - No code blocks found in response
    - Malformed code block syntax
    - Unable to extract file paths
    """

    def __init__(self, message: str, **kwargs: Any):
        if "category" not in kwargs:
            kwargs["category"] = ErrorCategory.DATA
        if "component" not in kwargs:
            kwargs["component"] = "DUT"
        if "operation" not in kwargs:
            kwargs["operation"] = "parse_response"
        if "is_retryable" not in kwargs:
            kwargs["is_retryable"] = False
        if "retry_suggestion" not in kwargs:
            kwargs["retry_suggestion"] = (
                "Check response format and parsing logic. May indicate LLM output changed."
            )
        super().__init__(message, **kwargs)


class TaskError(DataError):
    """Raised when task loading or validation fails.

    Examples:
    - YAML parsing errors
    - Missing required fields
    - Invalid task specification
    """

    def __init__(self, message: str, **kwargs: Any):
        if "component" not in kwargs:
            kwargs["component"] = "TaskLoader"
        if "operation" not in kwargs:
            kwargs["operation"] = "load_task"
        super().__init__(message, **kwargs)


# ============================================================================
# Infrastructure Errors (may be retryable)
# ============================================================================


class InfrastructureError(BrownBenchError):
    """Base class for infrastructure errors."""

    def __init__(self, message: str, is_retryable: bool = False, **kwargs: Any):
        super().__init__(
            message,
            category=ErrorCategory.INFRASTRUCTURE,
            severity=ErrorSeverity.ERROR,
            is_retryable=is_retryable,
            **kwargs,
        )


class WorktreeError(InfrastructureError):
    """Raised when git worktree operations fail.

    Examples:
    - Failed to create worktree
    - Failed to checkout commit
    - Worktree already exists
    """

    def __init__(self, message: str, **kwargs: Any):
        # Git errors are sometimes retryable (e.g., transient lock file issues)
        if "is_retryable" not in kwargs:
            kwargs["is_retryable"] = True
        if "component" not in kwargs:
            kwargs["component"] = "GitWorktree"
        if "retry_suggestion" not in kwargs and kwargs.get("is_retryable"):
            kwargs["retry_suggestion"] = (
                "Check git repository state and retry. May need manual cleanup."
            )
        super().__init__(message, **kwargs)


class ContainerError(InfrastructureError):
    """Raised when Docker container operations fail.

    Examples:
    - Failed to build image
    - Failed to start container
    - Container crashed
    """

    def __init__(self, message: str, **kwargs: Any):
        if "is_retryable" not in kwargs:
            kwargs["is_retryable"] = False
        if "component" not in kwargs:
            kwargs["component"] = "ContainerIsolation"
        super().__init__(message, **kwargs)


class CacheError(InfrastructureError):
    """Raised when cache operations fail.

    Examples:
    - Failed to write cache file
    - Cache corruption
    - Insufficient disk space
    """

    def __init__(self, message: str, **kwargs: Any):
        if "is_retryable" not in kwargs:
            kwargs["is_retryable"] = True
        if "component" not in kwargs:
            kwargs["component"] = "SolutionCache"
        if "retry_suggestion" not in kwargs:
            kwargs["retry_suggestion"] = (
                "Check disk space and file permissions. Cache may be corrupted."
            )
        super().__init__(message, **kwargs)


# ============================================================================
# Resource Errors (not retryable without intervention)
# ============================================================================


class ResourceError(BrownBenchError):
    """Base class for resource exhaustion errors."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.ERROR,
            is_retryable=False,
            **kwargs,
        )


class BudgetExceededError(ResourceError):
    """Raised when budget limits are exceeded.

    Examples:
    - DUT exceeded cost limit
    - Tournament exceeded total budget
    """

    def __init__(self, message: str, **kwargs: Any):
        if "component" not in kwargs:
            kwargs["component"] = "BudgetEnforcer"
        if "retry_suggestion" not in kwargs:
            kwargs["retry_suggestion"] = (
                "Increase budget limits in configuration or optimize DUT to reduce costs."
            )
        super().__init__(message, **kwargs)


class DiskSpaceError(ResourceError):
    """Raised when disk space is insufficient."""

    def __init__(self, message: str, **kwargs: Any):
        if "retry_suggestion" not in kwargs:
            kwargs["retry_suggestion"] = "Free up disk space or configure larger storage."
        super().__init__(message, **kwargs)


# ============================================================================
# Validation Errors (not retryable)
# ============================================================================


class ValidationError(BrownBenchError):
    """Raised when solution validation fails.

    Examples:
    - Build failures
    - Test failures
    - Static analysis failures
    """

    def __init__(self, message: str, **kwargs: Any):
        if "component" not in kwargs:
            kwargs["component"] = "Validator"
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            is_retryable=False,
            **kwargs,
        )


class BuildError(ValidationError):
    """Raised when solution build fails."""

    def __init__(self, message: str, **kwargs: Any):
        if "operation" not in kwargs:
            kwargs["operation"] = "build"
        super().__init__(message, **kwargs)


class TestError(ValidationError):
    """Raised when solution tests fail."""

    def __init__(self, message: str, **kwargs: Any):
        if "operation" not in kwargs:
            kwargs["operation"] = "test"
        super().__init__(message, **kwargs)


# ============================================================================
# Judge Errors
# ============================================================================


class JudgeError(BrownBenchError):
    """Raised when judge evaluation fails.

    May be retryable depending on the underlying cause.
    """

    def __init__(self, message: str, **kwargs: Any):
        if "is_retryable" not in kwargs:
            kwargs["is_retryable"] = True
        if "component" not in kwargs:
            kwargs["component"] = "Judge"

        is_retryable = kwargs["is_retryable"]
        super().__init__(
            message,
            category=ErrorCategory.API if is_retryable else ErrorCategory.DATA,
            severity=ErrorSeverity.ERROR,
            **kwargs,
        )


# ============================================================================
# Tournament Errors
# ============================================================================


class TournamentError(BrownBenchError):
    """Raised when tournament execution fails.

    Examples:
    - No DUTs provided
    - No tasks provided
    - Invalid tournament configuration
    """

    def __init__(self, message: str, **kwargs: Any):
        if "component" not in kwargs:
            kwargs["component"] = "TournamentRunner"
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            is_retryable=False,
            **kwargs,
        )


# ============================================================================
# Internal Errors
# ============================================================================


class InternalError(BrownBenchError):
    """Raised for unexpected internal errors (bugs).

    These indicate programming errors and should be reported as bugs.
    """

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.CRITICAL,
            is_retryable=False,
            retry_suggestion="This is likely a bug. Please report it with full stack trace.",
            **kwargs,
        )
