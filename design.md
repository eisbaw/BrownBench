# Technical Design Document: AI Code Generation Benchmark

**Version:** 0.1.0
**Status:** Draft
**Last Updated:** 2025-10-06

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Core Components](#core-components)
5. [DUT Catalog](#dut-catalog)
6. [Evaluation System](#evaluation-system)
7. [Statistical Engine](#statistical-engine)
8. [Isolation & Reproducibility](#isolation--reproducibility)
9. [Data Models](#data-models)
10. [CLI Design](#cli-design)
11. [Configuration System](#configuration-system)
12. [Development Workflow](#development-workflow)

---

## Overview

This framework implements a statistically rigorous benchmark for AI code generation approaches. The key design principles are:

- **Isolation**: Each DUT runs in a completely isolated environment
- **Reproducibility**: All randomness is controlled via seeds, all configs versioned
- **Statistical Rigor**: Proper power analysis, multiple comparison correction, effect sizes
- **Cost Awareness**: Track and optimize API costs via adaptive designs
- **Extensibility**: Easy to add new DUTs, tasks, judges, and arenas

---

## Technology Stack

### Core Technologies

- **Python 3.12**: Modern type hints, performance improvements
- **uv**: Fast package installer and resolver (replaces pip/pip-tools)
- **Nix**: Reproducible development environments via shell.nix
- **Just**: Command runner for common tasks (replaces Makefiles)

### Key Dependencies

**Package Management:**
```toml
# pyproject.toml will use uv for dependency resolution
[project]
name = "codegen-bench"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    # Core
    "click>=8.1.0",           # CLI framework
    "pydantic>=2.5.0",        # Data validation
    "pyyaml>=6.0",            # Config parsing
    "rich>=13.7.0",           # Terminal formatting
    "structlog>=24.1.0",      # Structured logging

    # AI APIs
    "anthropic>=0.18.0",      # Claude API
    "openai>=1.12.0",         # OpenAI API

    # Statistical Analysis
    "numpy>=1.26.0",
    "scipy>=1.11.0",
    "pandas>=2.1.0",
    "statsmodels>=0.14.0",    # Power analysis, mixed models
    "trueskill>=0.4.5",       # TrueSkill rating
    "pingouin>=0.5.4",        # Effect sizes

    # Multi-Objective Optimization
    "pymoo>=0.6.1",           # Pareto frontiers

    # Visualization
    "matplotlib>=3.8.0",
    "seaborn>=0.13.0",
    "plotly>=5.18.0",

    # Utilities
    "tqdm>=4.66.0",           # Progress bars
    "tenacity>=8.2.0",        # Retry logic
    "python-dotenv>=1.0.0",   # Environment variables
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.8.0",
    "ruff>=0.1.0",            # Fast linter/formatter
    "ipython>=8.20.0",
]
```

**Why uv over pip?**
- 10-100x faster dependency resolution
- Built-in lock file support
- Better conflict resolution
- Compatible with pyproject.toml

---

## Project Structure

```
codegen-bench/
├── pyproject.toml           # Project metadata, dependencies
├── uv.lock                  # Locked dependencies (uv-generated)
├── shell.nix                # Nix development environment
├── justfile                 # Task automation
├── README.md
├── design.md               # This document
│
├── src/
│   └── codegen_bench/
│       ├── __init__.py
│       ├── __main__.py      # CLI entry point
│       │
│       ├── cli/             # Command-line interface
│       │   ├── __init__.py
│       │   ├── main.py      # Click root command
│       │   ├── init.py      # codegen-bench init
│       │   ├── generate.py  # codegen-bench generate
│       │   ├── judge.py     # codegen-bench judge
│       │   ├── tournament.py
│       │   ├── leaderboard.py
│       │   ├── analyze.py
│       │   ├── calibrate.py
│       │   └── preregister.py
│       │
│       ├── core/            # Core domain models
│       │   ├── __init__.py
│       │   ├── task.py      # Task dataclass
│       │   ├── solution.py  # Solution dataclass
│       │   ├── arena.py     # Arena (quality dimension)
│       │   ├── judgment.py  # Judge vote, consensus
│       │   └── rating.py    # ELO/TrueSkill ratings
│       │
│       ├── dut/             # Device Under Test implementations
│       │   ├── __init__.py
│       │   ├── base.py      # Abstract base class
│       │   ├── registry.py  # DUT registry/factory
│       │   ├── simple_chat.py
│       │   ├── elaborate_prompt.py
│       │   ├── agentic_loop.py
│       │   ├── human_baseline.py
│       │   └── custom.py    # Load external DUT
│       │
│       ├── tasks/           # Task suite management
│       │   ├── __init__.py
│       │   ├── loader.py    # Load tasks from YAML
│       │   ├── validator.py # Validate task structure
│       │   └── builtin/     # Built-in task definitions
│       │       └── *.yaml
│       │
│       ├── cache/           # Solution caching
│       │   ├── __init__.py
│       │   ├── store.py     # Cache management
│       │   └── generator.py # Generate & cache solutions
│       │
│       ├── judge/           # AI Judge orchestration
│       │   ├── __init__.py
│       │   ├── base.py      # Judge abstract class
│       │   ├── orchestrator.py  # Multi-judge consensus
│       │   ├── claude_judge.py
│       │   ├── gpt_judge.py
│       │   └── prompts/     # Judge prompt templates
│       │       ├── maintainability.txt
│       │       ├── architecture.txt
│       │       └── ...
│       │
│       ├── stats/           # Statistical analysis
│       │   ├── __init__.py
│       │   ├── ratings/
│       │   │   ├── trueskill.py
│       │   │   ├── glicko2.py
│       │   │   └── bayesian_elo.py
│       │   ├── significance.py   # Hypothesis tests
│       │   ├── correction.py     # Multiple comparison
│       │   ├── effect_size.py    # Hedges' g, Cohen's h
│       │   ├── power.py          # Power analysis
│       │   ├── variance.py       # Mixed models, ICC
│       │   ├── adaptive/         # Adaptive trial designs
│       │   │   ├── mams.py       # Multi-arm multi-stage
│       │   │   ├── sequential.py # Group sequential
│       │   │   └── bayesian.py   # Bayesian adaptive
│       │   └── pareto.py         # Pareto frontier analysis
│       │
│       ├── isolation/       # DUT isolation mechanisms
│       │   ├── __init__.py
│       │   ├── sandbox.py   # Execution sandbox
│       │   ├── resource_limiter.py  # CPU/memory/time limits
│       │   └── determinism.py       # Seed control
│       │
│       ├── reporting/       # Result reporting
│       │   ├── __init__.py
│       │   ├── terminal.py  # Rich terminal output
│       │   ├── json.py      # JSON export
│       │   ├── html.py      # HTML reports
│       │   ├── latex.py     # LaTeX tables
│       │   └── plots.py     # Plotly visualizations
│       │
│       ├── config/          # Configuration management
│       │   ├── __init__.py
│       │   ├── schema.py    # Pydantic config models
│       │   └── defaults.py  # Default values
│       │
│       └── utils/           # Utilities
│           ├── __init__.py
│           ├── logging.py   # Structured logging setup
│           ├── api_client.py # Rate-limited API wrapper
│           └── validation.py # Schema validation
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── unit/
│   │   ├── test_dut.py
│   │   ├── test_stats.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_tournament.py
│   │   └── ...
│   └── fixtures/
│       ├── tasks/
│       ├── solutions/
│       └── ground_truth/
│
├── data/                    # Runtime data (gitignored)
│   ├── cache/               # Solution cache
│   ├── results/             # Tournament results
│   └── logs/                # Execution logs
│
├── tasks/                   # Task definitions (version controlled)
│   ├── core/
│   │   ├── task_001.yaml
│   │   └── ...
│   └── embedded/
│       └── ...
│
├── configs/                 # Example configurations
│   ├── default.yaml
│   ├── duts/
│   │   ├── simple-chat.yaml
│   │   ├── elaborate.yaml
│   │   └── ...
│   └── preregistrations/
│       └── example.yaml
│
└── docs/
    ├── user-guide.md
    ├── developer-guide.md
    └── statistical-methods.md
```

---

## Core Components

### 1. Task Suite Manager (`tasks/`)

**Purpose**: Load, validate, and manage benchmark tasks.

**Key Classes:**

```python
# src/codegen_bench/core/task.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

@dataclass
class Task:
    """A single benchmark task"""
    id: str
    name: str
    project: str
    domain: str
    difficulty: Literal["easy", "medium", "hard"]

    # Context
    codebase_path: Path
    specification: str
    constraints: list[str] = field(default_factory=list)

    # Validation
    test_suite_path: Optional[Path] = None
    compile_command: Optional[str] = None
    test_command: Optional[str] = None

    # Metadata
    expected_human_time_minutes: int = 0
    key_files: list[str] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)

    # Reference solution (for metrics)
    reference_solution_path: Optional[Path] = None

    @classmethod
    def from_yaml(cls, path: Path) -> "Task":
        """Load task from YAML file"""
        # Implementation
        pass

    def validate(self) -> bool:
        """Validate task structure"""
        # Check files exist, commands work, etc.
        pass
```

```python
# src/codegen_bench/tasks/loader.py
from pathlib import Path
from typing import Iterable

class TaskLoader:
    """Load tasks from various sources"""

    def __init__(self, base_path: Path):
        self.base_path = base_path

    def load_task(self, task_id: str) -> Task:
        """Load single task by ID"""
        path = self.base_path / f"{task_id}.yaml"
        return Task.from_yaml(path)

    def load_task_set(self, name: str) -> list[Task]:
        """Load predefined task set (core, embedded, all)"""
        if name == "core":
            pattern = "core/*.yaml"
        elif name == "embedded":
            pattern = "embedded/*.yaml"
        elif name == "all":
            pattern = "**/*.yaml"
        else:
            # Custom pattern
            pattern = name

        return [
            Task.from_yaml(p)
            for p in self.base_path.glob(pattern)
        ]
```

---

### 2. DUT Controller (`dut/`)

**Purpose**: Abstract interface for code generation approaches with complete isolation.

**Base Interface:**

```python
# src/codegen_bench/dut/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from codegen_bench.core.task import Task
from codegen_bench.core.solution import Solution

@dataclass
class ApproachMetadata:
    """Metadata about a code generation approach"""
    id: str
    name: str
    description: str
    version: str
    model: Optional[str] = None
    provider: Optional[str] = None
    config: dict = None

class CodeGenerationApproach(ABC):
    """Abstract base for all DUT implementations"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution for task

        Args:
            task: Task specification
            seed: Random seed for reproducibility

        Returns:
            Solution with code, metrics, metadata
        """
        pass

    @abstractmethod
    def get_metadata(self) -> ApproachMetadata:
        """Return approach configuration"""
        pass

    def __str__(self) -> str:
        return f"{self.get_metadata().name} (v{self.get_metadata().version})"
```

**Solution Model:**

```python
# src/codegen_bench/core/solution.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Solution:
    """Output from a code generation approach"""

    # Identifiers
    approach_id: str
    task_id: str
    seed: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Outputs
    changed_files: dict[str, str] = field(default_factory=dict)  # path -> content
    new_files: dict[str, str] = field(default_factory=dict)
    deleted_files: list[str] = field(default_factory=list)
    tests: Optional[dict[str, str]] = None
    documentation: Optional[str] = None

    # Metrics
    generation_time_seconds: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_calls: int = 0
    cost_usd: float = 0.0

    # Intermediate state (for analysis)
    reasoning_trace: Optional[str] = None
    iterations: int = 1

    # Validation results
    compiles: Optional[bool] = None
    tests_pass: Optional[bool] = None
    test_output: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dict for caching"""
        pass

    @classmethod
    def from_dict(cls, data: dict) -> "Solution":
        """Deserialize from dict"""
        pass
```

---

### 3. Solution Cache (`cache/`)

**Purpose**: Avoid regenerating solutions, separate solution variance from judge variance.

```python
# src/codegen_bench/cache/store.py
from pathlib import Path
import json
import hashlib
from typing import Optional

from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.base import CodeGenerationApproach

class SolutionCache:
    """Disk-based solution cache"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, dut: CodeGenerationApproach, task: Task, seed: int) -> str:
        """Generate unique cache key"""
        metadata = dut.get_metadata()
        key_data = f"{metadata.id}_{metadata.version}_{task.id}_{seed}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(self, dut: CodeGenerationApproach, task: Task, seed: int) -> Optional[Solution]:
        """Retrieve cached solution"""
        key = self._cache_key(dut, task, seed)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        with open(cache_file) as f:
            data = json.load(f)

        return Solution.from_dict(data)

    def put(self, dut: CodeGenerationApproach, task: Task, seed: int, solution: Solution):
        """Store solution in cache"""
        key = self._cache_key(dut, task, seed)
        cache_file = self.cache_dir / f"{key}.json"

        with open(cache_file, "w") as f:
            json.dump(solution.to_dict(), f, indent=2)
```

```python
# src/codegen_bench/cache/generator.py
from typing import Optional
import structlog

from codegen_bench.isolation.sandbox import IsolationSandbox

logger = structlog.get_logger()

class SolutionGenerator:
    """Generate solutions with caching and isolation"""

    def __init__(self, cache: SolutionCache, isolation: IsolationSandbox):
        self.cache = cache
        self.isolation = isolation

    def generate(
        self,
        dut: CodeGenerationApproach,
        task: Task,
        seed: int,
        force_regenerate: bool = False
    ) -> Solution:
        """Generate or retrieve cached solution"""

        # Try cache first
        if not force_regenerate:
            cached = self.cache.get(dut, task, seed)
            if cached:
                logger.info("cache_hit", dut=dut.get_metadata().id, task=task.id, seed=seed)
                return cached

        # Generate new solution in isolated environment
        logger.info("generating_solution", dut=dut.get_metadata().id, task=task.id, seed=seed)

        solution = self.isolation.run(
            fn=dut.solve,
            args=(task, seed),
            timeout=self._get_timeout(task),
            memory_limit_mb=4096
        )

        # Cache result
        self.cache.put(dut, task, seed, solution)

        return solution

    def generate_batch(
        self,
        dut: CodeGenerationApproach,
        task: Task,
        seeds: list[int]
    ) -> list[Solution]:
        """Generate multiple solutions with different seeds"""
        return [self.generate(dut, task, seed) for seed in seeds]
```

---

### 4. Judge Orchestrator (`judge/`)

**Purpose**: Coordinate AI judges for solution comparison.

**Arena Definition:**

```python
# src/codegen_bench/core/arena.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Arena:
    """A quality dimension for evaluation"""
    name: str
    display_name: str
    description: str
    criteria: list[str]
    prompt_template_path: Path

    def load_prompt(self, **kwargs) -> str:
        """Load and format prompt template"""
        with open(self.prompt_template_path) as f:
            template = f.read()
        return template.format(**kwargs)

# Built-in arenas
MAINTAINABILITY = Arena(
    name="maintainability",
    display_name="Maintainability",
    description="Code clarity, documentation, conventions",
    criteria=[
        "Code is easy to read and understand",
        "Documentation is clear and helpful",
        "Follows existing conventions",
        "Error handling is robust"
    ],
    prompt_template_path=Path("judge/prompts/maintainability.txt")
)

ARCHITECTURAL_INTEGRITY = Arena(
    name="architecture",
    display_name="Architectural Integrity",
    description="Respects existing patterns and abstractions",
    criteria=[
        "Respects existing architectural patterns",
        "Minimizes coupling",
        "Preserves abstractions",
        "Fits the mental model"
    ],
    prompt_template_path=Path("judge/prompts/architecture.txt")
)

# ... other arenas
```

**Judge Implementation:**

```python
# src/codegen_bench/judge/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

Vote = Literal["A", "B", "TIE"]

@dataclass
class JudgeVote:
    """A single judge's vote"""
    vote: Vote
    reasoning: str
    confidence: float  # 0-1

class Judge(ABC):
    """Abstract base for AI judges"""

    def __init__(self, model: str, temperature: float = 0.3, variant: int = 0):
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
        """Compare two solutions in given arena"""
        pass
```

```python
# src/codegen_bench/judge/claude_judge.py
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

class ClaudeJudge(Judge):
    """Claude-based judge"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.client = anthropic.Anthropic(api_key=api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def evaluate(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task
    ) -> JudgeVote:
        """Evaluate using Claude"""

        # Build prompt
        prompt = arena.load_prompt(
            task_spec=task.specification,
            solution_a=self._format_solution(solution_a),
            solution_b=self._format_solution(solution_b),
            constraints=task.constraints
        )

        # Call API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        return self._parse_vote(response.content[0].text)

    def _format_solution(self, sol: Solution) -> str:
        """Format solution for prompt"""
        # Show changed files with diffs
        pass

    def _parse_vote(self, response: str) -> JudgeVote:
        """Extract vote from response"""
        # Parse structured output
        # Format: VOTE: A|B|TIE\nREASONING: ...\nCONFIDENCE: 0.XX
        pass
```

**Orchestrator:**

```python
# src/codegen_bench/judge/orchestrator.py
from collections import Counter
from dataclasses import dataclass

@dataclass
class JudgmentResult:
    """Consensus result from multiple judges"""
    winner: Vote
    votes: list[JudgeVote]
    agreement_rate: float
    confidence: float

class JudgeOrchestrator:
    """Coordinate multiple judges"""

    def __init__(self, judges: list[Judge]):
        self.judges = judges

    def compare(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task
    ) -> JudgmentResult:
        """Get consensus judgment"""

        votes = []
        for judge in self.judges:
            vote = judge.evaluate(solution_a, solution_b, arena, task)
            votes.append(vote)

        # Compute consensus
        consensus = self._compute_consensus(votes)
        agreement = self._agreement_rate(votes)
        confidence = self._compute_confidence(votes)

        return JudgmentResult(
            winner=consensus,
            votes=votes,
            agreement_rate=agreement,
            confidence=confidence
        )

    def _compute_consensus(self, votes: list[JudgeVote]) -> Vote:
        """Majority vote with tie-breaking"""
        vote_counts = Counter(v.vote for v in votes)

        # If 2+ judges agree, use majority
        if len(self.judges) == 3:
            if vote_counts.most_common(1)[0][1] >= 2:
                return vote_counts.most_common(1)[0][0]
            return "TIE"

        # For 5 judges, need 3+ agreement
        if len(self.judges) == 5:
            if vote_counts.most_common(1)[0][1] >= 3:
                return vote_counts.most_common(1)[0][0]
            return "TIE"

        # Default: most common vote
        return vote_counts.most_common(1)[0][0]

    def _agreement_rate(self, votes: list[JudgeVote]) -> float:
        """Fraction of judges agreeing with majority"""
        consensus = self._compute_consensus(votes)
        agrees = sum(1 for v in votes if v.vote == consensus)
        return agrees / len(votes)

    def _compute_confidence(self, votes: list[JudgeVote]) -> float:
        """Average confidence of judges"""
        return sum(v.confidence for v in votes) / len(votes)
```

---

### 5. Statistical Engine (`stats/`)

**Rating Systems:**

```python
# src/codegen_bench/stats/ratings/trueskill.py
from trueskill import Rating, rate, quality
from typing import Literal

class TrueSkillRating:
    """TrueSkill rating with uncertainty"""

    def __init__(self, mu: float = 25.0, sigma: float = 8.33):
        self.rating = Rating(mu, sigma)

    def update(self, opponent: "TrueSkillRating", outcome: Literal["win", "loss", "tie"]):
        """Update after a match"""
        if outcome == "win":
            ranks = [0, 1]  # 0 is best
        elif outcome == "loss":
            ranks = [1, 0]
        else:  # tie
            ranks = [0, 0]

        new_ratings = rate([[self.rating], [opponent.rating]], ranks=ranks)
        self.rating = new_ratings[0][0]
        opponent.rating = new_ratings[1][0]

    def conservative_estimate(self) -> float:
        """95% confidence lower bound"""
        return self.rating.mu - 2 * self.rating.sigma

    def match_quality(self, opponent: "TrueSkillRating") -> float:
        """Predict match quality (0-1)"""
        return quality([[self.rating], [opponent.rating]])

    @property
    def mu(self) -> float:
        return self.rating.mu

    @property
    def sigma(self) -> float:
        return self.rating.sigma
```

**Effect Size Calculation:**

```python
# src/codegen_bench/stats/effect_size.py
import numpy as np
from scipy import stats
from dataclasses import dataclass

@dataclass
class EffectSize:
    """Effect size with confidence interval"""
    metric: str  # 'hedges_g', 'cohens_h', etc.
    value: float
    ci_lower: float
    ci_upper: float
    cles: float  # Common Language Effect Size
    interpretation: str
    sample_sizes: tuple[int, int]

def hedges_g(group_a: np.ndarray, group_b: np.ndarray, ci: float = 0.95) -> EffectSize:
    """Calculate Hedges' g with CI"""

    n_a, n_b = len(group_a), len(group_b)

    # Pooled standard deviation
    pooled_sd = np.sqrt(
        ((n_a - 1) * np.var(group_a, ddof=1) + (n_b - 1) * np.var(group_b, ddof=1))
        / (n_a + n_b - 2)
    )

    # Cohen's d
    d = (np.mean(group_a) - np.mean(group_b)) / pooled_sd

    # Hedges' correction for small samples
    correction = 1 - (3 / (4 * (n_a + n_b) - 9))
    g = d * correction

    # Bootstrap CI
    from scipy.stats import bootstrap

    def stat_fn(a, b, axis):
        # Recalculate within bootstrap
        pooled = np.sqrt(
            ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1))
            / (len(a) + len(b) - 2)
        )
        d_boot = (np.mean(a) - np.mean(b)) / pooled
        return d_boot * correction

    res = bootstrap(
        (group_a, group_b),
        lambda a, b, axis: stat_fn(a, b, axis),
        n_resamples=10000,
        confidence_level=ci,
        method='percentile'
    )

    # Common Language Effect Size
    cles = np.mean([a > b for a in group_a for b in group_b])

    # Interpret
    interpretation = _interpret_hedges_g(g)

    return EffectSize(
        metric="hedges_g",
        value=g,
        ci_lower=res.confidence_interval.low,
        ci_upper=res.confidence_interval.high,
        cles=cles,
        interpretation=interpretation,
        sample_sizes=(n_a, n_b)
    )

def _interpret_hedges_g(g: float) -> str:
    """Interpret effect size (SE field norms)"""
    abs_g = abs(g)
    if abs_g < 0.20:
        return "negligible"
    elif abs_g < 0.50:
        return "small"
    elif abs_g < 0.80:
        return "medium"
    else:
        return "large"
```

**Multiple Comparison Correction:**

```python
# src/codegen_bench/stats/correction.py
from typing import Literal
import numpy as np
from statsmodels.stats.multitest import multipletests

CorrectionMethod = Literal["fdr_bh", "fdr_by", "bonferroni", "holm", "dunnett"]

def correct_pvalues(
    p_values: list[float],
    method: CorrectionMethod = "fdr_bh",
    alpha: float = 0.05
) -> tuple[np.ndarray, np.ndarray]:
    """Apply multiple comparison correction

    Args:
        p_values: Raw p-values
        method: Correction method
        alpha: Significance level

    Returns:
        (rejected, p_adjusted): Boolean array and adjusted p-values
    """

    if method == "dunnett":
        # Special handling for many-to-one comparisons
        # Requires separate implementation
        raise NotImplementedError("Dunnett's test requires scipy.stats.dunnett")

    rejected, p_adjusted, _, _ = multipletests(
        p_values,
        alpha=alpha,
        method=method
    )

    return rejected, p_adjusted
```

**Adaptive Designs:**

```python
# src/codegen_bench/stats/adaptive/sequential.py
import numpy as np
from scipy.stats import norm
from dataclasses import dataclass
from typing import Literal

@dataclass
class SequentialBoundaries:
    """O'Brien-Fleming boundaries"""
    checkpoints: np.ndarray  # Sample sizes for interim analyses
    alpha_spending: np.ndarray  # Alpha spent at each look
    z_boundaries: np.ndarray  # Z-score boundaries

class GroupSequentialDesign:
    """Group sequential design with early stopping"""

    def __init__(self, max_n: int = 300, num_looks: int = 3, alpha: float = 0.05):
        self.max_n = max_n
        self.num_looks = num_looks
        self.alpha = alpha
        self.boundaries = self._compute_obrien_fleming()

    def _compute_obrien_fleming(self) -> SequentialBoundaries:
        """Conservative early stopping boundaries"""

        # Information fractions
        checkpoints = np.linspace(1/self.num_looks, 1.0, self.num_looks) * self.max_n
        info_frac = checkpoints / self.max_n

        # O'Brien-Fleming spending function
        z_alpha = norm.ppf(1 - self.alpha / 2)
        alpha_spending = 2 * (1 - norm.cdf(z_alpha / np.sqrt(info_frac)))

        # Z-score boundaries
        z_boundaries = z_alpha / np.sqrt(info_frac)

        return SequentialBoundaries(
            checkpoints=checkpoints.astype(int),
            alpha_spending=alpha_spending,
            z_boundaries=z_boundaries
        )

    def check_stopping(
        self,
        n: int,
        z_statistic: float
    ) -> Literal["continue", "stop_efficacy", "stop_futility"]:
        """Check if trial should stop"""

        # Find which look we're at
        look_idx = np.searchsorted(self.boundaries.checkpoints, n)

        if look_idx >= len(self.boundaries.checkpoints):
            return "continue"

        # Efficacy boundary
        if abs(z_statistic) > self.boundaries.z_boundaries[look_idx]:
            return "stop_efficacy"

        # Futility check (conditional power < 20%)
        cond_power = self._conditional_power(n, z_statistic)
        if cond_power < 0.20:
            return "stop_futility"

        return "continue"

    def _conditional_power(self, n: int, z: float) -> float:
        """Calculate conditional power"""
        # Simplified calculation
        remaining_n = self.max_n - n
        if remaining_n <= 0:
            return 1.0 if abs(z) > 1.96 else 0.0

        # Approximate conditional power
        # P(reject H0 at end | current z)
        return 1 - norm.cdf(1.96 - z * np.sqrt(n / self.max_n))
```

---

### 6. Isolation System (`isolation/`)

**Purpose**: Ensure DUTs run in isolated, reproducible environments.

```python
# src/codegen_bench/isolation/sandbox.py
import os
import resource
import signal
import multiprocessing as mp
from typing import Callable, Any, Optional
from dataclasses import dataclass

@dataclass
class ResourceLimits:
    """Resource limits for DUT execution"""
    timeout_seconds: int = 3600  # 1 hour
    memory_mb: int = 4096
    max_api_calls: Optional[int] = None
    max_cost_usd: Optional[float] = None

class IsolationSandbox:
    """Execute DUT in isolated environment"""

    def __init__(self, limits: ResourceLimits):
        self.limits = limits

    def run(
        self,
        fn: Callable,
        args: tuple = (),
        kwargs: dict = None,
        timeout: Optional[int] = None,
        memory_limit_mb: Optional[int] = None
    ) -> Any:
        """Run function with resource limits"""

        timeout = timeout or self.limits.timeout_seconds
        memory_limit_mb = memory_limit_mb or self.limits.memory_mb
        kwargs = kwargs or {}

        # Use multiprocessing for isolation
        with mp.Pool(processes=1) as pool:
            async_result = pool.apply_async(
                _run_with_limits,
                args=(fn, args, kwargs, memory_limit_mb)
            )

            try:
                result = async_result.get(timeout=timeout)
                return result
            except mp.TimeoutError:
                pool.terminate()
                raise TimeoutError(f"DUT exceeded timeout of {timeout}s")
            except Exception as e:
                pool.terminate()
                raise RuntimeError(f"DUT execution failed: {e}")

def _run_with_limits(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    memory_limit_mb: int
) -> Any:
    """Worker function with resource limits"""

    # Set memory limit (virtual memory)
    memory_bytes = memory_limit_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

    # Execute function
    return fn(*args, **kwargs)
```

**Determinism Control:**

```python
# src/codegen_bench/isolation/determinism.py
import random
import numpy as np
import os

def set_seed(seed: int):
    """Set all random seeds for reproducibility"""
    random.seed(seed)
    np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)

    # Note: API calls to Claude/GPT may still have variance
    # We handle this by generating multiple samples
```

---

## DUT Catalog

### Built-in DUT Implementations

#### 1. Simple Chat DUT

```python
# src/codegen_bench/dut/simple_chat.py
from codegen_bench.dut.base import CodeGenerationApproach, ApproachMetadata
from codegen_bench.core.task import Task
from codegen_bench.core.solution import Solution
import anthropic
import time

class SimpleChatDUT(CodeGenerationApproach):
    """Single-turn chat with minimal prompting"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.api_key = config.get("api_key")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution with simple prompt"""

        start_time = time.time()

        # Build simple prompt
        prompt = self._build_prompt(task)

        # Single API call
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        elapsed = time.time() - start_time

        # Parse response
        changed_files = self._parse_code_changes(response.content[0].text)

        # Calculate cost
        cost = self._calculate_cost(
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return Solution(
            approach_id=self.get_metadata().id,
            task_id=task.id,
            seed=seed,
            changed_files=changed_files,
            generation_time_seconds=elapsed,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            api_calls=1,
            cost_usd=cost
        )

    def _build_prompt(self, task: Task) -> str:
        """Build minimal prompt"""
        return f"""You are a software engineer. Implement the following change:

Task: {task.name}

Specification:
{task.specification}

Constraints:
{chr(10).join(f"- {c}" for c in task.constraints)}

Key files to modify: {', '.join(task.key_files)}

Provide the modified code for each file that needs to change.
"""

    def _parse_code_changes(self, response: str) -> dict[str, str]:
        """Extract file changes from response"""
        # Parse code blocks with file paths
        # Format: ```language:path/to/file.ext
        #         code content
        #         ```
        pass

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost"""
        # Claude Sonnet 4.5 pricing (as of Oct 2025)
        input_cost = input_tokens / 1000 * 0.003
        output_cost = output_tokens / 1000 * 0.015
        return input_cost + output_cost

    def get_metadata(self) -> ApproachMetadata:
        return ApproachMetadata(
            id="simple-chat",
            name="Simple Chat",
            description="Single-turn chat with minimal prompting",
            version="1.0.0",
            model=self.model,
            provider="anthropic"
        )
```

#### 2. Elaborate Prompt DUT

```python
# src/codegen_bench/dut/elaborate_prompt.py
from codegen_bench.dut.simple_chat import SimpleChatDUT
from pathlib import Path

class ElaboratePromptDUT(SimpleChatDUT):
    """Enhanced system prompt with best practices"""

    def _build_prompt(self, task: Task) -> str:
        """Build elaborate prompt with context"""

        # Load system prompt template
        system_prompt = """You are an expert systems programmer with 15+ years experience.
You are tasked with modifying production code that will be maintained for years.

Critical principles:
1. **Maintainability**: Code must be crystal clear and well-documented
2. **Performance**: This is production software, efficiency matters
3. **Safety**: Memory safety, thread safety, comprehensive error handling
4. **Integration**: Match existing patterns and conventions exactly

Before writing code:
- Analyze the existing architecture thoroughly
- Identify potential gotchas and edge cases
- Plan the minimal set of changes needed
- Consider long-term maintenance burden

Your output must be production-ready, not a prototype."""

        # Analyze existing codebase
        codebase_context = self._analyze_codebase(task)

        # Build comprehensive prompt
        prompt = f"""{system_prompt}

## Task
{task.name}

## Specification
{task.specification}

## Constraints (MUST satisfy)
{chr(10).join(f"- {c}" for c in task.constraints)}

## Existing Codebase Context
{codebase_context}

## Known Gotchas
{chr(10).join(f"- {g}" for g in task.gotchas)}

## Key Files to Modify
{', '.join(task.key_files)}

Provide complete, production-ready code for all files that need modification.
"""
        return prompt

    def _analyze_codebase(self, task: Task) -> str:
        """Analyze existing code patterns"""
        # Read key files, extract patterns, conventions
        # This gives the DUT more context
        pass

    def get_metadata(self) -> ApproachMetadata:
        return ApproachMetadata(
            id="elaborate-prompt",
            name="Elaborate Prompt",
            description="Enhanced system prompt with architectural analysis",
            version="1.0.0",
            model=self.model,
            provider="anthropic"
        )
```

#### 3. Agentic Loop DUT

```python
# src/codegen_bench/dut/agentic_loop.py
from codegen_bench.dut.base import CodeGenerationApproach, ApproachMetadata
from typing import Literal

class AgenticLoopDUT(CodeGenerationApproach):
    """ReAct-style agentic loop with tool use"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.max_iterations = config.get("max_iterations", 5)
        self.tools = self._setup_tools()

    def solve(self, task: Task, seed: int) -> Solution:
        """Solve with agentic loop"""

        iteration = 0
        state = self._initialize_state(task)

        while iteration < self.max_iterations:
            # Agent decides next action
            action = self._plan_action(state, task)

            if action["type"] == "submit":
                # Agent believes solution is ready
                break

            # Execute action
            observation = self._execute_action(action, state)

            # Update state
            state = self._update_state(state, action, observation)

            iteration += 1

        # Extract final solution
        return self._extract_solution(state, task, seed, iteration)

    def _setup_tools(self) -> dict:
        """Setup available tools"""
        return {
            "read_file": self._tool_read_file,
            "write_file": self._tool_write_file,
            "run_tests": self._tool_run_tests,
            "grep_code": self._tool_grep_code,
            "analyze_architecture": self._tool_analyze_architecture
        }

    def _plan_action(self, state: dict, task: Task) -> dict:
        """Agent plans next action"""
        # Use Claude with tool use
        pass

    def _execute_action(self, action: dict, state: dict) -> str:
        """Execute tool and return observation"""
        tool_fn = self.tools[action["type"]]
        return tool_fn(**action["args"])

    def get_metadata(self) -> ApproachMetadata:
        return ApproachMetadata(
            id="agentic-loop",
            name="Agentic Loop",
            description="ReAct-style agent with tool use and iteration",
            version="1.0.0",
            model=self.config.get("model"),
            provider="anthropic"
        )
```

#### 4. Human Baseline DUT

```python
# src/codegen_bench/dut/human_baseline.py
from codegen_bench.dut.base import CodeGenerationApproach, ApproachMetadata
import subprocess
from pathlib import Path

class HumanBaselineDUT(CodeGenerationApproach):
    """Human-written solutions (reference baseline)"""

    def solve(self, task: Task, seed: int) -> Solution:
        """Load pre-existing human solution"""

        if not task.reference_solution_path:
            raise ValueError(f"Task {task.id} has no reference solution")

        # Load reference solution (e.g., a git diff or patch)
        solution_path = task.reference_solution_path

        if solution_path.suffix == ".diff":
            changed_files = self._parse_diff(solution_path)
        else:
            changed_files = self._load_direct(solution_path)

        return Solution(
            approach_id="human-baseline",
            task_id=task.id,
            seed=seed,
            changed_files=changed_files,
            generation_time_seconds=task.expected_human_time_minutes * 60,
            cost_usd=self._estimate_human_cost(task.expected_human_time_minutes)
        )

    def _parse_diff(self, diff_path: Path) -> dict[str, str]:
        """Parse unified diff format"""
        # Apply diff to get final files
        pass

    def _estimate_human_cost(self, minutes: int) -> float:
        """Estimate human programmer cost"""
        # Assume $150/hour for expert programmer
        return (minutes / 60) * 150

    def get_metadata(self) -> ApproachMetadata:
        return ApproachMetadata(
            id="human-baseline",
            name="Human Expert",
            description="Reference solutions by expert programmers",
            version="1.0.0"
        )
```

### DUT Registry

```python
# src/codegen_bench/dut/registry.py
from typing import Type, Dict
from codegen_bench.dut.base import CodeGenerationApproach

class DUTRegistry:
    """Registry of available DUTs"""

    _registry: Dict[str, Type[CodeGenerationApproach]] = {}

    @classmethod
    def register(cls, dut_class: Type[CodeGenerationApproach]):
        """Register a DUT implementation"""
        # Get ID from metadata (need dummy instance)
        dummy = dut_class(config={})
        dut_id = dummy.get_metadata().id
        cls._registry[dut_id] = dut_class
        return dut_class

    @classmethod
    def get(cls, dut_id: str) -> Type[CodeGenerationApproach]:
        """Get DUT class by ID"""
        if dut_id not in cls._registry:
            raise ValueError(f"Unknown DUT: {dut_id}")
        return cls._registry[dut_id]

    @classmethod
    def list_available(cls) -> list[str]:
        """List all registered DUTs"""
        return list(cls._registry.keys())

# Auto-register built-in DUTs
from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.dut.elaborate_prompt import ElaboratePromptDUT
from codegen_bench.dut.agentic_loop import AgenticLoopDUT
from codegen_bench.dut.human_baseline import HumanBaselineDUT

DUTRegistry.register(SimpleChatDUT)
DUTRegistry.register(ElaboratePromptDUT)
DUTRegistry.register(AgenticLoopDUT)
DUTRegistry.register(HumanBaselineDUT)
```

---

## CLI Design

### CLI Framework (Click)

```python
# src/codegen_bench/cli/main.py
import click
from pathlib import Path
from rich.console import Console

console = Console()

@click.group()
@click.option("--config", "-c", type=Path, help="Configuration file")
@click.option("--verbose", "-v", count=True, help="Verbose output (-vv for debug)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
@click.option("--cache-dir", type=Path, help="Cache directory")
@click.pass_context
def cli(ctx, config, verbose, quiet, cache_dir):
    """AI Code Generation Benchmark Suite"""

    # Setup context
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['cache_dir'] = cache_dir or Path.home() / ".cache" / "codegen-bench"

    # Setup logging
    import structlog
    log_level = "DEBUG" if verbose >= 2 else "INFO" if verbose == 1 else "WARNING"
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(log_level)
    )

# Import subcommands
from codegen_bench.cli import init, generate, judge, tournament, leaderboard, analyze

cli.add_command(init.init)
cli.add_command(generate.generate)
cli.add_command(judge.judge_cmd)
cli.add_command(tournament.tournament)
cli.add_command(leaderboard.leaderboard)
cli.add_command(analyze.analyze)
```

### Example: Tournament Command

```python
# src/codegen_bench/cli/tournament.py
import click
from pathlib import Path
from typing import Optional

@click.command()
@click.option("--duts", required=True, help="Comma-separated DUT names")
@click.option("--tasks", default="core", help="Task set or file")
@click.option("--arenas", help="Arenas to evaluate (default: all)")
@click.option("--tier", type=int, default=2, help="Evaluation tier (1-3)")
@click.option("--adaptive", is_flag=True, help="Enable adaptive designs")
@click.option("--samples", type=int, help="Samples per comparison")
@click.option("--output-dir", "-o", type=Path, help="Output directory")
@click.option("--rating-system", default="trueskill", help="Rating system")
@click.option("--correction", default="fdr_bh", help="Multiple testing correction")
@click.option("--preregistration", type=Path, help="Pre-registered analysis plan")
@click.pass_context
def tournament(ctx, duts, tasks, arenas, tier, adaptive, samples, output_dir,
               rating_system, correction, preregistration):
    """Run full tournament comparing multiple DUTs"""

    from codegen_bench.core.tournament import TournamentRunner
    from rich.progress import Progress

    # Parse DUTs
    dut_list = [d.strip() for d in duts.split(",")]

    # Setup tournament
    runner = TournamentRunner(
        duts=dut_list,
        tasks=tasks,
        arenas=arenas,
        tier=tier,
        adaptive=adaptive,
        samples=samples,
        cache_dir=ctx.obj['cache_dir'],
        output_dir=output_dir or Path("./results"),
        rating_system=rating_system,
        correction_method=correction,
        preregistration_file=preregistration
    )

    # Run with progress bar
    with Progress() as progress:
        results = runner.run(progress=progress)

    # Display results
    from codegen_bench.reporting.terminal import TerminalReporter
    reporter = TerminalReporter()
    reporter.display(results)

    click.echo(f"\nResults saved to: {runner.output_dir}")
```

---

## Configuration System

### Configuration Schema (Pydantic)

```python
# src/codegen_bench/config/schema.py
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional, Literal

class JudgeConfig(BaseModel):
    """Judge configuration"""
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3
    system_prompt_variant: int = 0

class GlobalConfig(BaseModel):
    """Global benchmark configuration"""

    # Paths
    cache_dir: Path = Field(default=Path.home() / ".cache" / "codegen-bench")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    parallel_workers: int = 8

    # API Keys (prefer env vars)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Defaults
    default_tier: int = 2
    default_samples: int = 20
    default_alpha: float = 0.05
    correction_method: Literal["fdr_bh", "fdr_by", "bonferroni", "holm"] = "fdr_bh"

    # Judges
    judges: list[JudgeConfig] = Field(default_factory=lambda: [
        JudgeConfig(model="claude-sonnet-4-20250514", system_prompt_variant=0),
        JudgeConfig(model="claude-sonnet-4-20250514", system_prompt_variant=1),
        JudgeConfig(model="claude-opus-4-20250514", temperature=0.2)
    ])

    # Cost tracking
    cost_per_1k_input_tokens: dict[str, float] = Field(default_factory=lambda: {
        "claude-sonnet-4-20250514": 0.003,
        "claude-opus-4-20250514": 0.015
    })

    cost_per_1k_output_tokens: dict[str, float] = Field(default_factory=lambda: {
        "claude-sonnet-4-20250514": 0.015,
        "claude-opus-4-20250514": 0.075
    })

    @classmethod
    def from_yaml(cls, path: Path) -> "GlobalConfig":
        """Load config from YAML file"""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

---

## Development Workflow

### shell.nix

```nix
# shell.nix
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python 3.12
    python312
    python312Packages.pip

    # uv for fast package management
    uv

    # Just for task running
    just

    # Development tools
    git
    gnumake

    # Optional: Language servers for development
    python312Packages.python-lsp-server

    # Optional: For building reference projects
    gcc
    clang
  ];

  shellHook = ''
    # Setup virtual environment
    if [ ! -d .venv ]; then
      uv venv .venv
    fi
    source .venv/bin/activate

    # Install dependencies with uv
    uv pip install -e ".[dev]"

    export CODEGEN_BENCH_DEV=1
  '';
}
```

### Justfile

```just
# justfile
# Task automation for codegen-bench

# Variables
python := ".venv/bin/python"
pytest := ".venv/bin/pytest"
ruff := ".venv/bin/ruff"
mypy := ".venv/bin/mypy"

# Default recipe (list available recipes)
default:
    @just --list

# Setup development environment
setup:
    uv venv .venv
    uv pip install -e ".[dev]"

# Run all tests
test:
    {{pytest}} tests/ -v --cov=src/codegen_bench --cov-report=html

# Run tests with coverage
test-cov:
    {{pytest}} tests/ --cov=src/codegen_bench --cov-report=term --cov-report=html

# Run specific test file
test-file FILE:
    {{pytest}} {{FILE}} -v

# Lint code
lint:
    {{ruff}} check src/ tests/

# Format code
fmt:
    {{ruff}} format src/ tests/

# Type check
typecheck:
    {{mypy}} src/codegen_bench

# Run all quality checks (lint + type + test)
check: lint typecheck test

# Clean build artifacts
clean:
    rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/
    find . -type d -name __pycache__ -exec rm -rf {} +

# Build package
build:
    {{python}} -m build

# Install package locally
install:
    uv pip install -e .

# Run calibration test
calibrate:
    {{python}} -m codegen_bench calibrate --ground-truth=tests/fixtures/ground_truth.yaml

# Run quick tournament (tier 1)
quick-tournament:
    {{python}} -m codegen_bench tournament \
        --duts=simple-chat,elaborate-prompt \
        --tier=1 \
        --output-dir=./results/quick

# Generate documentation
docs:
    cd docs && make html

# Start development server (if applicable)
serve:
    {{python}} -m codegen_bench serve --dev

# Release (tag and push)
release VERSION:
    git tag -a v{{VERSION}} -m "Release v{{VERSION}}"
    git push origin v{{VERSION}}
```

---

## Data Models (Complete Reference)

### Core Models Summary

```python
# Complete type hierarchy

# Core domain
Task            # Benchmark task definition
Solution        # Generated code solution
Arena           # Quality evaluation dimension
JudgeVote       # Single judge's vote
JudgmentResult  # Consensus from multiple judges

# DUT system
CodeGenerationApproach  # Abstract base for DUTs
ApproachMetadata        # DUT metadata

# Ratings
TrueSkillRating        # TrueSkill rating with uncertainty
Glicko2Rating          # Glicko-2 alternative
BayesianELO            # Simple Bayesian ELO

# Statistics
EffectSize             # Effect size with CI
SequentialBoundaries   # O'Brien-Fleming boundaries

# Configuration
GlobalConfig           # Global settings
JudgeConfig           # Judge configuration
ResourceLimits        # Execution limits
```

---

## Testing Strategy

### Test Structure

```python
# tests/unit/test_dut.py
import pytest
from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.core.task import Task

def test_simple_chat_solve(mock_task, mock_anthropic_client):
    """Test SimpleChatDUT generates valid solution"""

    dut = SimpleChatDUT(config={"api_key": "test-key", "model": "claude-test"})
    dut.client = mock_anthropic_client  # Inject mock

    solution = dut.solve(mock_task, seed=42)

    assert solution.approach_id == "simple-chat"
    assert solution.task_id == mock_task.id
    assert solution.seed == 42
    assert solution.api_calls == 1
    assert len(solution.changed_files) > 0

# tests/integration/test_tournament.py
def test_mini_tournament(tmp_path):
    """Test full tournament on toy dataset"""

    from codegen_bench.core.tournament import TournamentRunner

    runner = TournamentRunner(
        duts=["simple-chat", "elaborate-prompt"],
        tasks="tests/fixtures/toy_tasks",
        tier=1,
        output_dir=tmp_path / "results"
    )

    results = runner.run()

    assert len(results.rankings) == 2
    assert results.rankings[0].elo > 1000
```

### Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path
from codegen_bench.core.task import Task

@pytest.fixture
def mock_task():
    """Minimal task for testing"""
    return Task(
        id="test_001",
        name="Test Task",
        project="test-project",
        domain="testing",
        difficulty="easy",
        codebase_path=Path("tests/fixtures/codebases/simple"),
        specification="Add a hello world function"
    )

@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock Anthropic API client"""
    # Use pytest-mock to mock API responses
    pass
```

---

## Deployment & Distribution

### PyPI Package

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "codegen-bench"
version = "0.1.0"
description = "Statistically rigorous benchmark for AI code generation"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [
    { name = "Your Name", email = "you@example.com" }
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Testing",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
]

[project.scripts]
codegen-bench = "codegen_bench.cli.main:cli"

[project.urls]
Homepage = "https://github.com/yourusername/codegen-bench"
Documentation = "https://codegen-bench.readthedocs.io"
Repository = "https://github.com/yourusername/codegen-bench.git"
```

---

## Security Considerations

### API Key Management

```python
# Use environment variables, never commit keys
# Support multiple methods:

# 1. Environment variables
import os
api_key = os.getenv("ANTHROPIC_API_KEY")

# 2. .env file (via python-dotenv)
from dotenv import load_dotenv
load_dotenv()

# 3. Config file with env var substitution
# config.yaml:
#   anthropic_api_key: ${ANTHROPIC_API_KEY}
```

### Sandbox Security

```python
# Isolate DUT execution to prevent:
# - Excessive resource consumption
# - File system access outside designated areas
# - Network access (except approved APIs)

# Use multiprocessing + resource limits
# Consider Docker containers for stronger isolation
```

---

## Performance Optimization

### Caching Strategy

1. **Solution Cache**: Avoid regenerating identical solutions
2. **Result Cache**: Cache judge evaluations
3. **API Response Cache**: Cache API responses (with TTL)

### Parallelization

```python
# Parallelize independent operations:
# - Generate solutions for different tasks in parallel
# - Judge comparisons in parallel
# - Statistical calculations in parallel

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# IO-bound (API calls): ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(judge.evaluate, ...) for ...]

# CPU-bound (stats): ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(calculate_effect_size, ...) for ...]
```

---

## Extensibility Points

### Adding a New DUT

```python
# 1. Create new file: src/codegen_bench/dut/my_dut.py
# 2. Inherit from CodeGenerationApproach
# 3. Implement solve() and get_metadata()
# 4. Register in dut/__init__.py

from codegen_bench.dut.registry import DUTRegistry

@DUTRegistry.register
class MyCustomDUT(CodeGenerationApproach):
    def solve(self, task, seed):
        # Your implementation
        pass

    def get_metadata(self):
        return ApproachMetadata(id="my-custom", ...)
```

### Adding a New Arena

```python
# 1. Create prompt template: judge/prompts/my_arena.txt
# 2. Define arena in core/arena.py

MY_ARENA = Arena(
    name="my_arena",
    display_name="My Custom Arena",
    description="Evaluates X dimension",
    criteria=["...", "..."],
    prompt_template_path=Path("judge/prompts/my_arena.txt")
)
```

### Adding a New Rating System

```python
# 1. Create: src/codegen_bench/stats/ratings/my_rating.py
# 2. Implement standard interface: update(), get_rating(), get_uncertainty()
# 3. Register in stats/ratings/__init__.py
```

---

## Monitoring & Observability

### Structured Logging

```python
# Use structlog for structured logging
import structlog

logger = structlog.get_logger()

logger.info(
    "solution_generated",
    dut="simple-chat",
    task="task_001",
    cost_usd=0.05,
    tokens=1234
)

# Outputs JSON for easy parsing:
# {"event": "solution_generated", "dut": "simple-chat", ...}
```

### Cost Tracking

```python
# Track cumulative costs
class CostTracker:
    def __init__(self):
        self.total_cost = 0.0
        self.costs_by_dut = {}

    def record(self, dut_id: str, cost: float):
        self.total_cost += cost
        self.costs_by_dut[dut_id] = self.costs_by_dut.get(dut_id, 0.0) + cost

        # Warn if approaching budget
        if self.total_cost > 100:
            logger.warning("cost_threshold_exceeded", total=self.total_cost)
```

---

## Future Enhancements

### Phase 2+ Features

1. **Real-time Dashboard**: Web UI for live tournament monitoring
2. **Continuous Benchmarking**: GitHub Action for CI integration
3. **Task Extraction**: Auto-generate tasks from git history
4. **Multi-language Support**: Extend beyond C/Python
5. **Federated Evaluation**: Distribute computation across machines
6. **Human-in-the-Loop**: Optional human validation for close calls

---

**End of Design Document**

This design provides a complete blueprint for implementing the AI Code Generation Benchmark framework with Python 3.12, uv, Nix, and Just.
