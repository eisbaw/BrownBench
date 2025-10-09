"""Prompt optimization utilities for reducing token usage."""

import re
from typing import Dict, List, Tuple

import tiktoken


class PromptOptimizer:
    """Utilities for analyzing and optimizing prompts for token efficiency."""

    def __init__(self, model: str = "claude-3-sonnet-20240229"):
        """Initialize prompt optimizer.

        Args:
            model: Model name for tokenization
        """
        # Use cl100k_base encoding (approximation for Claude)
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens in

        Returns:
            Token count
        """
        return len(self.encoder.encode(text))

    def analyze_prompt(self, prompt: str) -> Dict[str, any]:
        """Analyze prompt for optimization opportunities.

        Args:
            prompt: Prompt to analyze

        Returns:
            Analysis results
        """
        tokens = self.count_tokens(prompt)
        lines = prompt.split("\n")

        # Find redundancies
        redundancies = self._find_redundancies(prompt)

        # Find verbose patterns
        verbose_patterns = self._find_verbose_patterns(prompt)

        # Calculate metrics
        analysis = {
            "total_tokens": tokens,
            "line_count": len(lines),
            "avg_tokens_per_line": tokens / len(lines) if lines else 0,
            "redundancies": redundancies,
            "verbose_patterns": verbose_patterns,
            "whitespace_tokens": self.count_tokens(re.sub(r"\S", "", prompt)),
            "uppercase_ratio": sum(1 for c in prompt if c.isupper()) / len(prompt) if prompt else 0,
            "optimization_potential": self._estimate_optimization_potential(prompt),
        }

        return analysis

    def optimize_prompt(self, prompt: str, aggressive: bool = False) -> Tuple[str, Dict[str, int]]:
        """Optimize prompt for token efficiency.

        Args:
            prompt: Prompt to optimize
            aggressive: Whether to apply aggressive optimizations

        Returns:
            Tuple of (optimized_prompt, metrics)
        """
        original_tokens = self.count_tokens(prompt)
        optimized = prompt

        # Basic optimizations (always apply)
        optimized = self._remove_redundant_whitespace(optimized)
        optimized = self._simplify_formatting(optimized)
        optimized = self._condense_instructions(optimized)

        # Aggressive optimizations (optional)
        if aggressive:
            optimized = self._abbreviate_common_words(optimized)
            optimized = self._remove_examples(optimized)
            optimized = self._use_shorter_synonyms(optimized)

        # Calculate savings
        optimized_tokens = self.count_tokens(optimized)
        metrics = {
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": original_tokens - optimized_tokens,
            "reduction_percent": round((1 - optimized_tokens / original_tokens) * 100, 1) if original_tokens > 0 else 0,
        }

        return optimized, metrics

    def _find_redundancies(self, text: str) -> List[str]:
        """Find redundant phrases in text."""
        redundancies = []

        # Common redundant phrases
        redundant_patterns = [
            r"please\s+",
            r"you\s+must\s+",
            r"it\s+is\s+important\s+that\s+",
            r"make\s+sure\s+to\s+",
            r"be\s+careful\s+to\s+",
            r"remember\s+to\s+",
            r"note\s+that\s+",
            r"keep\s+in\s+mind\s+that\s+",
        ]

        for pattern in redundant_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                redundancies.append(pattern.replace(r"\s+", " ").replace("\\", ""))

        return redundancies

    def _find_verbose_patterns(self, text: str) -> List[str]:
        """Find verbose patterns that could be simplified."""
        verbose = []

        # Check for verbose constructions
        verbose_patterns = {
            r"in\s+order\s+to": "to",
            r"due\s+to\s+the\s+fact\s+that": "because",
            r"at\s+this\s+point\s+in\s+time": "now",
            r"in\s+the\s+event\s+that": "if",
            r"has\s+the\s+ability\s+to": "can",
            r"is\s+able\s+to": "can",
            r"a\s+number\s+of": "several",
            r"the\s+majority\s+of": "most",
        }

        for pattern, replacement in verbose_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                verbose.append(f'"{pattern}" -> "{replacement}"')

        return verbose

    def _remove_redundant_whitespace(self, text: str) -> str:
        """Remove redundant whitespace while preserving structure."""
        # Remove multiple blank lines
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        # Remove trailing whitespace
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        return text

    def _simplify_formatting(self, text: str) -> str:
        """Simplify formatting markers."""
        # Reduce excessive formatting
        text = re.sub(r"#{4,}", "###", text)  # Limit header depth
        text = re.sub(r"\*{3,}", "**", text)  # Reduce asterisks
        text = re.sub(r"={3,}", "==", text)  # Reduce equals signs
        text = re.sub(r"-{3,}", "--", text)  # Reduce dashes
        return text

    def _condense_instructions(self, text: str) -> str:
        """Condense verbose instructions."""
        replacements = {
            r"You are an? (.+?) expert": r"\1 expert",
            r"Your task is to": "",
            r"You must respond": "Respond",
            r"Please provide": "Provide",
            r"Make sure to": "",
            r"Be sure to": "",
            r"It is important that you": "",
            r"You should": "",
            r"You need to": "",
            r"In order to": "To",
            r"Due to the fact that": "Because",
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text.strip()

    def _abbreviate_common_words(self, text: str) -> str:
        """Abbreviate common technical words."""
        abbreviations = {
            r"\bdocumentation\b": "docs",
            r"\bconfiguration\b": "config",
            r"\bspecification\b": "spec",
            r"\bimplementation\b": "impl",
            r"\bmodification\b": "mod",
            r"\bmaximum\b": "max",
            r"\bminimum\b": "min",
            r"\binformation\b": "info",
        }

        for pattern, abbrev in abbreviations.items():
            text = re.sub(pattern, abbrev, text, flags=re.IGNORECASE)

        return text

    def _remove_examples(self, text: str) -> str:
        """Remove example sections to save tokens."""
        # Remove example blocks
        text = re.sub(r"Examples?:.*?(?=\n\n|\Z)", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"For example[,:].*?(?=\n|\Z)", "", text, flags=re.IGNORECASE)
        return text

    def _use_shorter_synonyms(self, text: str) -> str:
        """Replace words with shorter synonyms."""
        synonyms = {
            r"\butilize\b": "use",
            r"\bdemonstrate\b": "show",
            r"\bapproximately\b": "about",
            r"\bsubsequent\b": "next",
            r"\bprevious\b": "prior",
            r"\bfacilitate\b": "help",
            r"\binitialize\b": "init",
        }

        for pattern, synonym in synonyms.items():
            text = re.sub(pattern, synonym, text, flags=re.IGNORECASE)

        return text

    def _estimate_optimization_potential(self, text: str) -> str:
        """Estimate optimization potential."""
        original = self.count_tokens(text)
        optimized, _ = self.optimize_prompt(text, aggressive=True)
        optimized_tokens = self.count_tokens(optimized)

        reduction = (1 - optimized_tokens / original) * 100 if original > 0 else 0

        if reduction > 40:
            return "HIGH"
        elif reduction > 20:
            return "MEDIUM"
        else:
            return "LOW"

    def compare_prompts(self, prompt1: str, prompt2: str) -> Dict[str, any]:
        """Compare two prompts for efficiency.

        Args:
            prompt1: First prompt
            prompt2: Second prompt

        Returns:
            Comparison results
        """
        tokens1 = self.count_tokens(prompt1)
        tokens2 = self.count_tokens(prompt2)

        return {
            "prompt1_tokens": tokens1,
            "prompt2_tokens": tokens2,
            "difference": tokens2 - tokens1,
            "percent_change": round((tokens2 - tokens1) / tokens1 * 100, 1) if tokens1 > 0 else 0,
            "more_efficient": "prompt1" if tokens1 < tokens2 else "prompt2" if tokens2 < tokens1 else "equal",
        }