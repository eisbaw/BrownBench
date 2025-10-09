"""Tests for API proxy server."""

import json
import time
from unittest.mock import Mock, patch

import httpx
import pytest

from codegen_bench.budget.enforcer import BudgetConfig, BudgetEnforcer, BudgetExceededError
from codegen_bench.security.api_proxy import (
    APIProxy,
    APIProxyConfig,
    APIProxyError,
    TemporaryKey,
)


class TestTemporaryKey:
    """Tests for TemporaryKey dataclass."""

    def test_create_key_without_expiration(self) -> None:
        """Test creating a key that never expires."""
        key = TemporaryKey(
            key="tmp-abc123",
            dut_id="dut-001",
            created_at=time.time(),
            expires_at=None,
        )

        assert not key.is_expired()

    def test_create_key_with_future_expiration(self) -> None:
        """Test creating a key that expires in the future."""
        key = TemporaryKey(
            key="tmp-abc123",
            dut_id="dut-001",
            created_at=time.time(),
            expires_at=time.time() + 3600,  # Expires in 1 hour
        )

        assert not key.is_expired()

    def test_create_key_with_past_expiration(self) -> None:
        """Test creating a key that has already expired."""
        key = TemporaryKey(
            key="tmp-abc123",
            dut_id="dut-001",
            created_at=time.time() - 7200,  # Created 2 hours ago
            expires_at=time.time() - 3600,  # Expired 1 hour ago
        )

        assert key.is_expired()


class TestAPIProxyConfig:
    """Tests for APIProxyConfig validation."""

    def test_valid_config(self) -> None:
        """Test creating a valid configuration."""
        config = APIProxyConfig(
            host="localhost",
            port=8080,
            real_api_key="sk-ant-test123",
            api_base_url="https://api.anthropic.com/v1",
        )

        assert config.host == "localhost"
        assert config.port == 8080
        assert config.real_api_key == "sk-ant-test123"

    def test_empty_api_key_raises_error(self) -> None:
        """Test that empty API key raises ValueError."""
        with pytest.raises(ValueError, match="real_api_key cannot be empty"):
            APIProxyConfig(
                host="localhost",
                port=8080,
                real_api_key="",
            )

    def test_invalid_port_raises_error(self) -> None:
        """Test that invalid port raises ValueError."""
        with pytest.raises(ValueError, match="port must be 0-65535"):
            APIProxyConfig(
                host="localhost",
                port=99999,
                real_api_key="sk-ant-test123",
            )

        with pytest.raises(ValueError, match="port must be 0-65535"):
            APIProxyConfig(
                host="localhost",
                port=-1,
                real_api_key="sk-ant-test123",
            )

    def test_negative_ttl_raises_error(self) -> None:
        """Test that negative TTL raises ValueError."""
        with pytest.raises(ValueError, match="key_ttl_seconds must be positive"):
            APIProxyConfig(
                host="localhost",
                port=8080,
                real_api_key="sk-ant-test123",
                key_ttl_seconds=-1.0,
            )


