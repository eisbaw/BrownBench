"""Tests for judge base classes."""

from codegen_bench.core.arena import Arena
from codegen_bench.core.judgment import JudgeVote
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.judge.base import Judge


class MockJudge(Judge):
    """Mock judge for testing."""

    def __init__(self, vote: str = "A", confidence: float = 0.9):
        super().__init__(model="mock-model", temperature=0.3, variant=0)
        self.mock_vote = vote
        self.mock_confidence = confidence

    def evaluate(
        self, solution_a: Solution, solution_b: Solution, arena: Arena, task: Task
    ) -> JudgeVote:
        return JudgeVote(
            vote=self.mock_vote,  # type: ignore[arg-type]
            reasoning="Mock reasoning",
            confidence=self.mock_confidence,
        )


def test_judge_initialization():
    """Test judge initialization."""
    judge = MockJudge()
    assert judge.model == "mock-model"
    assert judge.temperature == 0.3
    assert judge.variant == 0


def test_judge_string_representation():
    """Test judge string representation."""
    judge = MockJudge()
    assert str(judge) == "Judge(mock-model, variant=0)"


def test_judge_evaluate(sample_task, sample_solution):
    """Test judge evaluate method."""
    from pathlib import Path

    judge = MockJudge(vote="A", confidence=0.85)

    arena = Arena(
        name="test",
        display_name="Test Arena",
        description="Test description",
        criteria=["Test criterion"],
        prompt_template_path=Path("test.txt"),
    )

    result = judge.evaluate(sample_solution, sample_solution, arena, sample_task)

    assert result.vote == "A"
    assert result.reasoning == "Mock reasoning"
    assert result.confidence == 0.85
