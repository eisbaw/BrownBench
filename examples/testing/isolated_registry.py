"""Example: Using isolated DUTRegistry for testing.

This example demonstrates how to use the improved DUTRegistry with
instance-based usage for isolated testing, preventing test interference
in parallel test execution.
"""

import threading
from typing import Any
from unittest.mock import MagicMock

from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task


# Example DUTs for demonstration
class TestDUT1(CodeGenerationApproach):
    """First test DUT."""
    APPROACH_ID = "test-dut-1"

    def solve(self, task: Task, seed: int) -> Solution:
        """Mock solve method."""
        return MagicMock(spec=Solution)

    def get_metadata(self):
        """Mock metadata."""
        return MagicMock()


class TestDUT2(CodeGenerationApproach):
    """Second test DUT."""
    APPROACH_ID = "test-dut-2"

    def solve(self, task: Task, seed: int) -> Solution:
        """Mock solve method."""
        return MagicMock(spec=Solution)

    def get_metadata(self):
        """Mock metadata."""
        return MagicMock()


def example_basic_usage():
    """Demonstrate basic registry usage (backward compatible)."""
    print("Basic Usage (Backward Compatible)")
    print("-" * 40)

    # Clear default registry for demo
    DUTRegistry.clear()

    # Register DUTs using class methods (uses default instance)
    DUTRegistry.register(TestDUT1)
    DUTRegistry.register(TestDUT2)

    # List available DUTs
    available = DUTRegistry.list_available()
    print(f"Registered DUTs: {available}")

    # Get a DUT class
    dut_class = DUTRegistry.get("test-dut-1")
    print(f"Retrieved DUT class: {dut_class.__name__}")

    # Create a DUT instance
    config = {"test_param": "value"}
    dut = DUTRegistry.create("test-dut-1", config)
    print(f"Created DUT instance: {dut}")

    print()


def example_instance_based_usage():
    """Demonstrate instance-based registry usage for testing."""
    print("Instance-Based Usage (For Testing)")
    print("-" * 40)

    # Create separate registry instances
    registry1 = DUTRegistry()
    registry2 = DUTRegistry()

    # Register different DUTs in each registry
    registry1.register_instance(TestDUT1)
    registry2.register_instance(TestDUT2)

    # Each registry is isolated
    print(f"Registry 1 DUTs: {registry1.list_available_instance()}")
    print(f"Registry 2 DUTs: {registry2.list_available_instance()}")

    # They don't interfere with each other
    assert "test-dut-1" in registry1.list_available_instance()
    assert "test-dut-1" not in registry2.list_available_instance()
    assert "test-dut-2" not in registry1.list_available_instance()
    assert "test-dut-2" in registry2.list_available_instance()

    print("✓ Registries are properly isolated")
    print()


def example_isolated_context_manager():
    """Demonstrate using the isolated() context manager."""
    print("Isolated Context Manager (Recommended for Tests)")
    print("-" * 40)

    # Set up default registry with a DUT
    DUTRegistry.clear()
    DUTRegistry.register(TestDUT1)
    print(f"Default registry before test: {DUTRegistry.list_available()}")

    # Use isolated registry in test
    with DUTRegistry.isolated() as test_registry:
        # This registry starts empty
        print(f"Test registry (initial): {test_registry.list_available_instance()}")

        # Register test-specific DUT
        test_registry.register_instance(TestDUT2)
        print(f"Test registry (after register): {test_registry.list_available_instance()}")

        # Default registry is unaffected
        print(f"Default registry (during test): {DUTRegistry.list_available()}")

        # Test operations
        dut_class = test_registry.get_instance("test-dut-2")
        assert dut_class is TestDUT2
        print("✓ Test operations work in isolated registry")

    # After context exit, test registry is discarded
    print(f"Default registry after test: {DUTRegistry.list_available()}")
    print("✓ Default registry unchanged after test")
    print()


