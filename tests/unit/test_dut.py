"""Tests for DUT base classes and registry."""

import pytest

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.exceptions import DUTError


class MockDUT(CodeGenerationApproach):
    """Mock DUT for testing."""

    APPROACH_ID = "mock-dut"

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate mock solution."""
        return Solution(
            approach_id="mock-dut",
            task_id=task.id,
            seed=seed,
            changed_files={"test.py": "# mock code"},
        )

    def get_metadata(self) -> ApproachMetadata:
        """Return mock metadata."""
        return ApproachMetadata(
            id="mock-dut",
            name="Mock DUT",
            description="Mock for testing",
            version="1.0.0",
        )


def test_approach_metadata_creation() -> None:
    """Test creating approach metadata."""
    metadata = ApproachMetadata(
        id="test-dut",
        name="Test DUT",
        description="Test approach",
        version="1.0.0",
        model="claude-sonnet-4",
        provider="anthropic",
    )
    assert metadata.id == "test-dut"
    assert metadata.model == "claude-sonnet-4"


def test_dut_string_representation(sample_task_dict: dict) -> None:
    """Test DUT string representation."""
    dut = MockDUT(config={})
    assert str(dut) == "Mock DUT (v1.0.0)"


def test_dut_solve(sample_task_dict: dict) -> None:
    """Test DUT solve method."""
    dut = MockDUT(config={})
    task = Task(**sample_task_dict)
    solution = dut.solve(task, seed=42)
    assert solution.approach_id == "mock-dut"
    assert solution.task_id == task.id
    assert solution.seed == 42


def test_registry_register() -> None:
    """Test registering a DUT."""
    DUTRegistry.clear()
    DUTRegistry.register(MockDUT)
    assert "mock-dut" in DUTRegistry.list_available()
    DUTRegistry.clear()


def test_registry_register_decorator() -> None:
    """Test using registry as decorator."""
    DUTRegistry.clear()

    @DUTRegistry.register
    class DecoratorDUT(CodeGenerationApproach):
        APPROACH_ID = "decorator-dut"

        def solve(self, task: Task, seed: int) -> Solution:
            return Solution(
                approach_id="decorator-dut",
                task_id=task.id,
                seed=seed,
            )

        def get_metadata(self) -> ApproachMetadata:
            return ApproachMetadata(
                id="decorator-dut",
                name="Decorator DUT",
                description="Test",
                version="1.0.0",
            )

    assert "decorator-dut" in DUTRegistry.list_available()
    DUTRegistry.clear()


def test_registry_get() -> None:
    """Test getting DUT by ID."""
    DUTRegistry.clear()
    DUTRegistry.register(MockDUT)
    dut_class = DUTRegistry.get("mock-dut")
    assert dut_class == MockDUT
    DUTRegistry.clear()


def test_registry_get_unknown() -> None:
    """Test getting unknown DUT raises error."""
    DUTRegistry.clear()
    with pytest.raises(DUTError, match="Unknown DUT"):
        DUTRegistry.get("nonexistent")


def test_registry_create() -> None:
    """Test creating DUT instance."""
    DUTRegistry.clear()
    DUTRegistry.register(MockDUT)
    dut = DUTRegistry.create("mock-dut", config={"test": "value"})
    assert isinstance(dut, MockDUT)
    assert dut.config == {"test": "value"}
    DUTRegistry.clear()


def test_registry_list_available() -> None:
    """Test listing available DUTs."""
    DUTRegistry.clear()
    DUTRegistry.register(MockDUT)
    duts = DUTRegistry.list_available()
    assert duts == ["mock-dut"]
    DUTRegistry.clear()


def test_registry_clear() -> None:
    """Test clearing registry."""
    DUTRegistry.clear()
    DUTRegistry.register(MockDUT)
    assert len(DUTRegistry.list_available()) > 0
    DUTRegistry.clear()
    assert len(DUTRegistry.list_available()) == 0
