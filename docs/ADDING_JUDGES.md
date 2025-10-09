# Adding New Judges

This guide explains how to create new judge implementations for BrownBench. A judge evaluates and compares code solutions across quality dimensions (arenas).

## Table of Contents

1. [Quick Start](#quick-start)
2. [Judge Interface](#judge-interface)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Implementation Patterns](#implementation-patterns)
5. [Testing Your Judge](#testing-your-judge)
6. [Calibration](#calibration)
7. [Example: ClaudeCodeJudge](#example-claudecodejudge)

## Quick Start

To create a new judge:

1. Subclass `Judge`
2. Implement `evaluate(solution_a, solution_b, arena, task)` method
3. Parse responses into `JudgeVote` format
4. Add rate limiting and retry logic
5. Calibrate against ground truth

**Minimal Example**:

```python
from codegen_bench.judge.base import Judge
from codegen_bench.core.judgment import JudgeVote, Vote
from codegen_bench.core.solution import Solution
from codegen_bench.core.arena import Arena
from codegen_bench.core.task import Task

class MyJudge(Judge):
    """Custom judge implementation."""

    def __init__(self, api_key: str, model: str = "my-model"):
        super().__init__(model=model)
        self.api_key = api_key
        self.client = MyAPIClient(api_key)

    def evaluate(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task
    ) -> JudgeVote:
        """Compare two solutions."""
        # 1. Build evaluation prompt
        prompt = self._build_prompt(solution_a, solution_b, arena, task)

        # 2. Call your AI/ML system
        response = self.client.generate(prompt)

        # 3. Parse response
        vote = self._parse_vote(response.text)

        return vote
```

## Judge Interface

### Base Class

```python
from abc import ABC, abstractmethod

class Judge(ABC):
    """Abstract base for AI judges that compare solutions."""

    def __init__(self, model: str, temperature: float = 0.3, variant: int = 0):
        """Initialize Judge.

        Args:
            model: Model identifier
            temperature: Sampling temperature for consistency
            variant: Prompt variant number for diversity
        """
        self.model = model
        self.temperature = temperature
        self.variant = variant

    @abstractmethod
    def evaluate(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task
    ) -> JudgeVote:
        """Compare two solutions in a given arena."""
        pass
```

### JudgeVote Structure

```python
from dataclasses import dataclass
from typing import Literal

Vote = Literal["A", "B", "TIE"]

@dataclass
class JudgeVote:
    """A judge's vote on solution comparison."""

    vote: Vote                # Winner: "A", "B", or "TIE"
    reasoning: str            # 2-3 sentence explanation
    confidence: float         # 0.0-1.0 (1.0 = completely certain)
```

### Required Method

#### `evaluate(solution_a, solution_b, arena, task) -> JudgeVote`

**Args**:
- `solution_a`: First solution to compare
- `solution_b`: Second solution to compare
- `arena`: Quality dimension (maintainability, performance, etc.)
- `task`: Programming task being solved

**Returns**:
- `JudgeVote` with winner, reasoning, and confidence

**Raises**:
- `JudgeError`: For API failures, parsing errors, or invalid responses

## Step-by-Step Guide

### Step 1: Create Judge File

```bash
touch src/codegen_bench/judge/my_judge.py
```

### Step 2: Define Judge Class

```python
"""My custom judge implementation."""

import os
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential

from codegen_bench.judge.base import Judge
from codegen_bench.core.judgment import JudgeVote, Vote
from codegen_bench.core.solution import Solution
from codegen_bench.core.arena import Arena
from codegen_bench.core.task import Task
from codegen_bench.exceptions import JudgeError
from codegen_bench.utils.rate_limiter import RateLimiter

class MyJudge(Judge):
    """Custom judge implementation using XYZ AI."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "default-model",
        temperature: float = 0.3,
        variant: int = 0,
        max_requests_per_minute: int = 50,
    ):
        """Initialize MyJudge.

        Args:
            api_key: API key (defaults to MY_API_KEY env var)
            model: Model identifier
            temperature: Sampling temperature
            variant: Prompt variant
            max_requests_per_minute: Rate limit
        """
        super().__init__(model, temperature, variant)

        self.api_key = api_key or os.getenv("MY_API_KEY")
        if not self.api_key:
            raise JudgeError("MY_API_KEY not found")

        self.client = MyAPIClient(api_key=self.api_key)
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=max_requests_per_minute
        )
```

### Step 3: Implement evaluate()

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def evaluate(
    self,
    solution_a: Solution,
    solution_b: Solution,
    arena: Arena,
    task: Task
) -> JudgeVote:
    """Evaluate two solutions using my AI."""

    # 1. Build prompt from arena template
    prompt = self._build_prompt(solution_a, solution_b, arena, task)

    # 2. Apply rate limiting
    self.rate_limiter.acquire()

    # 3. Call API
    try:
        response = self.client.generate(
            prompt=prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=2000,
        )
    except APIError as e:
        raise JudgeError(f"API call failed: {e}") from e

    # 4. Parse response
    vote = self._parse_vote(response.text)

    return vote
```

### Step 4: Build Prompt

Use arena-specific prompt templates:

```python
def _build_prompt(
    self,
    solution_a: Solution,
    solution_b: Solution,
    arena: Arena,
    task: Task
) -> str:
    """Build evaluation prompt.

    Uses the arena's prompt template with task and solution context.
    """
    # Format solutions for display
    solution_a_text = self._format_solution(solution_a)
    solution_b_text = self._format_solution(solution_b)

    # Format constraints
    constraints_text = "\n".join(f"- {c}" for c in task.constraints)

    # Load arena prompt template
    prompt = arena.load_prompt(
        task_spec=f"{task.name}\n\n{task.specification}",
        constraints=constraints_text,
        solution_a=solution_a_text,
        solution_b=solution_b_text,
    )

    return prompt

def _format_solution(self, solution: Solution) -> str:
    """Format solution for display in prompt."""
    if not solution.changed_files:
        return "(No files changed)"

    parts = []
    for path, content in solution.changed_files.items():
        parts.append(f"File: {path}")
        parts.append("```")
        parts.append(content)
        parts.append("```")
        parts.append("")

    return "\n".join(parts)
```

### Step 5: Parse Response

Extract winner, reasoning, and confidence:

```python
import re

def _parse_vote(self, response: str) -> JudgeVote:
    """Parse judge response into JudgeVote.

    Expected format:
        WINNER: A|B|TIE
        REASONING: <explanation>
        CONFIDENCE: <0.0-1.0>
    """
    # Extract WINNER
    winner_match = re.search(
        r"WINNER:\s*(A|B|TIE)",
        response,
        re.IGNORECASE
    )
    if not winner_match:
        raise JudgeError(f"Could not parse WINNER: {response}")

    winner_str = winner_match.group(1).upper()

    # Extract REASONING
    reasoning_match = re.search(
        r"REASONING:\s*(.+?)(?=CONFIDENCE:|$)",
        response,
        re.IGNORECASE | re.DOTALL
    )
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

    # Extract CONFIDENCE
    confidence_match = re.search(
        r"CONFIDENCE:\s*([0-9.]+)",
        response,
        re.IGNORECASE
    )
    confidence = float(confidence_match.group(1)) if confidence_match else 0.5

    # Validate and cast winner
    winner: Vote
    if winner_str == "A":
        winner = "A"
    elif winner_str == "B":
        winner = "B"
    elif winner_str == "TIE":
        winner = "TIE"
    else:
        raise JudgeError(f"Invalid winner: {winner_str}")

    return JudgeVote(
        vote=winner,
        reasoning=reasoning,
        confidence=confidence
    )
```

### Step 6: Add Error Handling

```python
from codegen_bench.exceptions import JudgeError

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def evaluate(self, ...) -> JudgeVote:
    try:
        # ... implementation ...
        pass
    except APITimeoutError as e:
        raise JudgeError(f"API timeout: {e}") from e
    except APIRateLimitError as e:
        raise JudgeError(f"Rate limit exceeded: {e}") from e
    except APIError as e:
        raise JudgeError(f"API error: {e}") from e
    except Exception as e:
        raise JudgeError(f"Unexpected error: {e}") from e
```

### Step 7: Add Tests

Create `tests/unit/test_my_judge.py`:

```python
import pytest
from codegen_bench.judge.my_judge import MyJudge
from codegen_bench.core.solution import Solution
from codegen_bench.core.arena import MAINTAINABILITY
from codegen_bench.core.task import Task
from codegen_bench.exceptions import JudgeError

def test_my_judge_initialization():
    """Test judge initialization."""
    judge = MyJudge(api_key="test-key", model="test-model")

    assert judge.model == "test-model"
    assert judge.temperature == 0.3
    assert judge.variant == 0

def test_my_judge_missing_api_key():
    """Test error when API key missing."""
    with pytest.raises(JudgeError, match="MY_API_KEY"):
        MyJudge(api_key=None)

def test_my_judge_evaluate(mock_task, mock_solutions):
    """Test solution evaluation."""
    judge = MyJudge(api_key="test-key")
    solution_a, solution_b = mock_solutions

    # Mock API response
    judge.client.generate = lambda p: MockResponse(
        text="WINNER: A\nREASONING: Solution A is better\nCONFIDENCE: 0.9"
    )

    vote = judge.evaluate(solution_a, solution_b, MAINTAINABILITY, mock_task)

    assert vote.vote == "A"
    assert vote.confidence == 0.9
    assert "better" in vote.reasoning

def test_my_judge_parse_vote():
    """Test vote parsing."""
    judge = MyJudge(api_key="test-key")

    response = """
    WINNER: B
    REASONING: Solution B has better error handling and clearer logic.
    CONFIDENCE: 0.85
    """

    vote = judge._parse_vote(response)

    assert vote.vote == "B"
    assert vote.confidence == 0.85
    assert "error handling" in vote.reasoning
```

## Implementation Patterns

### Pattern 1: OpenAI-based Judge

```python
import openai

class OpenAIJudge(Judge):
    """Judge using OpenAI models."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4",
        temperature: float = 0.3,
        variant: int = 0,
    ):
        super().__init__(model, temperature, variant)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise JudgeError("OPENAI_API_KEY not found")
        self.client = openai.OpenAI(api_key=self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def evaluate(self, solution_a, solution_b, arena, task) -> JudgeVote:
        prompt = self._build_prompt(solution_a, solution_b, arena, task)

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_vote(response.choices[0].message.content)
```

### Pattern 2: Local Model Judge

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class LocalModelJudge(Judge):
    """Judge using locally-hosted model."""

    def __init__(
        self,
        model_path: str,
        temperature: float = 0.3,
        variant: int = 0,
    ):
        super().__init__(model=model_path, temperature=temperature, variant=variant)

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
        )

    def evaluate(self, solution_a, solution_b, arena, task) -> JudgeVote:
        prompt = self._build_prompt(solution_a, solution_b, arena, task)

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        outputs = self.model.generate(
            **inputs,
            temperature=self.temperature,
            max_new_tokens=500,
        )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return self._parse_vote(response)
```

### Pattern 3: Ensemble Judge

```python
from typing import List
from collections import Counter

class EnsembleJudge(Judge):
    """Ensemble of multiple judges with majority voting."""

    def __init__(
        self,
        judges: List[Judge],
        model: str = "ensemble",
        temperature: float = 0.3,
        variant: int = 0,
    ):
        super().__init__(model, temperature, variant)
        self.judges = judges

    def evaluate(self, solution_a, solution_b, arena, task) -> JudgeVote:
        # Collect votes from all judges
        votes = [
            judge.evaluate(solution_a, solution_b, arena, task)
            for judge in self.judges
        ]

        # Majority voting
        vote_counts = Counter(v.vote for v in votes)
        winner = vote_counts.most_common(1)[0][0]

        # Average confidence
        avg_confidence = sum(v.confidence for v in votes) / len(votes)

        # Combine reasoning
        reasoning = " ".join(
            f"Judge {i+1}: {v.reasoning}"
            for i, v in enumerate(votes)
        )

        return JudgeVote(
            vote=winner,
            reasoning=reasoning,
            confidence=avg_confidence
        )
```

### Pattern 4: Tool-Augmented Judge

```python
class ToolAugmentedJudge(Judge):
    """Judge that runs tests and uses results in evaluation."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=api_key)

    def evaluate(self, solution_a, solution_b, arena, task) -> JudgeVote:
        # Run tests for both solutions
        test_results_a = self._run_tests(solution_a, task)
        test_results_b = self._run_tests(solution_b, task)

        # Build prompt with test results
        prompt = self._build_prompt_with_tests(
            solution_a, solution_b, arena, task,
            test_results_a, test_results_b
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_vote(response.content[0].text)

    def _run_tests(self, solution: Solution, task: Task) -> dict:
        """Run test suite and return results."""
        # Implementation of test execution
        pass
```

## Testing Your Judge

### Unit Tests

```python
def test_judge_initialization():
    """Test judge initializes correctly."""
    judge = MyJudge(api_key="test")
    assert judge.model
    assert judge.temperature >= 0

def test_judge_evaluate():
    """Test judge can evaluate solutions."""
    judge = MyJudge(api_key="test")

    solution_a = Solution(...)
    solution_b = Solution(...)
    arena = MAINTAINABILITY
    task = Task(...)

    vote = judge.evaluate(solution_a, solution_b, arena, task)

    assert vote.vote in ["A", "B", "TIE"]
    assert 0.0 <= vote.confidence <= 1.0
    assert len(vote.reasoning) > 0

def test_judge_parse_vote():
    """Test vote parsing."""
    judge = MyJudge(api_key="test")

    valid_response = """
    WINNER: A
    REASONING: Clear and concise
    CONFIDENCE: 0.9
    """

    vote = judge._parse_vote(valid_response)
    assert vote.vote == "A"
    assert vote.confidence == 0.9

def test_judge_parse_vote_invalid():
    """Test error on invalid response."""
    judge = MyJudge(api_key="test")

    invalid_response = "This is not a valid vote"

    with pytest.raises(JudgeError):
        judge._parse_vote(invalid_response)
```

### Integration Tests

```python
def test_judge_with_real_task():
    """Test judge with actual task and solutions."""
    from codegen_bench.tasks.registry import TaskRegistry

    judge = MyJudge(api_key=os.getenv("MY_API_KEY"))
    task = TaskRegistry.get("task-1")

    # Load two real solutions
    solution_a = load_solution("simple-chat-42")
    solution_b = load_solution("elaborate-prompt-42")

    vote = judge.evaluate(solution_a, solution_b, MAINTAINABILITY, task)

    assert vote.vote in ["A", "B", "TIE"]
    assert vote.confidence > 0
    assert len(vote.reasoning) > 20  # Meaningful reasoning

def test_judge_consistency():
    """Test judge gives consistent results."""
    judge = MyJudge(api_key=os.getenv("MY_API_KEY"), temperature=0.0)

    # Evaluate same pair twice
    vote1 = judge.evaluate(sol_a, sol_b, arena, task)
    vote2 = judge.evaluate(sol_a, sol_b, arena, task)

    # Should be identical (or very similar) at temp=0
    assert vote1.vote == vote2.vote
    assert abs(vote1.confidence - vote2.confidence) < 0.1
```

### Position Bias Test

```python
def test_judge_position_bias():
    """Test judge doesn't favor position A or B."""
    judge = MyJudge(api_key=os.getenv("MY_API_KEY"))

    # Test with A first
    vote_ab = judge.evaluate(sol_a, sol_b, arena, task)

    # Test with B first (swap positions)
    vote_ba = judge.evaluate(sol_b, sol_a, arena, task)

    # If A won in first test, B should win in second test
    if vote_ab.vote == "A":
        assert vote_ba.vote == "B", "Position bias detected"
    elif vote_ab.vote == "B":
        assert vote_ba.vote == "A", "Position bias detected"
    # TIE should remain TIE
```

## Calibration

After implementing a judge, you must calibrate it against ground truth.

### 1. Create Ground Truth Dataset

Collect expert judgments:

```yaml
# calibration/maintainability-ground-truth.yaml
arena: maintainability
pairs:
  - id: pair-001
    task_id: task-1
    solution_a_id: simple-chat-42
    solution_b_id: elaborate-prompt-42
    ground_truth:
      winner: B
      confidence: 0.9
      reasoning: "Solution B has clearer variable names and better documentation"
      expert_id: expert-1

  - id: pair-002
    task_id: task-2
    solution_a_id: simple-chat-43
    solution_b_id: elaborate-prompt-43
    ground_truth:
      winner: A
      confidence: 0.8
      reasoning: "Solution A follows existing conventions better"
      expert_id: expert-2
```

### 2. Run Calibration

```bash
codegen-bench calibrate \
  --judge my-judge \
  --ground-truth calibration/maintainability-ground-truth.yaml \
  --arena maintainability \
  --output my-judge-calibration.json
```

### 3. Analyze Results

The calibration report shows:

```json
{
  "agreement_rate": 0.87,
  "fleiss_kappa": 0.72,
  "position_bias": {
    "a_wins": 48,
    "b_wins": 52,
    "ties": 10,
    "bias_percentage": 4.0
  },
  "confusion_matrix": {
    "A_predicted_A": 45,
    "A_predicted_B": 3,
    "B_predicted_B": 47,
    "B_predicted_A": 5
  }
}
```

**Target metrics**:
- Agreement rate: ≥ 85%
- Fleiss' Kappa: ≥ 0.7
- Position bias: < 10%

### 4. Iterate on Prompts

If calibration fails, refine arena prompts:

1. Identify disagreements with experts
2. Analyze error patterns
3. Update arena prompt templates
4. Re-run calibration

## Example: ClaudeCodeJudge

Here's a complete example using Claude Code as a judge:

```python
"""ClaudeCodeJudge: Use Claude Code CLI as a judge."""

import subprocess
import tempfile
import re
from pathlib import Path

from codegen_bench.judge.base import Judge
from codegen_bench.core.judgment import JudgeVote, Vote
from codegen_bench.core.solution import Solution
from codegen_bench.core.arena import Arena
from codegen_bench.core.task import Task
from codegen_bench.exceptions import JudgeError

class ClaudeCodeJudge(Judge):
    """Use Claude Code CLI to judge solutions."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.3,
        variant: int = 0,
    ):
        super().__init__(model, temperature, variant)

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise JudgeError("ANTHROPIC_API_KEY required")

        # Verify claude-code CLI available
        try:
            subprocess.run(
                ["claude-code", "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise JudgeError("claude-code CLI not found")

    def evaluate(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task
    ) -> JudgeVote:
        """Evaluate solutions using Claude Code."""

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            solution_a, solution_b, arena, task
        )

        # Run Claude Code with prompt
        response = self._run_claude_code(prompt)

        # Parse vote from response
        vote = self._parse_vote(response)

        return vote

    def _build_evaluation_prompt(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task
    ) -> str:
        """Build evaluation prompt for Claude Code."""

        solution_a_text = self._format_solution(solution_a)
        solution_b_text = self._format_solution(solution_b)
        constraints_text = "\n".join(f"- {c}" for c in task.constraints)

        # Use arena prompt template
        return arena.load_prompt(
            task_spec=f"{task.name}\n\n{task.specification}",
            constraints=constraints_text,
            solution_a=solution_a_text,
            solution_b=solution_b_text,
        )

    def _run_claude_code(self, prompt: str) -> str:
        """Run Claude Code CLI with prompt."""

        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = self.api_key

        try:
            result = subprocess.run(
                [
                    "claude-code",
                    "--model", self.model,
                    "--message", prompt,
                    "--no-confirm",
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            raise JudgeError("Claude Code timed out")
        except subprocess.CalledProcessError as e:
            raise JudgeError(f"Claude Code failed: {e.stderr}")

    def _format_solution(self, solution: Solution) -> str:
        """Format solution for display."""
        if not solution.changed_files:
            return "(No files changed)"

        parts = []
        for path, content in solution.changed_files.items():
            parts.append(f"File: {path}")
            parts.append("```")
            parts.append(content)
            parts.append("```")
            parts.append("")

        return "\n".join(parts)

    def _parse_vote(self, response: str) -> JudgeVote:
        """Parse Claude Code output into JudgeVote."""

        # Extract WINNER
        winner_match = re.search(
            r"WINNER:\s*(A|B|TIE)",
            response,
            re.IGNORECASE
        )
        if not winner_match:
            raise JudgeError(f"Could not parse WINNER: {response}")

        winner_str = winner_match.group(1).upper()

        # Extract REASONING
        reasoning_match = re.search(
            r"REASONING:\s*(.+?)(?=CONFIDENCE:|$)",
            response,
            re.IGNORECASE | re.DOTALL
        )
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        # Extract CONFIDENCE
        confidence_match = re.search(
            r"CONFIDENCE:\s*([0-9.]+)",
            response,
            re.IGNORECASE
        )
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5

        # Validate winner
        winner: Vote
        if winner_str == "A":
            winner = "A"
        elif winner_str == "B":
            winner = "B"
        elif winner_str == "TIE":
            winner = "TIE"
        else:
            raise JudgeError(f"Invalid winner: {winner_str}")

        return JudgeVote(
            vote=winner,
            reasoning=reasoning,
            confidence=confidence
        )

    def __str__(self) -> str:
        return f"ClaudeCodeJudge(model={self.model}, variant={self.variant})"
```

### Usage

```python
from codegen_bench.judge.claude_code_judge import ClaudeCodeJudge

# Initialize judge
judge = ClaudeCodeJudge(model="claude-sonnet-4-20250514")

# Evaluate solutions
vote = judge.evaluate(solution_a, solution_b, arena, task)

print(f"Winner: {vote.vote}")
print(f"Reasoning: {vote.reasoning}")
print(f"Confidence: {vote.confidence}")
```

## Best Practices

### 1. Error Handling

Always handle API errors gracefully:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def evaluate(self, ...) -> JudgeVote:
    try:
        response = self.client.generate(prompt)
        return self._parse_vote(response.text)
    except APIError as e:
        raise JudgeError(f"API failed: {e}") from e
```

### 2. Rate Limiting

Use rate limiter to avoid hitting API limits:

```python
from codegen_bench.utils.rate_limiter import RateLimiter

self.rate_limiter = RateLimiter(max_requests_per_minute=50)

def evaluate(self, ...) -> JudgeVote:
    self.rate_limiter.acquire()  # Blocks if rate limit exceeded
    response = self.client.generate(prompt)
    ...
```

### 3. Logging

Add structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)

def evaluate(self, ...) -> JudgeVote:
    logger.info(
        "judge_evaluating",
        judge=str(self),
        task_id=task.id,
        arena=arena.name,
    )

    vote = ...

    logger.info(
        "judge_vote_cast",
        winner=vote.vote,
        confidence=vote.confidence,
    )

    return vote
```

### 4. Prompt Consistency

Always use arena prompt templates:

```python
# Good: Use arena templates
prompt = arena.load_prompt(
    task_spec=...,
    constraints=...,
    solution_a=...,
    solution_b=...,
)

# Bad: Custom prompts bypass calibration
prompt = f"Compare these solutions: {sol_a} vs {sol_b}"
```

### 5. Reproducibility

Use temperature for consistency:

```python
# Deterministic evaluation
judge = MyJudge(temperature=0.0)

# Diverse ensemble
judges = [
    MyJudge(temperature=0.3, variant=0),
    MyJudge(temperature=0.3, variant=1),
    MyJudge(temperature=0.3, variant=2),
]
```

## Troubleshooting

### Problem: Low Agreement with Ground Truth

**Diagnosis**: Judge disagrees with experts > 15%

**Solution**:
1. Review disagreement cases
2. Check if judge understands criteria
3. Refine arena prompt templates
4. Add contrastive examples
5. Re-calibrate

### Problem: Position Bias

**Diagnosis**: Judge favors solution A or B

**Solution**:
1. Test with position-swapped pairs
2. Remove suggestive language from prompts
3. Ensure neutral solution formatting
4. Add position randomization in tests

### Problem: All Votes are TIE

**Diagnosis**: Judge can't discriminate solutions

**Solution**:
1. Check if criteria are too strict
2. Test with clearly different solutions
3. Adjust confidence thresholds
4. Provide more context in prompts

### Problem: API Timeouts

**Diagnosis**: Requests timing out

**Solution**:
1. Reduce prompt length
2. Increase timeout limits
3. Add retry logic
4. Use faster model if available

## Next Steps

1. **Implement your judge** following this guide
2. **Add comprehensive tests** (>90% coverage)
3. **Run calibration** against ground truth
4. **Iterate** until ≥85% agreement
5. **Document** usage and limitations
6. **Submit PR** if contributing to BrownBench

## References

- Judge base class: `src/codegen_bench/judge/base.py`
- ClaudeJudge example: `src/codegen_bench/judge/claude_judge.py`
- JudgeVote: `src/codegen_bench/core/judgment.py`
- Calibration: `src/codegen_bench/stats/calibration.py`
- Ground truth format: `src/codegen_bench/stats/ground_truth.py`
