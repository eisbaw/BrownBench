"""Tests for ElaboratePromptDUT."""

import pytest
from unittest.mock import Mock, MagicMock
from codegen_bench.core.task import Task
from codegen_bench.dut.elaborate_prompt import ElaboratePromptDUT


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = Mock()
    message = Mock()
    message.content = [Mock(text='```python:test.py\nprint("hello")\n```')]
    message.usage = Mock(input_tokens=100, output_tokens=50)
    client.messages.create = Mock(return_value=message)
    return client


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return Task(
        id="test_elaborate",
        name="Test Task",
        project="test_project",
        domain="testing",
        difficulty="easy",
        codebase_path="test_project",
        specification="Add a test function",
        constraints=["Must use pytest", "Must be concise"],
        key_files=["test.py"],
        gotchas=["Don't forget imports", "Handle edge cases"],
    )


def test_elaborate_prompt_metadata():
    """Test ElaboratePromptDUT metadata."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})
    metadata = dut.get_metadata()

    assert metadata.id == "elaborate-prompt"
    assert metadata.name == "Elaborate Prompt"
    assert "Enhanced" in metadata.description
    assert metadata.version == "1.0.0"


def test_elaborate_prompt_build_prompt(sample_task):
    """Test that ElaboratePromptDUT builds detailed prompts."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})
    prompt = dut._build_prompt(sample_task)

    # Check for enhanced content
    assert "expert software engineer" in prompt.lower()
    assert "CRITICAL PRINCIPLES" in prompt
    assert "MAINTAINABILITY" in prompt
    assert "CORRECTNESS" in prompt

    # Check task details included
    assert sample_task.name in prompt
    assert sample_task.specification in prompt
    assert "Must use pytest" in prompt
    assert "Don't forget imports" in prompt
    assert "test.py" in prompt

    # Check for workflow guidance
    assert "WORKFLOW" in prompt or "Analyze" in prompt


def test_elaborate_prompt_solve(mock_anthropic_client, sample_task):
    """Test ElaboratePromptDUT solve method."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})
    dut.client = mock_anthropic_client

    solution = dut.solve(sample_task, seed=42)

    # Verify API was called
    assert mock_anthropic_client.messages.create.called

    # Check call arguments
    call_args = mock_anthropic_client.messages.create.call_args
    assert call_args[1]["model"]
    assert call_args[1]["max_tokens"]

    # Verify prompt is elaborate
    messages = call_args[1]["messages"]
    user_message = messages[0]["content"]
    assert "CRITICAL PRINCIPLES" in user_message
    assert len(user_message) > 200  # Should be detailed

    # Verify solution
    assert solution.approach_id == "elaborate-prompt"
    assert solution.task_id == sample_task.id


def test_elaborate_prompt_inherits_from_simple_chat():
    """Test that ElaboratePromptDUT properly inherits from SimpleChatDUT."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})

    # Should have same methods as SimpleChatDUT
    assert hasattr(dut, "solve")
    assert hasattr(dut, "_parse_code_changes")
    assert hasattr(dut, "_calculate_cost")

    # But overrides _build_prompt
    assert dut._build_prompt.__qualname__.startswith("ElaboratePromptDUT")
