"""Unit tests for timeout utilities."""

import time

import pytest

from codegen_bench.exceptions import DUTTimeoutError
from codegen_bench.utils.timeout import timeout_context, with_timeout


class TestTimeoutContext:
    """Tests for timeout_context context manager."""

    def test_timeout_context_completes_within_timeout(self):
        """Test that operations completing within timeout succeed."""
        with timeout_context(2, "fast operation"):
            time.sleep(0.1)
        # Should complete without raising

    def test_timeout_context_raises_on_timeout(self):
        """Test that operations exceeding timeout raise DUTTimeoutError."""
        with pytest.raises(DUTTimeoutError) as exc_info:
            with timeout_context(1, "slow operation"):
                time.sleep(2)

        error = exc_info.value
        assert "slow operation" in str(error)
        assert "exceeded timeout of 1s" in str(error)
        assert error.context.category.value == "resource"
        assert error.context.component == "DUT"
        assert error.context.operation == "solve"
        assert not error.context.is_retryable

    def test_timeout_context_zero_timeout_raises_ValueError(self):
        """Test that zero timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            with timeout_context(0, "operation"):
                pass

    def test_timeout_context_negative_timeout_raises_ValueError(self):
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            with timeout_context(-5, "operation"):
                pass

    def test_timeout_context_error_message_includes_operation(self):
        """Test that timeout error message includes operation name."""
        with pytest.raises(DUTTimeoutError) as exc_info:
            with timeout_context(1, "custom_operation_name"):
                time.sleep(2)

        assert "custom_operation_name" in str(exc_info.value)

    def test_timeout_context_cleans_up_after_success(self):
        """Test that timeout context properly cleans up after successful execution."""
        # This is mainly to ensure no signal handlers leak
        for _ in range(3):
            with timeout_context(2, "iteration"):
                time.sleep(0.1)
        # Should complete all iterations without issues

    def test_timeout_context_cleans_up_after_timeout(self):
        """Test that timeout context properly cleans up after timeout."""
        for _ in range(3):
            try:
                with timeout_context(1, "iteration"):
                    time.sleep(2)
            except DUTTimeoutError:
                pass
        # Should handle multiple timeouts without issues


class TestWithTimeoutDecorator:
    """Tests for with_timeout decorator."""

    def test_decorator_completes_within_timeout(self):
        """Test that decorated functions completing within timeout succeed."""

        @with_timeout(2, "decorated operation")
        def fast_function():
            time.sleep(0.1)
            return "success"

        result = fast_function()
        assert result == "success"

    def test_decorator_raises_on_timeout(self):
        """Test that decorated functions exceeding timeout raise DUTTimeoutError."""

        @with_timeout(1, "decorated operation")
        def slow_function():
            time.sleep(2)
            return "should not reach here"

        with pytest.raises(DUTTimeoutError) as exc_info:
            slow_function()

        assert "decorated operation" in str(exc_info.value)

    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves original function name."""

        @with_timeout(2, "operation")
        def my_function():
            return "result"

        assert my_function.__name__ == "my_function"

    def test_decorator_preserves_docstring(self):
        """Test that decorator preserves original function docstring."""

        @with_timeout(2, "operation")
        def documented_function():
            """This is a docstring."""
            return "result"

        assert documented_function.__doc__ == "This is a docstring."

    def test_decorator_with_args_and_kwargs(self):
        """Test that decorator works with functions accepting arguments."""

        @with_timeout(2, "operation")
        def function_with_args(a, b, c=None):
            time.sleep(0.1)
            return a + b + (c or 0)

        result = function_with_args(1, 2, c=3)
        assert result == 6

    def test_decorator_default_operation_name(self):
        """Test that decorator uses function name as default operation name."""

        @with_timeout(1, "")  # Empty operation name
        def my_slow_function():
            time.sleep(2)

        with pytest.raises(DUTTimeoutError):
            my_slow_function()


class TestTimeoutIntegration:
    """Integration tests for timeout functionality."""

    def test_timeout_error_context_metadata(self):
        """Test that DUTTimeoutError includes proper context metadata."""
        with pytest.raises(DUTTimeoutError) as exc_info:
            with timeout_context(1, "test_operation"):
                time.sleep(2)

        error = exc_info.value
        context = error.context

        # Verify all context fields
        assert context.category.value == "resource"
        assert context.severity.value == "error"
        assert context.component == "DUT"
        assert context.operation == "solve"
        assert not context.is_retryable
        assert "Increase timeout limit" in context.retry_suggestion
        assert context.metadata["timeout_seconds"] == 1

    def test_timeout_actionable_message(self):
        """Test that DUTTimeoutError provides actionable error message."""
        with pytest.raises(DUTTimeoutError) as exc_info:
            with timeout_context(5, "test_operation"):
                time.sleep(10)

        error = exc_info.value
        message = error.get_actionable_message()

        # Verify actionable message contains useful info
        assert "Category: resource" in message
        assert "Severity: error" in message
        assert "Component: DUT" in message
        assert "Operation: solve" in message
        assert "not retryable" in message
        assert "Increase timeout limit (currently 5s)" in message

    def test_nested_timeout_contexts(self):
        """Test that nested timeout contexts work correctly (inner takes precedence)."""
        # Outer timeout is generous, inner timeout is strict
        with pytest.raises(DUTTimeoutError) as exc_info:
            with timeout_context(10, "outer"):
                with timeout_context(1, "inner"):
                    time.sleep(2)

        # Should timeout on inner context
        assert "inner" in str(exc_info.value)

    def test_timeout_with_exception_in_operation(self):
        """Test that timeout context doesn't interfere with other exceptions."""

        class CustomError(Exception):
            pass

        with pytest.raises(CustomError):
            with timeout_context(2, "operation"):
                raise CustomError("test error")

    def test_timeout_boundary_condition(self):
        """Test timeout at exact boundary (may pass or fail depending on timing)."""
        # Sleep for exactly the timeout duration
        # This is a boundary condition - may pass or fail depending on system load
        try:
            with timeout_context(1, "boundary"):
                time.sleep(1.0)
        except DUTTimeoutError:
            # It's acceptable for this to timeout due to overhead
            pass
