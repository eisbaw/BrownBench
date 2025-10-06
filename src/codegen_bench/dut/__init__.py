"""Device Under Test (DUT) implementations."""

from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.dut.simple_chat import SimpleChatDUT

__all__ = [
    "ApproachMetadata",
    "CodeGenerationApproach",
    "DUTRegistry",
    "SimpleChatDUT",
]
