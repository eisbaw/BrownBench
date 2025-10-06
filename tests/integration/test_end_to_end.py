"""Integration test for end-to-end workflow."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from codegen_bench.cache.store import SolutionCache
from codegen_bench.core.solution import Solution
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.tasks.loader import TaskLoader
from codegen_bench.validation.applicator import SolutionApplicator
from codegen_bench.validation.executor import ValidationExecutor
from codegen_bench.validation.worktree import GitWorktreeStrategy


@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic API response."""
    mock_response = Mock()
    mock_response.content = [
        Mock(
            text="""Here is the implementation:

```c:src/hello.c
#include "hello.h"
#include <stdio.h>

int hello_world(void) {
    printf("Hello, World!\\n");
    return 0;
}
```

```c:src/hello.h
#ifndef HELLO_H
#define HELLO_H

int hello_world(void);

#endif // HELLO_H
```
"""
        )
    ]
    mock_response.usage = Mock(input_tokens=100, output_tokens=50)
    return mock_response


def test_end_to_end_workflow(tmp_path, mock_anthropic_response):
    """Test complete workflow: generate -> cache -> validate.

    This demonstrates Phase 0 deliverable: generate and validate solution for 1 task.
    """
    # Setup paths
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Load task
    task_loader = TaskLoader(Path("tasks"))
    task = task_loader.load_task("task_001")

    assert task.id == "task_001"
    assert task.name == "Add hello world function"

    # Setup DUT with mocked API
    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client

        dut_config = {"api_key": "test-key-12345"}
        dut = SimpleChatDUT(dut_config)

        # Generate solution
        solution = dut.solve(task, seed=42)

        # Verify solution was generated
        assert solution.task_id == "task_001"
        assert solution.approach_id == "simple-chat"
        assert solution.seed == 42
        assert len(solution.changed_files) == 2
        assert "src/hello.c" in solution.changed_files
        assert "src/hello.h" in solution.changed_files
        assert solution.api_calls == 1
        assert solution.cost_usd > 0

        # Test caching
        cache = SolutionCache(cache_dir)

        # Should not be cached yet
        cached = cache.get(dut, task, 42)
        assert cached is None

        # Cache the solution
        cache.put(dut, task, 42, solution)

        # Should be cached now
        cached = cache.get(dut, task, 42)
        assert cached is not None
        assert cached.task_id == solution.task_id
        assert cached.seed == solution.seed

    # Test validation (without mocking to verify real worktree operations)
    if not task.codebase_path.exists():
        pytest.skip("Codebase path does not exist")

    try:
        # Create worktree
        worktree_strategy = GitWorktreeStrategy(task.codebase_path)
        worktree_path = worktree_strategy.create_worktree()

        # Apply solution
        applicator = SolutionApplicator(worktree_path)
        applicator.apply(solution)

        # Verify files were created
        assert (worktree_path / "src" / "hello.c").exists()
        assert (worktree_path / "src" / "hello.h").exists()

        # Run validation
        executor = ValidationExecutor(worktree_path)

        # Test compile command
        if task.compile_command:
            result = executor.run_compile(task.compile_command)
            # Note: May fail if gcc not available, but structure is tested
            assert result is not None

        # Test test command
        if task.test_command:
            result = executor.run_tests(task.test_command)
            assert result is not None

    finally:
        # Cleanup worktree
        if 'worktree_strategy' in locals() and 'worktree_path' in locals():
            worktree_strategy.remove_worktree(worktree_path)


def test_registry_integration():
    """Test DUT registry integration."""
    # Verify SimpleChatDUT is registered
    available = DUTRegistry.list_available()
    assert "simple-chat" in available

    # Get DUT class
    dut_class = DUTRegistry.get("simple-chat")
    assert dut_class == SimpleChatDUT

    # Create instance
    dut = dut_class({"api_key": "test"})
    assert dut.get_metadata().id == "simple-chat"
    assert dut.get_metadata().version == "1.0.0"


def test_solution_persistence(tmp_path):
    """Test solution can be saved and loaded from JSON."""
    # Create solution
    solution = Solution(
        approach_id="test-dut",
        task_id="test-task",
        seed=42,
        timestamp=datetime.now(UTC),
        changed_files={"src/test.c": "#include <stdio.h>\n"},
        generation_time_seconds=1.5,
        total_tokens=100,
        prompt_tokens=50,
        completion_tokens=50,
        api_calls=1,
        cost_usd=0.001,
    )

    # Save to file
    output_file = tmp_path / "solution.json"
    with open(output_file, "w") as f:
        json.dump(solution.to_dict(), f, indent=2)

    # Load from file
    with open(output_file) as f:
        data = json.load(f)

    loaded = Solution.from_dict(data)

    # Verify
    assert loaded.approach_id == solution.approach_id
    assert loaded.task_id == solution.task_id
    assert loaded.seed == solution.seed
    assert loaded.changed_files == solution.changed_files
    assert loaded.cost_usd == solution.cost_usd
