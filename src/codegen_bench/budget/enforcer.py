"""Budget enforcement for controlling API costs during tournaments.

This module provides cost tracking and budget enforcement to prevent runaway
API costs during tournament execution. It supports:
- Per-DUT cost limits
- Global tournament budget limits
- Warning thresholds before hard stops
- Thread-safe cost accumulation
"""

from dataclasses import dataclass
from enum import Enum
from threading import Lock


class BudgetStatus(Enum):
    """Status of budget enforcement."""

    OK = "ok"  # Within budget, no warnings
    WARNING = "warning"  # Approaching limit
    EXCEEDED = "exceeded"  # Limit exceeded


@dataclass(frozen=True)
class BudgetConfig:
    """Configuration for budget enforcement.

    Attributes:
        global_limit: Maximum total cost in USD (None = unlimited)
        per_dut_limit: Maximum cost per DUT in USD (None = unlimited)
        warning_threshold: Fraction of limit to trigger warning (0.0-1.0)
    """

    global_limit: float | None = None
    per_dut_limit: float | None = None
    warning_threshold: float = 0.8

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.warning_threshold < 0 or self.warning_threshold > 1:
            raise ValueError(f"warning_threshold must be 0-1, got {self.warning_threshold}")

        if self.global_limit is not None and self.global_limit < 0:
            raise ValueError(f"global_limit must be positive, got {self.global_limit}")

        if self.per_dut_limit is not None and self.per_dut_limit < 0:
            raise ValueError(f"per_dut_limit must be positive, got {self.per_dut_limit}")


class BudgetExceededError(Exception):
    """Raised when budget limit is exceeded."""

    pass


class BudgetEnforcer:
    """Enforces budget limits during tournament execution.

    This class tracks costs and enforces budget limits with thread safety.
    It supports both per-DUT limits and global tournament limits.

    Example:
        >>> config = BudgetConfig(global_limit=100.0, per_dut_limit=20.0)
        >>> enforcer = BudgetEnforcer(config)
        >>>
        >>> # Record costs
        >>> enforcer.record_cost("dut1", 5.0)
        >>> enforcer.record_cost("dut1", 3.0)
        >>>
        >>> # Check status
        >>> status = enforcer.get_status()
        >>> print(f"Total: ${status.total_cost:.2f}")
        >>>
        >>> # Check before expensive operation
        >>> enforcer.check_budget("dut2", estimated_cost=15.0)
    """

    def __init__(self, config: BudgetConfig) -> None:
        """Initialize budget enforcer.

        Args:
            config: Budget configuration
        """
        self._config = config
        self._total_cost = 0.0
        self._dut_costs: dict[str, float] = {}
        self._lock = Lock()

    def record_cost(self, dut_id: str, cost_usd: float) -> None:
        """Record cost for a DUT.

        Args:
            dut_id: Identifier for the DUT
            cost_usd: Cost in USD to record

        Raises:
            ValueError: If cost is negative
            BudgetExceededError: If recording this cost would exceed limits
        """
        if cost_usd < 0:
            raise ValueError(f"Cost must be non-negative, got {cost_usd}")

        with self._lock:
            # Check if adding this cost would exceed limits
            new_total = self._total_cost + cost_usd
            new_dut_cost = self._dut_costs.get(dut_id, 0.0) + cost_usd

            # Check global limit
            if self._config.global_limit is not None:
                if new_total > self._config.global_limit:
                    raise BudgetExceededError(
                        f"Global budget exceeded: ${new_total:.2f} > ${self._config.global_limit:.2f}"
                    )

            # Check per-DUT limit
            if self._config.per_dut_limit is not None:
                if new_dut_cost > self._config.per_dut_limit:
                    raise BudgetExceededError(
                        f"Per-DUT budget exceeded for '{dut_id}': "
                        f"${new_dut_cost:.2f} > ${self._config.per_dut_limit:.2f}"
                    )

            # Record costs
            self._total_cost = new_total
            self._dut_costs[dut_id] = new_dut_cost

    def check_budget(self, dut_id: str | None = None, estimated_cost: float = 0.0) -> BudgetStatus:
        """Check budget status before performing an operation.

        Args:
            dut_id: DUT identifier (None for global check only)
            estimated_cost: Estimated cost of upcoming operation

        Returns:
            BudgetStatus indicating whether operation can proceed

        Raises:
            BudgetExceededError: If adding estimated cost would exceed hard limit
        """
        with self._lock:
            # Calculate what cost would be after operation
            future_total = self._total_cost + estimated_cost
            future_dut_cost = self._dut_costs.get(dut_id, 0.0) + estimated_cost if dut_id else 0.0

            # Check hard limits
            if self._config.global_limit is not None:
                if future_total > self._config.global_limit:
                    raise BudgetExceededError(
                        f"Estimated cost ${future_total:.2f} would exceed "
                        f"global budget ${self._config.global_limit:.2f}"
                    )

                # Check warning threshold
                if future_total >= self._config.global_limit * self._config.warning_threshold:
                    return BudgetStatus.WARNING

            if dut_id and self._config.per_dut_limit is not None:
                if future_dut_cost > self._config.per_dut_limit:
                    raise BudgetExceededError(
                        f"Estimated cost ${future_dut_cost:.2f} for '{dut_id}' would exceed "
                        f"per-DUT budget ${self._config.per_dut_limit:.2f}"
                    )

                # Check warning threshold
                if future_dut_cost >= self._config.per_dut_limit * self._config.warning_threshold:
                    return BudgetStatus.WARNING

            return BudgetStatus.OK

    def get_total_cost(self) -> float:
        """Get total cost across all DUTs.

        Returns:
            Total cost in USD
        """
        with self._lock:
            return self._total_cost

    def get_dut_cost(self, dut_id: str) -> float:
        """Get cost for a specific DUT.

        Args:
            dut_id: DUT identifier

        Returns:
            Cost in USD for this DUT (0.0 if no costs recorded)
        """
        with self._lock:
            return self._dut_costs.get(dut_id, 0.0)

    def get_all_dut_costs(self) -> dict[str, float]:
        """Get costs for all DUTs.

        Returns:
            Dictionary mapping DUT ID to cost in USD
        """
        with self._lock:
            return self._dut_costs.copy()

    def get_remaining_budget(self) -> tuple[float | None, float | None]:
        """Get remaining budget.

        Returns:
            Tuple of (global_remaining, per_dut_remaining) in USD.
            None indicates no limit set.
        """
        with self._lock:
            global_remaining = None
            if self._config.global_limit is not None:
                global_remaining = self._config.global_limit - self._total_cost

            per_dut_remaining = None
            if self._config.per_dut_limit is not None:
                # Return minimum remaining across all DUTs
                if self._dut_costs:
                    max_dut_cost = max(self._dut_costs.values())
                    per_dut_remaining = self._config.per_dut_limit - max_dut_cost
                else:
                    per_dut_remaining = self._config.per_dut_limit

            return (global_remaining, per_dut_remaining)

    def reset(self) -> None:
        """Reset all cost tracking.

        Useful for testing or starting a new tournament.
        """
        with self._lock:
            self._total_cost = 0.0
            self._dut_costs.clear()
