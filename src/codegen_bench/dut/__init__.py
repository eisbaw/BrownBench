"""Device Under Test (DUT) implementations."""

from codegen_bench.dut.base import ApproachMetadata, CodeGenerationApproach
from codegen_bench.dut.elaborate_prompt import ElaboratePromptDUT
from codegen_bench.dut.optimized_prompt import OptimizedPromptDUT
from codegen_bench.dut.registry import DUTRegistry
from codegen_bench.dut.simple_chat import SimpleChatDUT

# Auto-register built-in DUTs
DUTRegistry.register(SimpleChatDUT)
DUTRegistry.register(ElaboratePromptDUT)
DUTRegistry.register(OptimizedPromptDUT)

__all__ = [
    "ApproachMetadata",
    "CodeGenerationApproach",
    "DUTRegistry",
    "ElaboratePromptDUT",
    "OptimizedPromptDUT",
    "SimpleChatDUT",
]