class TestAPIProxy:
    """Tests for APIProxy server."""

    @pytest.fixture
    def config(self) -> APIProxyConfig:
        """Create a test proxy configuration."""
        return APIProxyConfig(
            host="localhost",
            port=0,  # Use port 0 to let OS assign free port
            real_api_key="sk-ant-test123",
            api_base_url="https://api.anthropic.com/v1",
        )

    @pytest.fixture
    def proxy(self, config: APIProxyConfig) -> APIProxy:
        """Create a test API proxy."""
        return APIProxy(config)

    def test_initialization(self, proxy: APIProxy) -> None:
        """Test proxy initialization."""
        assert not proxy.is_running()
        assert len(proxy.get_active_keys()) == 0

    def test_issue_key(self, proxy: APIProxy) -> None:
        """Test issuing a temporary key."""
        temp_key = proxy.issue_key("dut-001")

        assert temp_key.startswith("tmp-")
        assert len(temp_key) > 10  # Should be reasonably long

        # Key should be retrievable
        assert proxy.get_dut_id(temp_key) == "dut-001"

    def test_issue_multiple_keys(self, proxy: APIProxy) -> None:
        """Test issuing multiple keys for different DUTs."""
        key1 = proxy.issue_key("dut-001")
        key2 = proxy.issue_key("dut-002")

        assert key1 != key2
        assert proxy.get_dut_id(key1) == "dut-001"
        assert proxy.get_dut_id(key2) == "dut-002"

    def test_revoke_key(self, proxy: APIProxy) -> None:
        """Test revoking a temporary key."""
        temp_key = proxy.issue_key("dut-001")
        assert proxy.get_dut_id(temp_key) == "dut-001"

        proxy.revoke_key(temp_key)
        assert proxy.get_dut_id(temp_key) is None

    def test_revoke_nonexistent_key(self, proxy: APIProxy) -> None:
        """Test revoking a key that doesn't exist (should not raise)."""
        proxy.revoke_key("nonexistent-key")  # Should not raise

    def test_get_dut_id_for_invalid_key(self, proxy: APIProxy) -> None:
        """Test getting DUT ID for invalid key returns None."""
        assert proxy.get_dut_id("invalid-key") is None

    def test_key_expiration(self) -> None:
        """Test that expired keys are rejected."""
        config = APIProxyConfig(
            host="localhost",
            port=0,
            real_api_key="sk-ant-test123",
            key_ttl_seconds=0.1,  # 100ms TTL
        )
        proxy = APIProxy(config)

        temp_key = proxy.issue_key("dut-001")
        assert proxy.get_dut_id(temp_key) == "dut-001"

        # Wait for key to expire
        time.sleep(0.2)

        # Expired key should be rejected
        assert proxy.get_dut_id(temp_key) is None

    def test_get_active_keys(self, proxy: APIProxy) -> None:
        """Test getting all active keys."""
        key1 = proxy.issue_key("dut-001")
        key2 = proxy.issue_key("dut-002")

        active_keys = proxy.get_active_keys()
        assert len(active_keys) == 2
        assert active_keys[key1] == "dut-001"
        assert active_keys[key2] == "dut-002"

        # Revoke one key
        proxy.revoke_key(key1)
        active_keys = proxy.get_active_keys()
        assert len(active_keys) == 1
        assert key2 in active_keys

    def test_start_and_stop_server(self, proxy: APIProxy) -> None:
        """Test starting and stopping the proxy server."""
        assert not proxy.is_running()

        proxy.start()
        assert proxy.is_running()

        proxy.stop()
        assert not proxy.is_running()

    def test_start_already_running_raises_error(self, proxy: APIProxy) -> None:
        """Test that starting an already running server raises error."""
        proxy.start()
        try:
            with pytest.raises(APIProxyError, match="already running"):
                proxy.start()
        finally:
            proxy.stop()

    def test_stop_not_running_does_nothing(self, proxy: APIProxy) -> None:
        """Test that stopping a non-running server does nothing."""
        proxy.stop()  # Should not raise

    @patch("httpx.Client")
    def test_forward_request_replaces_key(self, mock_client_class: Mock, proxy: APIProxy) -> None:
        """Test that request forwarding replaces temporary key with real key."""
        # Set up mock HTTP client
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"usage": {"input_tokens": 100, "output_tokens": 50}}'
        mock_response.json.return_value = {"usage": {"input_tokens": 100, "output_tokens": 50}}
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create new proxy with mocked client
        config = APIProxyConfig(
            host="localhost",
            port=0,
            real_api_key="sk-ant-real-key",
            api_base_url="https://api.anthropic.com/v1",
        )
        proxy_with_mock = APIProxy(config)
        proxy_with_mock._http_client = mock_client

        # Forward a request
        headers = {"x-api-key": "tmp-fake-key", "content-type": "application/json"}
        body = b'{"messages": [{"role": "user", "content": "Hello"}]}'

        response = proxy_with_mock._forward_request(
            method="POST",
            path="/messages",
            headers=headers,
            body=body,
            dut_id="dut-001",
        )

        # Verify request was forwarded
        assert mock_client.request.called
        call_kwargs = mock_client.request.call_args[1]

        # Verify real key was used (not temporary key)
        assert call_kwargs["headers"]["x-api-key"] == "sk-ant-real-key"

        # Verify response was returned
        assert response.status_code == 200

    @patch("httpx.Client")
    def test_forward_request_tracks_cost(self, mock_client_class: Mock) -> None:
        """Test that request forwarding tracks cost with budget enforcer."""
        # Set up budget enforcer
        budget_config = BudgetConfig(per_dut_limit=10.0)
        budget_enforcer = BudgetEnforcer(budget_config)

        # Set up mock HTTP client
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"usage": {"input_tokens": 1000, "output_tokens": 500}}'
        mock_response.json.return_value = {"usage": {"input_tokens": 1000, "output_tokens": 500}}
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create proxy with budget enforcer
        config = APIProxyConfig(
            host="localhost",
            port=0,
            real_api_key="sk-ant-real-key",
            api_base_url="https://api.anthropic.com/v1",
            budget_enforcer=budget_enforcer,
        )
        proxy_with_budget = APIProxy(config)
        proxy_with_budget._http_client = mock_client

        # Forward a request
        headers = {"x-api-key": "tmp-fake-key"}
        body = b'{"messages": []}'

        proxy_with_budget._forward_request(
            method="POST",
            path="/messages",
            headers=headers,
            body=body,
            dut_id="dut-001",
        )

        # Verify cost was tracked
        dut_cost = budget_enforcer.get_dut_cost("dut-001")
        assert dut_cost > 0

        # Verify cost calculation (1000 input @ $0.003/1k + 500 output @ $0.015/1k)
        expected_cost = (1000 / 1000) * 0.003 + (500 / 1000) * 0.015
        assert abs(dut_cost - expected_cost) < 0.0001

    @patch("httpx.Client")
    def test_forward_request_enforces_budget(self, mock_client_class: Mock) -> None:
        """Test that request forwarding enforces budget limits."""
        # Set up budget enforcer with low limit
        budget_config = BudgetConfig(per_dut_limit=0.015)  # $0.015 limit
        budget_enforcer = BudgetEnforcer(budget_config)

        # Set up mock HTTP client
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # First response: within budget
        small_response = Mock(spec=httpx.Response)
        small_response.status_code = 200
        small_response.headers = {"content-type": "application/json"}
        small_response.content = b'{"usage": {"input_tokens": 1000, "output_tokens": 500}}'
        small_response.json.return_value = {"usage": {"input_tokens": 1000, "output_tokens": 500}}
        # Cost: (1000/1000)*0.003 + (500/1000)*0.015 = 0.003 + 0.0075 = 0.0105

        # Second response: would exceed budget
        large_response = Mock(spec=httpx.Response)
        large_response.status_code = 200
        large_response.headers = {"content-type": "application/json"}
        large_response.content = b'{"usage": {"input_tokens": 1000, "output_tokens": 500}}'
        large_response.json.return_value = {"usage": {"input_tokens": 1000, "output_tokens": 500}}
        # Cost: another 0.0105, total would be 0.021 > 0.015

        # Configure mock to return different responses
        mock_client.request.side_effect = [small_response, large_response]

        # Create proxy with budget enforcer
        config = APIProxyConfig(
            host="localhost",
            port=0,
            real_api_key="sk-ant-real-key",
            budget_enforcer=budget_enforcer,
        )
        proxy_with_budget = APIProxy(config)
        proxy_with_budget._http_client = mock_client

        # First request should succeed
        headers = {"x-api-key": "tmp-fake-key"}
        body = b'{"messages": []}'

        proxy_with_budget._forward_request(
            method="POST",
            path="/messages",
            headers=headers,
            body=body,
            dut_id="dut-001",
        )

        # Second request should fail due to budget exceeded
        with pytest.raises(BudgetExceededError):
            proxy_with_budget._forward_request(
                method="POST",
                path="/messages",
                headers=headers,
                body=body,
                dut_id="dut-001",
            )

    def test_estimate_cost_from_response(self, proxy: APIProxy) -> None:
        """Test cost estimation from API response."""
        # Create mock response with usage data
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
            }
        }

        cost = proxy._estimate_cost_from_response(mock_response)

        # Expected: (1000 / 1000) * 0.003 + (500 / 1000) * 0.015
        expected_cost = 0.003 + 0.0075
        assert abs(cost - expected_cost) < 0.0001

    def test_estimate_cost_from_error_response(self, proxy: APIProxy) -> None:
        """Test cost estimation from error response returns 0."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}

        cost = proxy._estimate_cost_from_response(mock_response)
        assert cost == 0.0

    def test_estimate_cost_from_malformed_response(self, proxy: APIProxy) -> None:
        """Test cost estimation handles malformed response gracefully."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)

        # Should not raise, just return 0
        cost = proxy._estimate_cost_from_response(mock_response)
        assert cost == 0.0

    def test_concurrent_key_operations(self, proxy: APIProxy) -> None:
        """Test thread safety of key operations."""
        import threading

        keys = []
        errors = []

        def issue_keys() -> None:
            try:
                for i in range(100):
                    key = proxy.issue_key(f"dut-{i}")
                    keys.append(key)
            except Exception as e:
                errors.append(e)

        # Run multiple threads issuing keys
        threads = [threading.Thread(target=issue_keys) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Verify all keys are unique
        assert len(keys) == len(set(keys))
