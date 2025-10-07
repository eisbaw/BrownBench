"""Adaptive trial designs for efficient benchmarking.

Adaptive designs allow early stopping when results are clear, saving time and cost.
These methods are adapted from clinical trial methodology.

Modules:
- sequential: Group sequential design with O'Brien-Fleming boundaries
- mams: Multi-Arm Multi-Stage design for screening many approaches
- bayesian: Bayesian adaptive design with continuous monitoring
"""

from codegen_bench.stats.adaptive.mams import MAMSConfig, MAMSDesign, MAMSResult
from codegen_bench.stats.adaptive.sequential import (
    GroupSequentialDesign,
    SequentialBoundaries,
    StoppingDecision,
)

__all__ = [
    "GroupSequentialDesign",
    "SequentialBoundaries",
    "StoppingDecision",
    "MAMSConfig",
    "MAMSDesign",
    "MAMSResult",
]
