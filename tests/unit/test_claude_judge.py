"""Tests for Claude judge implementation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codegen_bench.core.arena import Arena
from codegen_bench.judge.claude_judge import ClaudeJudge


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    response = MagicMock()
    response.content = [
        MagicMock(
            text="""
WINNER: A
REASONING: Solution A has better error handling and follows conventions more closely.
CONFIDENCE: 0.85
"""
        )
    ]
    return response


def test_claude_judge_init():
    """Test ClaudeJudge initialization."""
    judge = ClaudeJudge(api_key="test-key")
    assert judge.model == "claude-sonnet-4-20250514"
    assert judge.temperature == 0.3
    assert judge.variant == 0
    assert judge.api_key == "test-key"


def test_claude_judge_init_from_env():
    """Test ClaudeJudge initialization from environment."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-key"}):
        judge = ClaudeJudge()
        assert judge.api_key == "env-key"


def test_claude_judge_evaluate_no_api_key(sample_task, sample_solution):
    """Test ClaudeJudge evaluate without API key raises error."""
    from tenacity import RetryError

    judge = ClaudeJudge(api_key=None)

    with patch.dict("os.environ", {}, clear=True):
        arena = Arena(
            name="test",
            display_name="Test",
            description="Test",
            criteria=["Test"],
            prompt_template_path=Path("test.txt"),
        )

        # The retry decorator wraps the ValueError in RetryError
        with pytest.raises((ValueError, RetryError)):
            judge.evaluate(sample_solution, sample_solution, arena, sample_task)


def test_claude_judge_evaluate(sample_task, sample_solution, mock_anthropic_response):
    """Test ClaudeJudge evaluate method."""
    judge = ClaudeJudge(api_key="test-key")

    arena = Arena(
        name="maintainability",
        display_name="Maintainability",
        description="Code clarity and conventions",
        criteria=["Clear code", "Good documentation"],
        prompt_template_path=Path("maintainability.txt"),
    )

    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_client_class.return_value = mock_client

        result = judge.evaluate(sample_solution, sample_solution, arena, sample_task)

    assert result.vote == "A"
    assert "better error handling" in result.reasoning
    assert result.confidence == 0.85


def test_parse_vote_valid():
    """Test parsing valid vote response."""
    judge = ClaudeJudge(api_key="test-key")

    response = """
WINNER: B
REASONING: Solution B is more efficient and maintainable.
CONFIDENCE: 0.92
"""

    vote = judge._parse_vote(response)

    assert vote.vote == "B"
    assert "more efficient" in vote.reasoning
    assert vote.confidence == 0.92


def test_parse_vote_tie():
    """Test parsing TIE vote."""
    judge = ClaudeJudge(api_key="test-key")

    response = """
WINNER: TIE
REASONING: Both solutions are equivalent in quality.
CONFIDENCE: 0.75
"""

    vote = judge._parse_vote(response)

    assert vote.vote == "TIE"
    assert "equivalent" in vote.reasoning
    assert vote.confidence == 0.75


def test_parse_vote_missing_winner():
    """Test parsing response without winner."""
    judge = ClaudeJudge(api_key="test-key")

    response = """
REASONING: This is a good solution.
CONFIDENCE: 0.8
"""

    with pytest.raises(ValueError, match="Could not parse WINNER"):
        judge._parse_vote(response)


def test_format_solution():
    """Test solution formatting."""
    from datetime import UTC, datetime

    from codegen_bench.core.solution import Solution

    judge = ClaudeJudge(api_key="test-key")

    solution = Solution(
        approach_id="test",
        task_id="task_001",
        seed=42,
        timestamp=datetime.now(UTC),
        changed_files={
            "src/main.c": "#include <stdio.h>\nint main() { return 0; }",
            "src/utils.c": "int add(int a, int b) { return a + b; }",
        },
    )

    formatted = judge._format_solution(solution)

    assert "File: src/main.c" in formatted
    assert "#include <stdio.h>" in formatted
    assert "File: src/utils.c" in formatted
    assert "int add" in formatted


def test_format_solution_empty():
    """Test formatting empty solution."""
    from datetime import UTC, datetime

    from codegen_bench.core.solution import Solution

    judge = ClaudeJudge(api_key="test-key")

    solution = Solution(
        approach_id="test",
        task_id="task_001",
        seed=42,
        timestamp=datetime.now(UTC),
        changed_files={},
    )

    formatted = judge._format_solution(solution)

    assert formatted == "(No files changed)"
