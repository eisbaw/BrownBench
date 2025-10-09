"""Unit tests for prompt optimizer."""

import pytest

from codegen_bench.utils.prompt_optimizer import PromptOptimizer


class TestPromptOptimizer:
    """Test prompt optimization utilities."""

    def test_count_tokens(self):
        """Test token counting."""
        optimizer = PromptOptimizer()

        # Simple text
        assert optimizer.count_tokens("Hello world") > 0

        # Empty text
        assert optimizer.count_tokens("") == 0

        # Whitespace affects token count
        text1 = "Hello world"
        text2 = "Hello    world"
        assert optimizer.count_tokens(text1) != optimizer.count_tokens(text2)

    def test_analyze_prompt(self):
        """Test prompt analysis."""
        optimizer = PromptOptimizer()

        prompt = """You are an expert. Please make sure to follow these instructions.

        It is important that you understand the task.
        In order to complete this, you need to be careful.

        Examples:
        - Example 1
        - Example 2
        """

        analysis = optimizer.analyze_prompt(prompt)

        assert "total_tokens" in analysis
        assert "line_count" in analysis
        assert "redundancies" in analysis
        assert "verbose_patterns" in analysis
        assert "optimization_potential" in analysis

        # Should find redundancies
        assert len(analysis["redundancies"]) > 0

    def test_optimize_prompt_basic(self):
        """Test basic prompt optimization."""
        optimizer = PromptOptimizer()

        verbose_prompt = """You are an expert software engineer.

        Your task is to implement the following:
        Please make sure to follow all instructions carefully.
        It is important that you understand everything.



        In order to complete this task, you need to write code.
        """

        optimized, metrics = optimizer.optimize_prompt(verbose_prompt, aggressive=False)

        # Should reduce tokens
        assert metrics["optimized_tokens"] < metrics["original_tokens"]
        assert metrics["tokens_saved"] > 0
        assert metrics["reduction_percent"] > 0

        # Should remove redundant whitespace
        assert "\n\n\n" not in optimized

        # Should simplify instructions
        assert "Please make sure to" not in optimized

    def test_optimize_prompt_aggressive(self):
        """Test aggressive prompt optimization."""
        optimizer = PromptOptimizer()

        verbose_prompt = """You are an expert in software implementation.

        Documentation should be comprehensive.
        Configuration must be correct.
        The specification needs to be followed.

        Examples:
        - Example of good code
        - Example of bad code

        For example, you should utilize best practices.
        """

        optimized, metrics = optimizer.optimize_prompt(verbose_prompt, aggressive=True)

        # Should have more reduction with aggressive mode
        assert metrics["reduction_percent"] > 20

        # Should abbreviate words
        assert "impl" in optimized or "implementation" not in optimized

        # Should remove examples
        assert "Example of good code" not in optimized

    def test_find_redundancies(self):
        """Test redundancy detection."""
        optimizer = PromptOptimizer()

        text = """Please follow these instructions.
        You must ensure correctness.
        It is important that you understand.
        Make sure to validate.
        Remember to test.
        """

        redundancies = optimizer._find_redundancies(text)

        assert len(redundancies) >= 4
        assert "please " in redundancies
        assert "you must " in redundancies

    def test_find_verbose_patterns(self):
        """Test verbose pattern detection."""
        optimizer = PromptOptimizer()

        text = """In order to succeed, you need to work.
        Due to the fact that it's complex, be careful.
        At this point in time, we should proceed.
        In the event that something fails, retry.
        """

        verbose = optimizer._find_verbose_patterns(text)

        assert len(verbose) >= 4
        assert any("in order to" in v for v in verbose)

    def test_compare_prompts(self):
        """Test prompt comparison."""
        optimizer = PromptOptimizer()

        prompt1 = "Simple prompt"
        prompt2 = "This is a much more verbose and lengthy prompt with many unnecessary words"

        comparison = optimizer.compare_prompts(prompt1, prompt2)

        assert comparison["prompt1_tokens"] < comparison["prompt2_tokens"]
        assert comparison["difference"] > 0
        assert comparison["more_efficient"] == "prompt1"

    def test_condense_instructions(self):
        """Test instruction condensation."""
        optimizer = PromptOptimizer()

        text = """You are an expert developer.
        Your task is to implement this.
        You must respond with code.
        Please provide complete solution.
        Make sure to test everything.
        """

        condensed = optimizer._condense_instructions(text)

        assert "Your task is to" not in condensed
        assert "You must respond" not in condensed or "Respond" in condensed
        assert "Please provide" not in condensed or "Provide" in condensed

    def test_simplify_formatting(self):
        """Test formatting simplification."""
        optimizer = PromptOptimizer()

        text = """##### Deep Header
        ***** Many asterisks
        ===== Many equals
        ----- Many dashes
        """

        simplified = optimizer._simplify_formatting(text)

        assert "#####" not in simplified
        assert "*****" not in simplified
        assert "=====" not in simplified
        assert "-----" not in simplified

    def test_empty_prompt_handling(self):
        """Test handling of empty prompts."""
        optimizer = PromptOptimizer()

        # Empty prompt
        analysis = optimizer.analyze_prompt("")
        assert analysis["total_tokens"] == 0

        optimized, metrics = optimizer.optimize_prompt("", aggressive=True)
        assert metrics["tokens_saved"] == 0

    def test_whitespace_token_counting(self):
        """Test whitespace token counting in analysis."""
        optimizer = PromptOptimizer()

        prompt_with_spaces = "Hello    world    test"
        prompt_compact = "Hello world test"

        analysis_spaces = optimizer.analyze_prompt(prompt_with_spaces)
        analysis_compact = optimizer.analyze_prompt(prompt_compact)

        assert analysis_spaces["whitespace_tokens"] > analysis_compact["whitespace_tokens"]

    def test_optimization_potential_estimation(self):
        """Test optimization potential estimation."""
        optimizer = PromptOptimizer()

        # High potential (verbose prompt)
        verbose = """You are an expert. Please make sure to carefully follow all of these instructions.
        It is very important that you understand everything completely.
        In order to successfully complete this task, you must be very careful.
        Examples: Example 1, Example 2, Example 3
        """ * 3

        # Low potential (already optimized)
        concise = "Expert. Task: implement X. Output: code."

        assert optimizer._estimate_optimization_potential(verbose) in ["HIGH", "MEDIUM"]
        assert optimizer._estimate_optimization_potential(concise) == "LOW"