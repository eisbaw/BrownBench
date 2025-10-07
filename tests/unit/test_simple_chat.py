"""Tests for SimpleChatDUT."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from codegen_bench.core.task import Task
from codegen_bench.dut.simple_chat import SimpleChatDUT


@pytest.fixture
def mock_anthropic_client(monkeypatch):
    """Mock Anthropic client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [
        Mock(
            text="""Here's the solution:

```c:src/main.c
#include <stdio.h>

int main() {
    printf("Hello, world!\\n");
    return 0;
}
```

```c:src/helper.c
void helper() {
    // Helper function
}
```
"""
        )
    ]
    mock_response.usage = Mock(input_tokens=100, output_tokens=200)
    mock_client.messages.create = Mock(return_value=mock_response)

    # Monkey-patch the Anthropic class
    mock_anthropic_class = Mock(return_value=mock_client)
    monkeypatch.setattr("codegen_bench.dut.simple_chat.anthropic.Anthropic", mock_anthropic_class)

    return mock_client


@pytest.fixture
def simple_task(tmp_path):
    """Create a simple task for testing."""
    return Task(
        id="test_task_001",
        name="Add hello world",
        project="test-project",
        domain="testing",
        difficulty="easy",
        codebase_path=tmp_path / "codebase",
        specification="Add a hello world program in C",
        constraints=["Must use stdio.h", "Return 0 on success"],
        key_files=["src/main.c"],
    )


def test_simple_chat_init_with_api_key():
    """Test SimpleChatDUT initialization with explicit API key."""
    dut = SimpleChatDUT(config={"api_key": "test-key"})
    assert dut.model == "claude-sonnet-4-20250514"
    assert dut.max_tokens == 8000
    assert dut.temperature == 0.3


def test_simple_chat_init_with_custom_config():
    """Test SimpleChatDUT initialization with custom config."""
    dut = SimpleChatDUT(
        config={
            "api_key": "test-key",
            "model": "claude-opus-4-20250514",
            "max_tokens": 4000,
            "temperature": 0.5,
        }
    )
    assert dut.model == "claude-opus-4-20250514"
    assert dut.max_tokens == 4000
    assert dut.temperature == 0.5


def test_simple_chat_solve_no_api_key(monkeypatch, simple_task):
    """Test SimpleChatDUT solve fails without API key."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    dut = SimpleChatDUT(config={})
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
        dut.solve(simple_task, seed=42)


def test_simple_chat_solve(mock_anthropic_client, simple_task):
    """Test SimpleChatDUT solve method."""
    dut = SimpleChatDUT(config={"api_key": "test-key"})
    solution = dut.solve(simple_task, seed=42)

    # Verify solution structure
    assert solution.approach_id == "simple-chat"
    assert solution.task_id == "test_task_001"
    assert solution.seed == 42
    assert isinstance(solution.timestamp, datetime)

    # Verify code changes were parsed
    assert len(solution.changed_files) == 2
    assert "src/main.c" in solution.changed_files
    assert "src/helper.c" in solution.changed_files
    assert "printf" in solution.changed_files["src/main.c"]

    # Verify metrics
    assert solution.api_calls == 1
    assert solution.total_tokens == 300
    assert solution.prompt_tokens == 100
    assert solution.completion_tokens == 200
    assert solution.cost_usd > 0
    assert solution.generation_time_seconds >= 0

    # Verify API was called
    mock_anthropic_client.messages.create.assert_called_once()


def test_simple_chat_build_prompt(simple_task):
    """Test prompt building."""
    dut = SimpleChatDUT(config={"api_key": "test-key"})
    prompt = dut._build_prompt(simple_task)

    assert "Add hello world" in prompt
    assert "Add a hello world program in C" in prompt
    assert "Must use stdio.h" in prompt
    assert "Return 0 on success" in prompt
    assert "src/main.c" in prompt


def test_simple_chat_parse_code_changes():
    """Test code change parsing."""
    dut = SimpleChatDUT(config={"api_key": "test-key"})

    response = """Here is my solution:

```c:src/main.c
int main() {
    return 0;
}
```

Some explanation text here.

```python:test.py
def test():
    pass
```
"""
    changed_files = dut._parse_code_changes(response)

    assert len(changed_files) == 2
    assert "src/main.c" in changed_files
    assert "test.py" in changed_files
    assert "int main()" in changed_files["src/main.c"]
    assert "def test():" in changed_files["test.py"]


def test_simple_chat_parse_code_no_changes():
    """Test parsing with no code blocks."""
    dut = SimpleChatDUT(config={"api_key": "test-key"})
    response = "Just some text without code blocks."
    changed_files = dut._parse_code_changes(response)
    assert len(changed_files) == 0


def test_simple_chat_calculate_cost():
    """Test cost calculation."""
    dut = SimpleChatDUT(config={"api_key": "test-key"})

    # Test with known values
    cost = dut._calculate_cost(1000, 2000)
    # 1000 * 0.003 / 1000 + 2000 * 0.015 / 1000 = 0.003 + 0.030 = 0.033
    assert cost == pytest.approx(0.033, abs=0.001)


def test_simple_chat_get_metadata():
    """Test metadata retrieval."""
    dut = SimpleChatDUT(config={"api_key": "test-key", "model": "claude-opus-4-20250514"})
    metadata = dut.get_metadata()

    assert metadata.id == "simple-chat"
    assert metadata.name == "Simple Chat"
    assert metadata.version == "1.0.0"
    assert metadata.model == "claude-opus-4-20250514"
    assert metadata.provider == "anthropic"


def test_simple_chat_string_representation():
    """Test string representation."""
    dut = SimpleChatDUT(config={"api_key": "test-key"})
    assert str(dut) == "Simple Chat (v1.0.0)"
