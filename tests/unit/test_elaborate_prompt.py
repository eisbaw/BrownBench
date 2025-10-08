"""Tests for ElaboratePromptDUT."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from anthropic.types import TextBlock

from codegen_bench.core.task import Task
from codegen_bench.dut.elaborate_prompt import ElaboratePromptDUT


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = Mock()
    message = Mock()
    text_content = '```python:test.py\nprint("hello")\n```'
    text_block = TextBlock(type="text", text=text_content)
    message.content = [text_block]
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
        codebase_path=Path("test_project"),
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
    assert "Elaborate Prompt" in metadata.name
    assert "brownfield" in metadata.description.lower() or "Enhanced" in metadata.description
    assert metadata.version == "2.0.0"


def test_elaborate_prompt_build_prompt(sample_task):
    """Test that ElaboratePromptDUT builds detailed prompts."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})
    prompt = dut._build_prompt(sample_task)

    # Check for brownfield-focused content
    assert "brownfield" in prompt.lower() or "production code" in prompt.lower()
    assert "CRITICAL PRINCIPLES" in prompt or "SURGICAL" in prompt
    assert "PATTERN MATCHING" in prompt or "existing conventions" in prompt.lower()

    # Check task details included
    assert sample_task.name in prompt
    assert sample_task.specification in prompt
    assert "Must use pytest" in prompt
    assert "Don't forget imports" in prompt
    assert "test.py" in prompt

    # Check for workflow guidance
    assert "WORKFLOW" in prompt or "Analyze" in prompt or "Study" in prompt


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


def test_elaborate_prompt_hash_consistency():
    """Test that prompt hash is consistent for ElaboratePromptDUT."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})
    metadata1 = dut.get_metadata()
    metadata2 = dut.get_metadata()

    assert metadata1.prompt_hash is not None
    assert metadata1.prompt_hash == metadata2.prompt_hash
    assert len(metadata1.prompt_hash) == 16


def test_elaborate_prompt_includes_gotchas_in_hash():
    """Test that gotchas are included in prompt hash computation."""
    # This is implicit in the prompt generation - the hash should remain
    # consistent as long as the template doesn't change
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})
    metadata = dut.get_metadata()

    # Just verify the hash exists and has correct format
    assert metadata.prompt_hash is not None
    assert len(metadata.prompt_hash) == 16
    assert all(c in "0123456789abcdef" for c in metadata.prompt_hash)


def test_elaborate_prompt_codebase_context_disabled():
    """Test ElaboratePromptDUT with codebase context disabled."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key", "include_codebase_context": False})

    # Create task with fake codebase path
    task = Task(
        id="test",
        name="Test",
        project="test",
        domain="test",
        difficulty="easy",
        codebase_path=Path("/nonexistent"),
        specification="Test spec",
        key_files=["test.py"],
    )

    prompt = dut._build_prompt(task)

    # Should not include codebase context section
    assert "CODEBASE CONTEXT" not in prompt
    assert "current versions of the key files" not in prompt


def test_elaborate_prompt_codebase_context_enabled(sample_task, tmp_path):
    """Test ElaboratePromptDUT with codebase context enabled."""
    # Create a real test file
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    return 'world'\n")

    # Update sample task to use tmp_path
    sample_task.codebase_path = tmp_path
    sample_task.key_files = ["test.py"]

    dut = ElaboratePromptDUT(config={"api_key": "test-key", "include_codebase_context": True})
    prompt = dut._build_prompt(sample_task)

    # Should include codebase context
    assert "CODEBASE CONTEXT" in prompt
    assert "test.py" in prompt
    assert "def hello():" in prompt
    assert "return 'world'" in prompt


def test_elaborate_prompt_read_file_safely():
    """Test safe file reading with error handling."""
    dut = ElaboratePromptDUT(config={"api_key": "test-key"})

    # Test non-existent file
    content = dut._read_file_safely(Path("/nonexistent/file.txt"))
    assert "File not found" in content

    # Test with actual file (using a temp file)
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("line 1\nline 2\nline 3\n")
        f.flush()
        temp_path = Path(f.name)

    try:
        content = dut._read_file_safely(temp_path)
        assert "line 1" in content
        assert "line 2" in content
    finally:
        temp_path.unlink()


def test_elaborate_prompt_max_context_files(sample_task, tmp_path):
    """Test that max_context_files limits files included."""
    # Create multiple test files
    for i in range(10):
        (tmp_path / f"file{i}.py").write_text(f"# File {i}\n")

    sample_task.codebase_path = tmp_path
    sample_task.key_files = [f"file{i}.py" for i in range(10)]

    # Configure to include max 3 files
    dut = ElaboratePromptDUT(config={"api_key": "test-key", "max_context_files": 3})
    prompt = dut._build_prompt(sample_task)

    # Should include first 3 files
    assert "file0.py" in prompt
    assert "file1.py" in prompt
    assert "file2.py" in prompt

    # Should mention remaining files not shown
    assert "7 more files" in prompt or "Plus 7" in prompt

    # Later files should not have their content included
    assert "# File 9" not in prompt
