"""Judge system for comparing solutions."""

from codegen_bench.judge.base import Judge
from codegen_bench.judge.claude_judge import ClaudeJudge
from codegen_bench.judge.optimized_claude_judge import OptimizedClaudeJudge

__all__ = ["Judge", "ClaudeJudge", "OptimizedClaudeJudge"]
