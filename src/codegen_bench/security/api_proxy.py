"""API proxy for secure DUT execution with budget tracking.

This module provides an HTTP proxy server that:
- Issues temporary API keys to DUTs
- Replaces temporary keys with real API keys
- Forwards requests to actual API providers
- Tracks costs per DUT
- Integrates with BudgetEnforcer

The proxy enables secure DUT execution in containers without exposing real API keys.
"""

import secrets
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Lock, Thread
from typing import Any

import httpx
import structlog

from codegen_bench.budget.enforcer import BudgetEnforcer

logger = structlog.get_logger(__name__)

# Timeout constants (in seconds)
UPSTREAM_REQUEST_TIMEOUT = 60  # Timeout for forwarding to actual API
PROXY_SHUTDOWN_TIMEOUT = 5  # Timeout for graceful shutdown


@dataclass(frozen=True)
class TemporaryKey:
    """Temporary API key issued to a DUT.

    Attributes:
        key: The temporary key string
        dut_id: ID of the DUT this key belongs to
        created_at: Unix timestamp when key was created
        expires_at: Unix timestamp when key expires (None = never)
    """

    key: str
    dut_id: str
    created_at: float
    expires_at: float | None = None

    def is_expired(self) -> bool:
        """Check if key has expired.

        Returns:
            True if key has expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass(frozen=True)
class APIProxyConfig:
    """Configuration for API proxy server.

    Attributes:
        host: Host to bind to (default: localhost)
        port: Port to listen on (default: 8080)
        real_api_key: Real API key to use for upstream requests
        api_base_url: Base URL for upstream API (e.g., https://api.anthropic.com/v1)
        key_ttl_seconds: TTL for temporary keys (None = never expire)
        budget_enforcer: Optional budget enforcer for cost tracking
    """

    host: str = "localhost"
    port: int = 8080
    real_api_key: str = ""
    api_base_url: str = "https://api.anthropic.com/v1"
    key_ttl_seconds: float | None = None
    budget_enforcer: BudgetEnforcer | None = None

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.real_api_key:
            raise ValueError("real_api_key cannot be empty")

        if self.port < 0 or self.port > 65535:
            raise ValueError(f"port must be 0-65535, got {self.port}")

        if self.key_ttl_seconds is not None and self.key_ttl_seconds <= 0:
            raise ValueError(f"key_ttl_seconds must be positive, got {self.key_ttl_seconds}")


class APIProxyError(Exception):
    """Raised when API proxy operations fail."""

    pass


class APIProxy:
    """HTTP proxy server for secure API access.

    This proxy sits between DUTs and external APIs, providing:
    1. Temporary key generation for DUTs
    2. Key replacement before forwarding requests
    3. Cost tracking per DUT
    4. Budget enforcement

    Example:
        >>> from codegen_bench.budget.enforcer import BudgetConfig, BudgetEnforcer
        >>>
        >>> # Set up budget enforcement
        >>> budget_config = BudgetConfig(per_dut_limit=10.0)
        >>> budget_enforcer = BudgetEnforcer(budget_config)
        >>>
        >>> # Configure proxy
        >>> config = APIProxyConfig(
        ...     host="localhost",
        ...     port=8080,
        ...     real_api_key="sk-ant-...",
        ...     api_base_url="https://api.anthropic.com/v1",
        ...     budget_enforcer=budget_enforcer,
        ... )
        >>>
        >>> # Start proxy
        >>> proxy = APIProxy(config)
        >>> proxy.start()
        >>>
        >>> # Issue temporary key for DUT
        >>> temp_key = proxy.issue_key("dut-001")
        >>> print(f"Temporary key: {temp_key}")
        >>>
        >>> # DUT uses temp key, proxy forwards with real key
        >>> # Costs are automatically tracked per DUT
        >>>
        >>> # Cleanup
        >>> proxy.stop()
        >>> proxy.revoke_key(temp_key)
    """

    def __init__(self, config: APIProxyConfig) -> None:
        """Initialize API proxy.

        Args:
            config: Proxy configuration
        """
        self._config = config
        self._keys: dict[str, TemporaryKey] = {}  # temp_key -> TemporaryKey
        self._lock = Lock()
        self._server: HTTPServer | None = None
        self._server_thread: Thread | None = None
        self._running = False
        self._http_client = httpx.Client(timeout=UPSTREAM_REQUEST_TIMEOUT)

    def issue_key(self, dut_id: str) -> str:
        """Issue a temporary API key for a DUT.

        Args:
            dut_id: Identifier for the DUT

        Returns:
            Temporary API key string
        """
        # Generate cryptographically secure random key
        temp_key = f"tmp-{secrets.token_urlsafe(32)}"

        created_at = time.time()
        expires_at = None
        if self._config.key_ttl_seconds is not None:
            expires_at = created_at + self._config.key_ttl_seconds

        with self._lock:
            self._keys[temp_key] = TemporaryKey(
                key=temp_key,
                dut_id=dut_id,
                created_at=created_at,
                expires_at=expires_at,
            )

        logger.info(
            "temporary_key_issued",
            dut_id=dut_id,
            key_prefix=temp_key[:10],
            expires_at=expires_at,
        )

        return temp_key

    def revoke_key(self, temp_key: str) -> None:
        """Revoke a temporary API key.

        Args:
            temp_key: The temporary key to revoke
        """
        with self._lock:
            if temp_key in self._keys:
                dut_id = self._keys[temp_key].dut_id
                del self._keys[temp_key]
                logger.info(
                    "temporary_key_revoked",
                    dut_id=dut_id,
                    key_prefix=temp_key[:10],
                )

    def get_dut_id(self, temp_key: str) -> str | None:
        """Get DUT ID associated with a temporary key.

        Args:
            temp_key: The temporary key

        Returns:
            DUT ID if key exists and is valid, None otherwise
        """
        with self._lock:
            key_info = self._keys.get(temp_key)
            if key_info is None:
                return None

            if key_info.is_expired():
                logger.warning(
                    "expired_key_used",
                    dut_id=key_info.dut_id,
                    key_prefix=temp_key[:10],
                )
                return None

            return key_info.dut_id

    def start(self) -> None:
        """Start the proxy server in a background thread.

        Raises:
            APIProxyError: If server is already running or fails to start
        """
        if self._running:
            raise APIProxyError("Proxy server is already running")

        logger.info(
            "starting_api_proxy",
            host=self._config.host,
            port=self._config.port,
        )

        # Create request handler with access to this proxy instance
        proxy_instance = self

        class ProxyRequestHandler(BaseHTTPRequestHandler):
            """HTTP request handler that forwards to upstream API."""

            def do_POST(self) -> None:  # noqa: N802
                """Handle POST requests."""
                try:
                    # Read request body
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length)

                    # Extract temporary key from Authorization header
                    auth_header = self.headers.get("x-api-key", "")
                    if not auth_header:
                        self.send_error(401, "Missing x-api-key header")
                        return

                    # Get DUT ID from temporary key
                    dut_id = proxy_instance.get_dut_id(auth_header)
                    if dut_id is None:
                        self.send_error(401, "Invalid or expired API key")
                        return

                    # Forward request with real API key
                    try:
                        response = proxy_instance._forward_request(
                            method="POST",
                            path=self.path,
                            headers=dict(self.headers),
                            body=body,
                            dut_id=dut_id,
                        )

                        # Send response back to client
                        self.send_response(response.status_code)
                        for key, value in response.headers.items():
                            # Skip hop-by-hop headers
                            if key.lower() not in ("connection", "keep-alive", "transfer-encoding"):
                                self.send_header(key, value)
                        self.end_headers()
                        self.wfile.write(response.content)

                    except Exception as e:
                        logger.error(
                            "upstream_request_failed",
                            dut_id=dut_id,
                            path=self.path,
                            error=str(e),
                        )
                        self.send_error(502, f"Upstream request failed: {e}")

                except Exception as e:
                    logger.error("request_handling_failed", error=str(e))
                    self.send_error(500, f"Internal error: {e}")

            def log_message(self, format: str, *args: Any) -> None:  # noqa: ARG002
                """Suppress default logging (we use structlog)."""
                pass

        # Create and start server
        try:
            self._server = HTTPServer(
                (self._config.host, self._config.port),
                ProxyRequestHandler,
            )
            self._running = True

            # Run server in background thread
            self._server_thread = Thread(
                target=self._server.serve_forever,
                daemon=True,
            )
            self._server_thread.start()

            logger.info(
                "api_proxy_started",
                host=self._config.host,
                port=self._config.port,
            )

        except Exception as e:
            self._running = False
            raise APIProxyError(f"Failed to start proxy server: {e}") from e

    def stop(self) -> None:
        """Stop the proxy server.

        This method blocks until server shutdown is complete.
        """
        if not self._running:
            return

        logger.info("stopping_api_proxy")

        if self._server:
            self._server.shutdown()
            if self._server_thread:
                self._server_thread.join(timeout=PROXY_SHUTDOWN_TIMEOUT)
            self._server.server_close()

        self._running = False
        self._http_client.close()

        logger.info("api_proxy_stopped")

    def _forward_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
        dut_id: str,
    ) -> httpx.Response:
        """Forward request to upstream API.

        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            body: Request body
            dut_id: DUT identifier for budget tracking

        Returns:
            Response from upstream API

        Raises:
            APIProxyError: If forwarding fails
        """
        # Build upstream URL
        url = f"{self._config.api_base_url}{path}"

        # Replace temporary key with real key
        headers = dict(headers)  # Copy to avoid mutating caller's dict
        headers["x-api-key"] = self._config.real_api_key

        # Remove hop-by-hop headers
        for hop_header in ("host", "connection", "keep-alive", "transfer-encoding"):
            headers.pop(hop_header, None)

        logger.debug(
            "forwarding_request",
            dut_id=dut_id,
            method=method,
            url=url,
        )

        # Forward request
        response = self._http_client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
        )

        # Track cost if budget enforcer is configured
        if self._config.budget_enforcer:
            cost = self._estimate_cost_from_response(response)
            if cost > 0:
                try:
                    self._config.budget_enforcer.record_cost(dut_id, cost)
                    logger.info(
                        "cost_tracked",
                        dut_id=dut_id,
                        cost_usd=cost,
                    )
                except Exception as e:
                    logger.error(
                        "cost_tracking_failed",
                        dut_id=dut_id,
                        error=str(e),
                    )
                    # Re-raise to fail fast on budget violations
                    raise

        return response

    def _estimate_cost_from_response(self, response: httpx.Response) -> float:
        """Estimate cost from API response.

        This is a simple estimation based on response headers or body.
        For Anthropic API, we parse the usage field from the JSON response.

        Args:
            response: API response

        Returns:
            Estimated cost in USD
        """
        try:
            # For Anthropic API, parse usage from JSON response
            if response.status_code == 200:
                data = response.json()
                usage = data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                # Use Claude Sonnet 4.5 pricing (matching SimpleChatDUT)
                # $3/M input, $15/M output
                input_cost = (input_tokens / 1000) * 0.003
                output_cost = (output_tokens / 1000) * 0.015

                return input_cost + output_cost

        except Exception as e:
            logger.warning(
                "cost_estimation_failed",
                error=str(e),
                note="Cost tracking may be inaccurate",
            )

        return 0.0

    def is_running(self) -> bool:
        """Check if proxy server is running.

        Returns:
            True if server is running, False otherwise
        """
        return self._running

    def get_active_keys(self) -> dict[str, str]:
        """Get all active temporary keys and their DUT IDs.

        Returns:
            Dictionary mapping temporary keys to DUT IDs
        """
        with self._lock:
            return {
                key: info.dut_id
                for key, info in self._keys.items()
                if not info.is_expired()
            }
