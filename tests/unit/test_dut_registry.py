"""Unit tests for DUTRegistry."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from codegen_bench.dut.base import CodeGenerationApproach
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.exceptions import DUTError


class MockDUT(CodeGenerationApproach):
    """Mock DUT for testing."""

    APPROACH_ID = "mock-dut"

    def solve(self, task, seed):
        """Mock solve method."""
        return MagicMock()

    def get_metadata(self):
        """Mock metadata."""
        return MagicMock()


class AnotherMockDUT(CodeGenerationApproach):
    """Another mock DUT for testing."""

    APPROACH_ID = "another-mock-dut"

    def solve(self, task, seed):
        """Mock solve method."""
        return MagicMock()

    def get_metadata(self):
        """Mock metadata."""
        return MagicMock()


class NoDUT(CodeGenerationApproach):
    """DUT without APPROACH_ID for testing."""

    APPROACH_ID = ""  # Invalid: empty string

    def solve(self, task, seed):
        """Mock solve method."""
        return MagicMock()

    def get_metadata(self):
        """Mock metadata."""
        return MagicMock()


class TestDUTRegistry:
    """Test DUTRegistry functionality."""

    def setup_method(self):
        """Clear registry before each test."""
        DUTRegistry.clear()
        DUTRegistry.set_audit_on_register(False)

    def teardown_method(self):
        """Clear registry after each test."""
        DUTRegistry.clear()
        DUTRegistry.set_audit_on_register(False)

    def test_register_dut(self):
        """Test registering a DUT."""
        # Register DUT
        result = DUTRegistry.register(MockDUT)

        # Should return the same class (for decorator usage)
        assert result is MockDUT

        # Should be in registry
        assert "mock-dut" in DUTRegistry.list_available()

    def test_register_multiple_duts(self):
        """Test registering multiple DUTs."""
        DUTRegistry.register(MockDUT)
        DUTRegistry.register(AnotherMockDUT)

        available = DUTRegistry.list_available()
        assert "mock-dut" in available
        assert "another-mock-dut" in available
        assert len(available) == 2

    def test_register_duplicate_overwrites(self):
        """Test that registering same ID overwrites previous."""
        DUTRegistry.register(MockDUT)
        DUTRegistry.register(MockDUT)  # Register again

        # Should still have only one entry
        available = DUTRegistry.list_available()
        assert available == ["mock-dut"]

    def test_register_without_approach_id(self):
        """Test registering DUT without APPROACH_ID fails."""
        with pytest.raises(DUTError, match="must define APPROACH_ID"):
            DUTRegistry.register(NoDUT)

    def test_get_registered_dut(self):
        """Test getting a registered DUT."""
        DUTRegistry.register(MockDUT)

        dut_class = DUTRegistry.get("mock-dut")
        assert dut_class is MockDUT

    def test_get_unregistered_dut(self):
        """Test getting an unregistered DUT raises error."""
        with pytest.raises(DUTError, match="Unknown DUT: nonexistent"):
            DUTRegistry.get("nonexistent")

    def test_create_dut_instance(self):
        """Test creating a DUT instance."""
        DUTRegistry.register(MockDUT)

        config = {"test": "config"}
        dut = DUTRegistry.create("mock-dut", config)

        assert isinstance(dut, MockDUT)
        assert dut.config == config

    def test_create_unregistered_dut(self):
        """Test creating an unregistered DUT raises error."""
        with pytest.raises(DUTError, match="Unknown DUT: nonexistent"):
            DUTRegistry.create("nonexistent", {})

    def test_list_available_sorted(self):
        """Test list_available returns sorted list."""
        # Register in non-alphabetical order
        DUTRegistry.register(AnotherMockDUT)
        DUTRegistry.register(MockDUT)

        available = DUTRegistry.list_available()
        assert available == ["another-mock-dut", "mock-dut"]

    def test_list_available_empty(self):
        """Test list_available when registry is empty."""
        assert DUTRegistry.list_available() == []

    def test_clear_registry(self):
        """Test clearing the registry."""
        DUTRegistry.register(MockDUT)
        assert DUTRegistry.list_available() == ["mock-dut"]

        DUTRegistry.clear()
        assert DUTRegistry.list_available() == []

    def test_thread_safety_concurrent_registration(self):
        """Test thread-safe concurrent registration."""
        results = []
        errors = []

        def register_dut():
            try:
                DUTRegistry.register(MockDUT)
                results.append("success")
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=register_dut) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0
        # Should have registered successfully
        assert "mock-dut" in DUTRegistry.list_available()

    def test_thread_safety_concurrent_get(self):
        """Test thread-safe concurrent get operations."""
        DUTRegistry.register(MockDUT)

        results = []
        errors = []

        def get_dut():
            try:
                dut_class = DUTRegistry.get("mock-dut")
                results.append(dut_class)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=get_dut) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0
        # All results should be the same class
        assert all(r is MockDUT for r in results)

    @patch("codegen_bench.security.auditor.DUTAuditor")
    def test_register_with_audit_enabled(self, mock_auditor_class):
        """Test registration with security audit enabled."""
        # Setup mock audit
        mock_auditor = MagicMock()
        mock_report = MagicMock()
        mock_report.passed = True
        mock_report.findings = []
        mock_auditor.audit_dut.return_value = mock_report
        mock_auditor_class.return_value = mock_auditor

        # Enable audit on register
        DUTRegistry.set_audit_on_register(True)

        # Register DUT
        DUTRegistry.register(MockDUT)

        # Should have audited the DUT
        mock_auditor.audit_dut.assert_called_once()
        assert "mock-dut" in DUTRegistry.list_available()

    @patch("codegen_bench.security.auditor.DUTAuditor")
    def test_register_with_audit_failed(self, mock_auditor_class):
        """Test registration fails when audit fails."""
        # Setup mock audit to fail
        mock_auditor = MagicMock()
        mock_report = MagicMock()
        mock_report.passed = False
        mock_report.findings = []
        mock_report.get_summary.return_value = "Security issues found"
        mock_auditor.audit_dut.return_value = mock_report
        mock_auditor_class.return_value = mock_auditor

        # Enable audit on register
        DUTRegistry.set_audit_on_register(True)

        # Registration should fail
        with pytest.raises(DUTError, match="failed security audit"):
            DUTRegistry.register(MockDUT)

        # Should not be in registry
        assert "mock-dut" not in DUTRegistry.list_available()

    @patch("codegen_bench.security.auditor.DUTAuditor")
    def test_register_with_explicit_audit_override(self, mock_auditor_class):
        """Test explicit audit parameter overrides global setting."""
        # Setup mock audit
        mock_auditor = MagicMock()
        mock_report = MagicMock()
        mock_report.passed = True
        mock_report.findings = []
        mock_auditor.audit_dut.return_value = mock_report
        mock_auditor_class.return_value = mock_auditor

        # Global audit is disabled
        DUTRegistry.set_audit_on_register(False)

        # But explicitly enable for this registration
        DUTRegistry.register(MockDUT, audit=True)

        # Should have audited despite global setting
        mock_auditor.audit_dut.assert_called_once()

    @patch("codegen_bench.security.auditor.DUTAuditor")
    def test_manual_audit_dut(self, mock_auditor_class):
        """Test manually auditing a registered DUT."""
        # Setup mock audit
        mock_auditor = MagicMock()
        mock_report = MagicMock()
        mock_auditor.audit_dut.return_value = mock_report
        mock_auditor_class.return_value = mock_auditor

        # Register DUT without audit
        DUTRegistry.register(MockDUT)

        # Manually audit
        report = DUTRegistry.audit_dut("mock-dut")

        # Should have audited
        mock_auditor.audit_dut.assert_called_once()
        assert report is mock_report

    def test_manual_audit_unregistered_dut(self):
        """Test manually auditing an unregistered DUT fails."""
        with pytest.raises(DUTError, match="Unknown DUT: nonexistent"):
            DUTRegistry.audit_dut("nonexistent")

    def test_decorator_usage(self):
        """Test using register as a decorator."""

        @DUTRegistry.register
        class DecoratorDUT(CodeGenerationApproach):
            APPROACH_ID = "decorator-dut"

            def solve(self, task, seed):
                return MagicMock()

            def get_metadata(self):
                return MagicMock()

        # Should be registered
        assert "decorator-dut" in DUTRegistry.list_available()
        # Should get the class back
        assert DUTRegistry.get("decorator-dut") is DecoratorDUT


class TestDUTRegistryInstanceBased:
    """Test instance-based usage of DUTRegistry."""

    def test_instance_isolation(self):
        """Test that instances are isolated from each other."""
        # Create two separate instances
        registry1 = DUTRegistry()
        registry2 = DUTRegistry()

        # Register in first instance
        registry1.register_instance(MockDUT)

        # Second instance should not see registration
        assert registry1.list_available_instance() == ["mock-dut"]
        assert registry2.list_available_instance() == []

    def test_instance_methods_work(self):
        """Test all instance methods work correctly."""
        registry = DUTRegistry()

        # Test register
        result = registry.register_instance(MockDUT)
        assert result is MockDUT

        # Test list_available
        assert registry.list_available_instance() == ["mock-dut"]

        # Test get
        dut_class = registry.get_instance("mock-dut")
        assert dut_class is MockDUT

        # Test create
        config = {"test": "config"}
        dut = registry.create_instance("mock-dut", config)
        assert isinstance(dut, MockDUT)

        # Test clear
        registry.clear_instance()
        assert registry.list_available_instance() == []

    def test_isolated_context_manager(self):
        """Test the isolated() context manager."""
        # Register in default instance
        DUTRegistry.clear()
        DUTRegistry.register(MockDUT)
        assert DUTRegistry.list_available() == ["mock-dut"]

        # Use isolated instance
        with DUTRegistry.isolated() as registry:
            # Should be empty initially
            assert registry.list_available_instance() == []

            # Register different DUT
            registry.register_instance(AnotherMockDUT)
            assert registry.list_available_instance() == ["another-mock-dut"]

            # Default instance unchanged
            assert DUTRegistry.list_available() == ["mock-dut"]

        # After context exit, isolated registry is gone
        # Default instance still has original registration
        assert DUTRegistry.list_available() == ["mock-dut"]

    def test_instance_thread_safety(self):
        """Test thread safety of instance operations."""
        registry = DUTRegistry()
        results = []
        errors = []

        def register_dut():
            try:
                registry.register_instance(MockDUT)
                results.append("success")
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=register_dut) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0
        # Should have registered successfully
        assert "mock-dut" in registry.list_available_instance()

    @patch("codegen_bench.security.auditor.DUTAuditor")
    def test_instance_audit_on_register(self, mock_auditor_class):
        """Test audit on register for instance."""
        registry = DUTRegistry()

        # Setup mock audit
        mock_auditor = MagicMock()
        mock_report = MagicMock()
        mock_report.passed = True
        mock_report.findings = []
        mock_auditor.audit_dut.return_value = mock_report
        mock_auditor_class.return_value = mock_auditor

        # Enable audit
        registry.set_audit_on_register_instance(True)

        # Register should trigger audit
        registry.register_instance(MockDUT)

        mock_auditor.audit_dut.assert_called_once()


class TestDUTRegistryBackwardCompatibility:
    """Test that class-level methods still work for backward compatibility."""

    def setup_method(self):
        """Clear default registry before each test."""
        DUTRegistry.clear()

    def test_class_methods_use_default_instance(self):
        """Test that class methods delegate to default instance."""
        # Class method should work
        DUTRegistry.register(MockDUT)
        assert DUTRegistry.list_available() == ["mock-dut"]

        # Get the default instance
        default = DUTRegistry._get_default_instance()

        # Should see the same registration
        assert default.list_available_instance() == ["mock-dut"]

    def test_singleton_default_instance(self):
        """Test that default instance is a singleton."""
        instance1 = DUTRegistry._get_default_instance()
        instance2 = DUTRegistry._get_default_instance()

        assert instance1 is instance2

    def test_decorator_still_works(self):
        """Test that decorator usage still works."""

        @DUTRegistry.register
        class DecoratorDUT(CodeGenerationApproach):
            APPROACH_ID = "decorator-dut"

            def solve(self, task, seed):
                return MagicMock()

            def get_metadata(self):
                return MagicMock()

        # Should be registered in default instance
        assert "decorator-dut" in DUTRegistry.list_available()
