"""Tests for Arena."""

from pathlib import Path

from codegen_bench.core.arena import (
    ALL_ARENAS,
    ARCHITECTURAL_INTEGRITY,
    MAINTAINABILITY,
    PERFORMANCE,
    SAFETY,
    SURGICAL_PRECISION,
    TESTABILITY,
    Arena,
)


def test_arena_creation():
    """Test Arena dataclass creation."""
    arena = Arena(
        name="test",
        display_name="Test Arena",
        description="Test description",
        criteria=["criterion1", "criterion2"],
        prompt_template_path=Path("test/path.txt"),
    )

    assert arena.name == "test"
    assert arena.display_name == "Test Arena"
    assert arena.description == "Test description"
    assert arena.criteria == ["criterion1", "criterion2"]
    assert arena.prompt_template_path == Path("test/path.txt")


def test_builtin_arenas_defined():
    """Test that all built-in arenas are defined."""
    assert MAINTAINABILITY is not None
    assert ARCHITECTURAL_INTEGRITY is not None
    assert SURGICAL_PRECISION is not None
    assert TESTABILITY is not None
    assert PERFORMANCE is not None
    assert SAFETY is not None


def test_all_arenas_list():
    """Test that ALL_ARENAS contains all built-in arenas."""
    assert len(ALL_ARENAS) == 6
    assert MAINTAINABILITY in ALL_ARENAS
    assert ARCHITECTURAL_INTEGRITY in ALL_ARENAS
    assert SURGICAL_PRECISION in ALL_ARENAS
    assert TESTABILITY in ALL_ARENAS
    assert PERFORMANCE in ALL_ARENAS
    assert SAFETY in ALL_ARENAS


def test_arena_names_unique():
    """Test that all arena names are unique."""
    names = [arena.name for arena in ALL_ARENAS]
    assert len(names) == len(set(names))


def test_load_prompt_maintainability():
    """Test loading maintainability arena prompt."""
    prompt = MAINTAINABILITY.load_prompt(
        task_spec="Implement feature X",
        constraints="Must be thread-safe\nMust use existing API",
        solution_a="Solution A code here",
        solution_b="Solution B code here",
    )

    # Check prompt structure
    assert "Implement feature X" in prompt
    assert "Must be thread-safe" in prompt
    assert "Must use existing API" in prompt
    assert "Solution A code here" in prompt
    assert "Solution B code here" in prompt
    assert "WINNER:" in prompt
    assert "REASONING:" in prompt
    assert "CONFIDENCE:" in prompt
    assert "Maintainability" in prompt or "maintainability" in prompt


def test_load_prompt_architecture():
    """Test loading architecture arena prompt."""
    prompt = ARCHITECTURAL_INTEGRITY.load_prompt(
        task_spec="Refactor module Y",
        constraints="Maintain backward compatibility",
        solution_a="Arch solution A",
        solution_b="Arch solution B",
    )

    assert "Refactor module Y" in prompt
    assert "Maintain backward compatibility" in prompt
    assert "Arch solution A" in prompt
    assert "Arch solution B" in prompt
    assert "WINNER:" in prompt


def test_load_prompt_surgical_precision():
    """Test loading surgical precision arena prompt."""
    prompt = SURGICAL_PRECISION.load_prompt(
        task_spec="Fix bug in parser",
        constraints="No breaking changes",
        solution_a="Minimal fix",
        solution_b="Large refactor",
    )

    assert "Fix bug in parser" in prompt
    assert "No breaking changes" in prompt
    assert "Minimal fix" in prompt
    assert "Large refactor" in prompt
    assert "WINNER:" in prompt


def test_load_prompt_testability():
    """Test loading testability arena prompt."""
    prompt = TESTABILITY.load_prompt(
        task_spec="Add validation logic",
        constraints="100% test coverage required",
        solution_a="Solution with tests",
        solution_b="Solution without tests",
    )

    assert "Add validation logic" in prompt
    assert "100% test coverage required" in prompt
    assert "Solution with tests" in prompt
    assert "Solution without tests" in prompt


def test_load_prompt_performance():
    """Test loading performance arena prompt."""
    prompt = PERFORMANCE.load_prompt(
        task_spec="Optimize search algorithm",
        constraints="O(n log n) or better",
        solution_a="O(n) solution",
        solution_b="O(n^2) solution",
    )

    assert "Optimize search algorithm" in prompt
    assert "O(n log n) or better" in prompt
    assert "O(n) solution" in prompt
    assert "O(n^2) solution" in prompt


def test_load_prompt_safety():
    """Test loading safety arena prompt."""
    prompt = SAFETY.load_prompt(
        task_spec="Handle user input",
        constraints="Must sanitize all inputs",
        solution_a="Safe solution",
        solution_b="Unsafe solution",
    )

    assert "Handle user input" in prompt
    assert "Must sanitize all inputs" in prompt
    assert "Safe solution" in prompt
    assert "Unsafe solution" in prompt


def test_all_prompts_contain_required_sections():
    """Test that all arena prompts contain required output format."""
    for arena in ALL_ARENAS:
        prompt = arena.load_prompt(
            task_spec="Test task",
            constraints="Test constraints",
            solution_a="Test solution A",
            solution_b="Test solution B",
        )

        # All prompts must specify output format
        assert "WINNER:" in prompt
        assert "REASONING:" in prompt
        assert "CONFIDENCE:" in prompt

        # All prompts must contain the input parameters
        assert "Test task" in prompt
        assert "Test constraints" in prompt
        assert "Test solution A" in prompt
        assert "Test solution B" in prompt


def test_arena_criteria_nonempty():
    """Test that all arenas have non-empty criteria lists."""
    for arena in ALL_ARENAS:
        assert len(arena.criteria) > 0
        assert all(len(c) > 0 for c in arena.criteria)


def test_arena_descriptions_nonempty():
    """Test that all arenas have non-empty descriptions."""
    for arena in ALL_ARENAS:
        assert len(arena.description) > 0
        assert len(arena.display_name) > 0