def example_parallel_testing():
    """Demonstrate parallel testing with isolated registries."""
    print("Parallel Testing with Isolated Registries")
    print("-" * 40)

    results = []
    errors = []

    def test_function(test_id: int):
        """Simulate a test function running in parallel."""
        try:
            # Each test gets its own isolated registry
            with DUTRegistry.isolated() as registry:
                # Register a DUT specific to this test
                if test_id % 2 == 0:
                    registry.register_instance(TestDUT1)
                    expected = "test-dut-1"
                else:
                    registry.register_instance(TestDUT2)
                    expected = "test-dut-2"

                # Verify isolation
                available = registry.list_available_instance()
                assert len(available) == 1
                assert available[0] == expected

                results.append(f"Test {test_id}: {expected}")
        except Exception as e:
            errors.append(f"Test {test_id}: {e}")

    # Run tests in parallel
    threads = []
    for i in range(10):
        t = threading.Thread(target=test_function, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all tests to complete
    for t in threads:
        t.join()

    # Check results
    if errors:
        print(f"❌ Errors occurred: {errors}")
    else:
        print(f"✓ All {len(results)} tests passed with proper isolation")
        for result in sorted(results):
            print(f"  {result}")

    print()


def example_test_fixture():
    """Demonstrate using registry as a test fixture."""
    print("Using Registry as Test Fixture")
    print("-" * 40)

    class TestCase:
        """Simulated test case class."""

        def setup_method(self):
            """Set up test with isolated registry."""
            self.registry = DUTRegistry()
            print("  Setup: Created isolated registry")

        def teardown_method(self):
            """Clean up after test."""
            # Registry is automatically garbage collected
            self.registry = None
            print("  Teardown: Registry discarded")

        def test_dut_functionality(self):
            """Test DUT functionality with isolated registry."""
            print("  Test: Running with isolated registry")

            # Register test DUT
            self.registry.register_instance(TestDUT1)

            # Test operations
            assert "test-dut-1" in self.registry.list_available_instance()
            dut_class = self.registry.get_instance("test-dut-1")
            assert dut_class is TestDUT1

            print("  Test: ✓ DUT functionality verified")

    # Run simulated test
    test = TestCase()
    print("Running test case:")
    test.setup_method()
    test.test_dut_functionality()
    test.teardown_method()

    print()


def example_migration_path():
    """Show migration path from class-based to instance-based usage."""
    print("Migration Path")
    print("-" * 40)

    print("Old pattern (class-based, shared state):")
    print("""
    # Old: All tests share global state
    DUTRegistry.register(MyDUT)
    DUTRegistry.list_available()  # Sees all registrations
    """)

    print("New pattern (instance-based, isolated):")
    print("""
    # New: Each test gets isolated registry
    with DUTRegistry.isolated() as registry:
        registry.register_instance(MyDUT)
        registry.list_available_instance()  # Only sees this test's DUTs
    """)

    print("Benefits of new pattern:")
    print("  ✓ No test interference")
    print("  ✓ Safe for parallel execution")
    print("  ✓ Cleaner test isolation")
    print("  ✓ Backward compatible (old pattern still works)")
    print()


def example_production_vs_testing():
    """Show difference between production and testing usage."""
    print("Production vs Testing Usage")
    print("-" * 40)

    print("Production usage (global registry):")
    print("""
    # In production, use the global registry for discovery
    from codegen_bench.dut.registry import DUTRegistry
    from my_duts import CustomDUT

    # Register globally for CLI/API access
    DUTRegistry.register(CustomDUT)

    # CLI can now discover and use CustomDUT
    codegen-bench tournament --dut custom-dut ...
    """)

    print("\nTesting usage (isolated registry):")
    print("""
    # In tests, use isolated registry to avoid interference
    def test_my_dut():
        with DUTRegistry.isolated() as registry:
            registry.register_instance(CustomDUT)
            # Test CustomDUT without affecting other tests
            ...
    """)

    print("\nKey differences:")
    print("  Production: Global state for discovery")
    print("  Testing: Isolated state for safety")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("DUTRegistry Isolation Examples")
    print("=" * 60)
    print()

    example_basic_usage()
    example_instance_based_usage()
    example_isolated_context_manager()
    example_parallel_testing()
    example_test_fixture()
    example_migration_path()
    example_production_vs_testing()

    print("=" * 60)
    print("Summary: Use DUTRegistry.isolated() for safe, parallel testing")
    print("=" * 60)