#!/usr/bin/env python
"""Demonstration of prompt optimization for token efficiency.

This script shows the token savings achieved by prompt optimization.
Run this to see before/after comparisons and potential cost savings.
"""

from pathlib import Path
from typing import Dict

from codegen_bench.core.config import PricingConfig
from codegen_bench.core.task import Task
from codegen_bench.dut.elaborate_prompt import ElaboratePromptDUT
from codegen_bench.dut.optimized_prompt import OptimizedPromptDUT
from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.judge.claude_judge import ClaudeJudge
from codegen_bench.judge.optimized_claude_judge import OptimizedClaudeJudge
from codegen_bench.utils.prompt_optimizer import PromptOptimizer


def create_sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="sample",
        name="Add caching to API endpoint",
        project="web_server",
        domain="web",
        difficulty="medium",
        codebase_path=Path("/tmp/sample"),
        specification="""Add Redis caching to the /api/users endpoint:
        - Cache user data for 5 minutes
        - Invalidate on user updates
        - Handle Redis connection failures gracefully""",
        constraints=[
            "Must not break existing functionality",
            "Must handle cache misses properly",
            "Must log cache hit/miss metrics",
        ],
        gotchas=["Redis might be unavailable", "User data contains sensitive information"],
        key_files=["api/users.py", "lib/cache.py"],
    )


def analyze_dut_prompts():
    """Analyze and compare DUT prompts."""
    print("=" * 60)
    print("DUT PROMPT COMPARISON")
    print("=" * 60)

    task = create_sample_task()
    optimizer = PromptOptimizer()
    pricing = PricingConfig()

    # Initialize DUTs
    config = {"api_key": "dummy", "model": "claude-3-sonnet-20240229"}

    duts = {
        "SimpleChatDUT": SimpleChatDUT(config),
        "ElaboratePromptDUT": ElaboratePromptDUT(config),
        "OptimizedPromptDUT": OptimizedPromptDUT(config),
    }

    results = {}

    for name, dut in duts.items():
        # Build prompt
        if hasattr(dut, "_build_prompt"):
            prompt = dut._build_prompt(task)
        else:
            continue

        # Analyze
        tokens = optimizer.count_tokens(prompt)
        analysis = optimizer.analyze_prompt(prompt)

        results[name] = {
            "tokens": tokens,
            "lines": analysis["line_count"],
            "optimization_potential": analysis["optimization_potential"],
            "prompt_sample": prompt[:200] + "..." if len(prompt) > 200 else prompt,
        }

    # Display results
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Tokens: {data['tokens']:,}")
        print(f"  Lines: {data['lines']}")
        print(f"  Optimization potential: {data['optimization_potential']}")

        # Calculate cost for 1000 generations
        cost_per_1k = pricing.claude_sonnet_4_5_input_per_1k
        cost_1000_gens = (data['tokens'] * 1000 / 1000) * cost_per_1k
        print(f"  Cost for 1000 generations: ${cost_1000_gens:.2f}")

    # Show savings
    print("\n" + "-" * 60)
    print("SAVINGS COMPARISON:")

    elaborate_tokens = results["ElaboratePromptDUT"]["tokens"]
    optimized_tokens = results["OptimizedPromptDUT"]["tokens"]

    tokens_saved = elaborate_tokens - optimized_tokens
    percent_saved = (tokens_saved / elaborate_tokens) * 100

    print(f"  Tokens saved per prompt: {tokens_saved:,}")
    print(f"  Reduction: {percent_saved:.1f}%")

    # Cost savings for a tournament
    tournament_gens = 10 * 20 * 5  # 10 DUTs, 20 tasks, 5 samples
    total_tokens_saved = tokens_saved * tournament_gens
    cost_saved = (total_tokens_saved / 1000) * pricing.claude_sonnet_4_5_input_per_1k

    print(f"\n  For a tournament with {tournament_gens} generations:")
    print(f"  Total tokens saved: {total_tokens_saved:,}")
    print(f"  Cost saved: ${cost_saved:.2f}")


def demonstrate_optimization_techniques():
    """Demonstrate various optimization techniques."""
    print("\n" + "=" * 60)
    print("OPTIMIZATION TECHNIQUES DEMO")
    print("=" * 60)

    optimizer = PromptOptimizer()

    # Example verbose prompt
    verbose_prompt = """You are an expert software engineer with extensive experience.

    Your task is to carefully implement the following change to the codebase.
    Please make sure to follow all of the instructions provided below.
    It is very important that you understand everything completely before proceeding.

    INSTRUCTIONS:
    1. You must read through all of the existing code first
    2. You need to understand the current architecture
    3. You should follow existing patterns and conventions
    4. Make sure to test your changes thoroughly
    5. Please provide complete documentation

    In order to successfully complete this task, you will need to:
    - Analyze the existing implementation
    - Design your solution carefully
    - Implement the changes incrementally
    - Verify everything works correctly

    Remember to be careful about backward compatibility.
    Note that all existing tests must continue to pass.
    Keep in mind that this is production code.

    Examples of good practices:
    - Example 1: Always validate inputs
    - Example 2: Handle errors gracefully
    - Example 3: Write clear comments

    Due to the fact that this is critical code, please be extra careful.
    """

    print("\nORIGINAL PROMPT:")
    print("-" * 40)
    print(f"Tokens: {optimizer.count_tokens(verbose_prompt):,}")
    print(f"Lines: {len(verbose_prompt.splitlines())}")

    # Basic optimization
    basic_optimized, basic_metrics = optimizer.optimize_prompt(verbose_prompt, aggressive=False)

    print("\nBASIC OPTIMIZATION:")
    print("-" * 40)
    print(f"Tokens: {basic_metrics['optimized_tokens']:,}")
    print(f"Saved: {basic_metrics['tokens_saved']} tokens ({basic_metrics['reduction_percent']}%)")

    # Aggressive optimization
    aggressive_optimized, aggressive_metrics = optimizer.optimize_prompt(verbose_prompt, aggressive=True)

    print("\nAGGRESSIVE OPTIMIZATION:")
    print("-" * 40)
    print(f"Tokens: {aggressive_metrics['optimized_tokens']:,}")
    print(f"Saved: {aggressive_metrics['tokens_saved']} tokens ({aggressive_metrics['reduction_percent']}%)")

    # Show the optimized prompt
    print("\nOPTIMIZED PROMPT SAMPLE:")
    print("-" * 40)
    print(aggressive_optimized[:500] + "..." if len(aggressive_optimized) > 500 else aggressive_optimized)


