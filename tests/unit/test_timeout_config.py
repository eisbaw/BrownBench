"""Unit tests for timeout configuration in DUTs."""

import pytest

from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.dut.elaborate_prompt import ElaboratePromptDUT
from codegen_bench.exceptions import DUTConfigError


def test_simple_chat_default_timeout():
    """Test SimpleChatDUT uses default timeout."""
    config = {"api_key": "test-key", "model": "claude-3-sonnet-20241022"}
    dut = SimpleChatDUT(config)
    assert dut.timeout_seconds == 300  # Default from base class


def test_simple_chat_custom_timeout():
    """Test SimpleChatDUT accepts custom timeout."""
    config = {
        "api_key": "test-key",
        "model": "claude-3-sonnet-20241022",
        "timeout_seconds": 600,  # 10 minutes
    }
    dut = SimpleChatDUT(config)
    assert dut.timeout_seconds == 600


def test_simple_chat_invalid_timeout_negative():
    """Test SimpleChatDUT rejects negative timeout."""
    config = {"api_key": "test-key", "model": "claude-3-sonnet-20241022", "timeout_seconds": -10}
    with pytest.raises(DUTConfigError, match="timeout_seconds must be a positive integer"):
        SimpleChatDUT(config)


def test_simple_chat_invalid_timeout_zero():
    """Test SimpleChatDUT rejects zero timeout."""
    config = {"api_key": "test-key", "model": "claude-3-sonnet-20241022", "timeout_seconds": 0}
    with pytest.raises(DUTConfigError, match="timeout_seconds must be a positive integer"):
        SimpleChatDUT(config)


def test_simple_chat_invalid_timeout_string():
    """Test SimpleChatDUT rejects non-integer timeout."""
    config = {"api_key": "test-key", "model": "claude-3-sonnet-20241022", "timeout_seconds": "300"}
    with pytest.raises(DUTConfigError, match="timeout_seconds must be a positive integer"):
        SimpleChatDUT(config)


def test_elaborate_prompt_default_timeout():
    """Test ElaboratePromptDUT uses default timeout."""
    config = {"api_key": "test-key", "model": "claude-3-sonnet-20241022"}
    dut = ElaboratePromptDUT(config)
    assert dut.timeout_seconds == 300  # Default from base class


def test_elaborate_prompt_custom_timeout():
    """Test ElaboratePromptDUT accepts custom timeout."""
    config = {
        "api_key": "test-key",
        "model": "claude-3-sonnet-20241022",
        "timeout_seconds": 900,  # 15 minutes
        "include_codebase_context": True,
        "max_context_files": 10,
    }
    dut = ElaboratePromptDUT(config)
    assert dut.timeout_seconds == 900
    assert dut.include_codebase_context is True
    assert dut.max_context_files == 10


def test_elaborate_prompt_inherits_validation():
    """Test ElaboratePromptDUT inherits timeout validation from base."""
    config = {"api_key": "test-key", "model": "claude-3-sonnet-20241022", "timeout_seconds": -1}
    with pytest.raises(DUTConfigError, match="timeout_seconds must be a positive integer"):
        ElaboratePromptDUT(config)