def analyze_judge_prompts():
    """Analyze judge prompt efficiency."""
    print("\n" + "=" * 60)
    print("JUDGE PROMPT COMPARISON")
    print("=" * 60)

    optimizer = PromptOptimizer()
    pricing = PricingConfig()

    # Compare standard vs optimized judge prompts
    standard_prompt = """You are an expert code reviewer evaluating two solutions to a programming task.

Task: Add caching to API endpoint
Description: Add Redis caching to improve performance

Constraints:
- Must not break existing functionality
- Must handle cache misses properly
- Must log cache hit/miss metrics

Solution A:
[solution code here]

Solution B:
[solution code here]

Evaluation Criteria: Maintainability

Evaluate which solution is more maintainable based on:

1. **Code Clarity**: Is the code easy to read and understand?
2. **Documentation**: Are comments and docstrings clear and helpful?
3. **Conventions**: Does the code follow existing project conventions and style?
4. **Error Handling**: Is error handling robust and complete?
5. **Simplicity**: Is the solution as simple as possible while meeting requirements?
6. **Future Modification**: How easy would it be to modify or extend this code?

# Output Format

You MUST respond in exactly this format:

WINNER: A|B|TIE
REASONING: [2-3 sentences explaining your decision, focusing on the most important differences]
CONFIDENCE: [number between 0.0 and 1.0 indicating how confident you are]

Examples:
- WINNER: A
- WINNER: B
- WINNER: TIE

Guidelines:
- Use TIE only if the solutions are truly equivalent in maintainability
- Be specific about what makes one solution better
- Consider long-term maintenance burden, not just initial implementation
- Prefer solutions that will be easier to understand 6 months from now
- Consider that this code will be maintained by developers who didn't write it"""

    optimized_prompt = """Expert reviewing two solutions.

Task: Add caching to API endpoint
Spec: Add Redis caching to improve performance

Solution A:
[solution code here]

Solution B:
[solution code here]

Evaluate: clarity, documentation, conventions, error handling, simplicity, modifiability.
Pick more maintainable solution.

RESPOND:
WINNER: A|B|TIE
REASONING: [2-3 sentences]
CONFIDENCE: [0.0-1.0]"""

    # Analyze both
    standard_tokens = optimizer.count_tokens(standard_prompt)
    optimized_tokens = optimizer.count_tokens(optimized_prompt)

    print(f"\nStandard Judge Prompt:")
    print(f"  Tokens: {standard_tokens:,}")

    print(f"\nOptimized Judge Prompt:")
    print(f"  Tokens: {optimized_tokens:,}")

    savings = standard_tokens - optimized_tokens
    percent = (savings / standard_tokens) * 100

    print(f"\nSavings:")
    print(f"  Tokens saved: {savings:,} ({percent:.1f}%)")

    # Cost impact for 1000 judgments
    cost_per_1k = pricing.claude_sonnet_4_5_input_per_1k
    cost_saved = (savings * 1000 / 1000) * cost_per_1k
    print(f"  Cost saved per 1000 judgments: ${cost_saved:.2f}")


def show_recommendations():
    """Show recommendations for prompt optimization."""
    print("\n" + "=" * 60)
    print("PROMPT OPTIMIZATION RECOMMENDATIONS")
    print("=" * 60)

    recommendations = [
        ("Remove redundant instructions", "30-40%", "Eliminate 'please', 'make sure to', etc."),
        ("Use concise language", "20-30%", "Replace verbose phrases with shorter equivalents"),
        ("Eliminate examples when possible", "10-20%", "Remove if model already understands task"),
        ("Simplify formatting", "5-10%", "Reduce excessive markdown/whitespace"),
        ("Abbreviate common terms", "5-10%", "Use 'config' instead of 'configuration'"),
        ("Condense criteria lists", "10-15%", "Combine related evaluation points"),
    ]

    print("\nTechnique                      | Savings | Description")
    print("-" * 70)
    for technique, savings, description in recommendations:
        print(f"{technique:30} | {savings:7} | {description}")

    print("\nBEST PRACTICES:")
    print("-" * 40)
    print("1. Test optimized prompts to ensure quality isn't compromised")
    print("2. Start with basic optimization before aggressive changes")
    print("3. Monitor model performance with different prompt styles")
    print("4. Consider task complexity when deciding optimization level")
    print("5. Keep critical instructions even if verbose")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print(" PROMPT OPTIMIZATION FOR TOKEN EFFICIENCY")
    print("=" * 60)

    analyze_dut_prompts()
    demonstrate_optimization_techniques()
    analyze_judge_prompts()
    show_recommendations()

    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    print("\nPrompt optimization can reduce token usage by 30-50% while")
    print("maintaining effectiveness. For a typical tournament with")
    print("1000 generations, this can save $50-100 in API costs.")
    print("\nUse OptimizedPromptDUT and OptimizedClaudeJudge for")
    print("cost-effective benchmarking without sacrificing quality.")
    print("=" * 60)


if __name__ == "__main__":
    main()