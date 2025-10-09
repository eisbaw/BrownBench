# Product Requirements Document: AI Code Generation Benchmark Suite

**Version:** 0.1.0  
**Status:** Draft  
**Last Updated:** 2025-10-06

## Executive Summary

A rigorous, statistically-sound benchmark suite for evaluating AI-assisted code generation approaches in brownfield software projects. The tool uses AI-as-judge with multi-arena ELO ratings, emphasizing reproducibility, statistical significance, and cost-effectiveness analysis via Pareto frontier optimization.

**Core Innovation:** Treat code generation approaches as devices under test (DUTs) in an isolated, controlled environment with comprehensive statistical validation.

---

## 1. Vision & Goals

### Primary Goals

1. **Quantify the ROI of elaborate prompting vs. simple AI assistance**
   - Does complex scaffolding (multi-agent, chain-of-thought, etc.) produce measurably better code?
   - What is the cost-effectiveness (quality per dollar/token)?

2. **Create reproducible, objective quality metrics**
   - Remove human bottleneck from evaluation
   - Achieve >80% agreement with expert human judgment on calibration set
   - Provide confidence intervals and statistical significance

3. **Enable community comparison**
   - Standardized task suite from real brownfield projects
   - Leaderboard with Pareto frontier analysis
   - Open dataset for reproducibility

### Non-Goals

- ❌ Real-time code generation (this is a benchmark, not a dev tool)
- ❌ Training new models (evaluation only)
- ❌ IDE integration (standalone CLI tool)
- ❌ Supporting all programming languages initially (start with C, Python)
- ❌ Solving toy/synthetic problems (only real brownfield tasks)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                         │
│  codegen-bench [command] [options]                          │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────────┐     ┌─────────▼──────┐
│ Task Suite │     │ DUT Controller │
│ Manager    │     │ (Approach API) │
└───┬────────┘     └────────┬───────┘
    │                       │
    │              ┌────────▼─────────┐
    │              │ Solution Cache   │
    │              │ & Generator      │
    │              └────────┬─────────┘
    │                       │
┌───▼───────────────────────▼──────────────────┐
│         Judge Orchestrator                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Judge A  │  │ Judge B  │  │ Judge C  │  │
│  │ (Claude) │  │ (Claude) │  │ (Claude) │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└───────────────────┬──────────────────────────┘
                    │
        ┌───────────▼────────────┐
        │  Statistical Engine    │
        │  - ELO calculation     │
        │  - Significance tests  │
        │  - Confidence intervals│
        │  - Power analysis      │
        └───────────┬────────────┘
                    │
        ┌───────────▼────────────┐
        │  Reporting Engine      │
        │  - Leaderboards        │
        │  - Pareto frontiers    │
        │  - Detailed analytics  │
        └────────────────────────┘
```

---

## 3. Core Components

### 3.1 Task Suite Manager

**Responsibilities:**
- Load task definitions from brownfield projects
- Provide task context (existing codebase, requirements, gotchas)
- Validate task completion (tests, static analysis)

**Task Structure:**
```python
@dataclass
class Task:
    id: str                          # Unique identifier
    name: str                        # Human-readable name
    project: str                     # Source project (e.g., "ffmpeg")
    domain: str                      # "firmware", "signal_processing", etc.
    difficulty: Literal["easy", "medium", "hard"]
    
    # Context
    codebase_path: Path              # Reference codebase
    specification: str               # What needs to be done
    constraints: List[str]           # Must maintain X, must not break Y
    
    # Validation
    test_suite: Path                 # Tests that must pass
    reference_solution: Optional[Path]  # Expert solution (for metrics)
    
    # Metadata
    expected_human_time_minutes: int
    key_files: List[str]             # Files likely to change
    gotchas: List[str]               # Hidden complexity (for analysis)
```

**Task Selection Criteria:**
- Real commits from mature projects (>5 years old, >100K LOC)
- Non-trivial changes (5-15 files, multiple functions)
- Requires understanding existing architecture
- Has test suite or can be tested
- Spans different domains (systems, embedded, algorithms, etc.)

### 3.2 DUT (Device Under Test) Controller

**Responsibilities:**
- Abstract interface for different code generation approaches
- Isolate execution environment
- Track resource consumption (time, tokens, API calls)
- Ensure reproducibility

**DUT Interface:**
```python
class CodeGenerationApproach(ABC):
    """Abstract base for all approaches (DUTs)"""
    
    @abstractmethod
    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution for task
        
        Args:
            task: Task specification
            seed: Random seed for reproducibility
            
        Returns:
            Solution with code, tests, metadata
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> ApproachMetadata:
        """Return approach configuration"""
        pass

@dataclass
class Solution:
    approach_id: str
    task_id: str
    
    # Outputs
    changed_files: Dict[str, str]    # path -> content
    new_files: Dict[str, str]
    tests: Optional[Dict[str, str]]
    documentation: Optional[str]
    
    # Metrics
    generation_time_seconds: float
    total_tokens: int                 # Input + output
    prompt_tokens: int
    completion_tokens: int
    api_calls: int
    cost_usd: float
    
    # Intermediate state (for analysis)
    reasoning_trace: Optional[str]
    iterations: int                   # How many refinement loops
```

**Isolation Requirements:**
- Each DUT runs in clean environment
- No shared state between runs
- Deterministic seed control where possible
- Resource limits (timeout, max tokens)

**Built-in DUT Implementations:**
1. `HumanBaselineDUT` - Records human-written solutions
2. `SimpleChatDUT` - Single prompt to Claude/GPT
3. `ElaboratePromptDUT` - Custom system prompt + examples
4. `AgenticLoopDUT` - ReAct-style with tool use
5. `CustomDUT` - Load external implementation

### 3.3 Solution Cache & Generator

**Responsibilities:**
- Generate N solutions per (DUT, task) pair
- Cache solutions to disk (avoid regeneration)
- Handle variance analysis
- Enable reproducibility

**Design:**
```python
class SolutionCache:
    def get_or_generate(
        self,
        dut: CodeGenerationApproach,
        task: Task,
        n_solutions: int = 3,
        seeds: Optional[List[int]] = None
    ) -> List[Solution]:
        """Get cached solutions or generate new ones
        
        Args:
            dut: Device under test
            task: Task to solve
            n_solutions: Number of solutions to generate
            seeds: Fixed seeds for reproducibility
            
        Returns:
            List of solutions (from cache or freshly generated)
        """
        cache_key = f"{dut.id}_{task.id}"
        
        if cache_key in self.cache:
            return self.cache[cache_key][:n_solutions]
        
        solutions = []
        for i, seed in enumerate(seeds or range(n_solutions)):
            sol = dut.solve(task, seed)
            solutions.append(sol)
            self._save_to_disk(cache_key, i, sol)
        
        return solutions
```

**Cache Location:** `~/.cache/codegen-bench/solutions/`

**Benefits:**
- Separate solution variance from judge variance
- Enable offline analysis
- Reduce API costs
- Allow incremental experiments

### 3.4 Judge Orchestrator

**Responsibilities:**
- Coordinate multiple AI judges
- Implement consensus voting
- Handle rate limiting and retries
- Track judge reliability

**Architecture:**
```python
class JudgeOrchestrator:
    def __init__(self, judges: List[Judge]):
        self.judges = judges
        self.calibration_accuracy = {}
        
    def compare_solutions(
        self,
        solution_a: Solution,
        solution_b: Solution,
        arena: Arena,
        task: Task
    ) -> JudgmentResult:
        """Get consensus judgment from multiple judges"""
        
        votes = []
        for judge in self.judges:
            vote = judge.evaluate(solution_a, solution_b, arena, task)
            votes.append(vote)
        
        # Consensus logic
        consensus = self._compute_consensus(votes)
        
        return JudgmentResult(
            winner=consensus,
            votes=votes,
            agreement_rate=self._agreement_rate(votes),
            confidence=self._compute_confidence(votes)
        )

@dataclass
class Arena:
    """Quality dimension to evaluate"""
    name: str
    description: str
    judge_prompt: str
    criteria: List[str]
```

**Arenas (Quality Dimensions):**

1. **Maintainability Arena**
   - Code clarity, documentation
   - Adherence to conventions
   - Ease of future modification
   - Error handling robustness

2. **Architectural Integrity Arena**
   - Respects existing patterns
   - Minimizes coupling
   - Preserves abstractions
   - Fits mental model

3. **Surgical Precision Arena**
   - Minimal blast radius
   - Only changes what's needed
   - Avoids unnecessary refactoring
   - Low side effects

4. **Testability Arena**
   - Test coverage and quality
   - Tests are non-brittle
   - Edge cases covered
   - Meaningful assertions

5. **Performance Awareness Arena**
   - Hot path considerations
   - Algorithmic complexity
   - Memory efficiency
   - Cache-friendliness

6. **Safety & Correctness Arena**
   - Error handling completeness
   - Resource cleanup
   - Thread safety
   - Undefined behavior risks

**Judge Configuration:**
```python
@dataclass
class Judge:
    model: str                    # "claude-sonnet-4.5"
    temperature: float            # 0.3 for consistency
    system_prompt_variant: int    # Different prompt formulations
    
    def evaluate(
        self,
        sol_a: Solution,
        sol_b: Solution,
        arena: Arena,
        task: Task
    ) -> Vote:
        """Return: 'A', 'B', or 'TIE' with reasoning"""
        pass
```

**Consensus Algorithm:**
```python
def _compute_consensus(votes: List[Vote]) -> str:
    """
    3 judges: 
    - If 2+ agree: Use majority
    - If all different: Return 'TIE'
    
    5 judges:
    - If 3+ agree: Use majority
    - Otherwise: 'TIE'
    """
    pass
```

### 3.5 Statistical Engine

**Responsibilities:**
- Rating calculation with uncertainty (TrueSkill, Glicko-2, Bayesian ELO)
- Significance testing with effect sizes
- Multiple comparison correction (FDR preferred)
- Power analysis and sample size calculation
- Variance decomposition via mixed models

**Core Algorithms:**

#### Rating Systems (Three Options)

**TrueSkill (Default for multi-way comparisons)**
```python
from trueskill import Rating, rate, quality

class TrueSkillRating:
    """Microsoft TrueSkill with uncertainty quantification"""
    
    def __init__(self, mu=25.0, sigma=8.33):
        self.rating = Rating(mu, sigma)
    
    def update(self, *opponents, outcome: List[int]):
        """Update after match. outcome: ranks [0,1,2...] (0=best)"""
        ratings = [self.rating] + [o.rating for o in opponents]
        new_ratings = rate(ratings, ranks=outcome)
        self.rating = new_ratings[0]
    
    def conservative_estimate(self) -> float:
        """95% confidence lower bound"""
        return self.rating.mu - 2 * self.rating.sigma
    
    def match_quality(self, opponent) -> float:
        """Predict match quality (0-1, higher=more informative)"""
        return quality([[self.rating], [opponent.rating]])
```

**Glicko-2 (Public domain, simpler alternative)**
```python
class Glicko2Rating:
    """Glicko-2 with rating deviation and volatility"""
    
    def __init__(self, rating=1500, rd=350, vol=0.06):
        self.mu = rating       # Rating
        self.phi = rd          # Rating deviation (uncertainty)
        self.sigma = vol       # Volatility (consistency)
    
    def update(self, opponent_ratings, outcomes):
        """Update via Illinois algorithm"""
        # Implementation follows Glickman's paper
        # Available in glicko2 library
        pass
```

**Bayesian ELO (Fastest, simplest)**
```python
class BayesianELO:
    """ELO with Gaussian uncertainty"""
    
    def __init__(self, prior_mean=1500, prior_std=200):
        self.mean = prior_mean
        self.std = prior_std
    
    def update(self, opponent: 'BayesianELO', result: str):
        expected = 1 / (1 + 10**((opponent.mean - self.mean)/400))
        actual = {'win': 1.0, 'loss': 0.0, 'tie': 0.5}[result]
        
        # Kalman filter update
        K = self.std**2 / (self.std**2 + 200**2)
        self.mean += K * 32 * (actual - expected)
        self.std = sqrt((1 - K) * self.std**2)
```

#### Adaptive Trial Designs (Medical-Inspired)

**Multi-Arm Multi-Stage (MAMS)**
```python
class MAMSDesign:
    """Efficiently compare multiple approaches vs baseline"""
    
    def __init__(self, num_arms: int, control_id: str, 
                 alpha=0.05, power=0.80):
        self.num_arms = num_arms
        self.control_id = control_id
        self.alpha = alpha  # Dunnett-adjusted automatically
        
    def stage1_evaluation(self, cheap_metric_results: Dict) -> List[str]:
        """Select promising arms using cheap proxy metrics"""
        from scipy.stats import dunnett
        
        # Many-to-one comparison (more powerful than Bonferroni)
        treatment_results = [r for arm, r in results.items() 
                            if arm != self.control_id]
        control_results = results[self.control_id]
        
        # Dunnett test for multiple comparisons vs control
        significant_arms = dunnett(treatment_results, control_results)
        
        # Select top 2-3 performers
        return top_performers[:3]
```

**Group Sequential Design with Early Stopping**
```python
class GroupSequentialDesign:
    """O'Brien-Fleming boundaries for interim analyses"""
    
    def __init__(self, max_n=300, num_looks=3, alpha=0.05):
        self.checkpoints = np.linspace(0.33, 1.0, num_looks) * max_n
        self.alpha = alpha
        self.boundaries = self._compute_obrien_fleming_boundaries()
    
    def _compute_obrien_fleming_boundaries(self):
        """Conservative early stopping boundaries"""
        from scipy.stats import norm
        information_fractions = self.checkpoints / self.checkpoints[-1]
        # Alpha spending: α(t) = 2[1 - Φ(z_α/2 / √t)]
        return [self.alpha * (1 - norm.cdf(norm.ppf(1-self.alpha/2) / 
                np.sqrt(t))) for t in information_fractions]
    
    def check_interim(self, n: int, z_statistic: float) -> str:
        """Returns: 'continue', 'stop_efficacy', 'stop_futility'"""
        look_idx = np.searchsorted(self.checkpoints, n)
        
        if abs(z_statistic) > norm.ppf(1 - self.boundaries[look_idx]/2):
            return 'stop_efficacy'
        
        # Futility check (conditional power < 20%)
        if self._conditional_power(n, z_statistic) < 0.20:
            return 'stop_futility'
        
        return 'continue'
```

**Bayesian Adaptive Design**
```python
class BayesianAdaptiveDesign:
    """Continuous monitoring with posterior probabilities"""
    
    def __init__(self, prior_alpha=1, prior_beta=1, 
                 superiority_threshold=0.95):
        self.alpha_A = prior_alpha
        self.beta_A = prior_beta
        self.alpha_B = prior_alpha  
        self.beta_B = prior_beta
        self.threshold = superiority_threshold
    
    def update(self, successes_A, failures_A, successes_B, failures_B):
        """Update posteriors with new data"""
        self.alpha_A += successes_A
        self.beta_A += failures_A
        self.alpha_B += successes_B
        self.beta_B += failures_B
    
    def probability_B_superior(self, samples=10000) -> float:
        """P(θ_B > θ_A | data)"""
        theta_A = np.random.beta(self.alpha_A, self.beta_A, samples)
        theta_B = np.random.beta(self.alpha_B, self.beta_B, samples)
        return np.mean(theta_B > theta_A)
    
    def should_stop(self) -> Tuple[bool, str]:
        """Check stopping criteria"""
        p_superior = self.probability_B_superior()
        
        if p_superior > self.threshold:
            return True, "B superior"
        elif p_superior < (1 - self.threshold):
            return True, "A superior"
        
        return False, "continue"
```

#### Multiple Comparison Correction

**Default: Benjamini-Hochberg FDR Control**
```python
def correct_multiple_comparisons(
    p_values: List[float],
    method: str = 'fdr_bh',  # Default to FDR
    alpha: float = 0.05
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply multiple testing correction
    
    Args:
        p_values: Raw p-values from all comparisons
        method: 'fdr_bh' (default), 'fdr_by', 'bonferroni', 'holm', 'dunnett'
        alpha: Family-wise error rate or FDR level
        
    Returns:
        (rejected, p_adjusted): Boolean array and adjusted p-values
        
    Method selection guide:
    - 'fdr_bh': Benjamini-Hochberg FDR (DEFAULT - exploratory, many comparisons)
    - 'holm': Holm-Bonferroni step-down (confirmatory, few comparisons)
    - 'dunnett': Many-to-one vs baseline (MAMS design, 10-15% more powerful)
    - 'bonferroni': Most conservative (use only when FWER critical)
    """
    from statsmodels.stats.multitest import multipletests
    
    if method == 'dunnett':
        # Special handling for many-to-one comparisons
        from scipy.stats import dunnett
        return dunnett_correction(p_values, alpha)
    
    rejected, p_adjusted, _, _ = multipletests(
        p_values, 
        alpha=alpha, 
        method=method
    )
    
    return rejected, p_adjusted
```

**Dunnett's Test for MAMS**
```python
def dunnett_test(treatments: List[np.ndarray], 
                 control: np.ndarray,
                 alpha: float = 0.05) -> Dict:
    """
    Optimal test for multiple treatments vs single control
    
    10-15% more powerful than Bonferroni for many-to-one comparisons
    """
    from scipy.stats import dunnett
    
    result = dunnett(*treatments, control=control)
    
    return {
        'statistics': result.statistic,
        'pvalues': result.pvalue,
        'significant': result.pvalue < alpha,
        'power_gain_vs_bonferroni': 0.10  # Approximate
    }
```

#### Effect Size Calculation (MANDATORY)

**Critical principle**: Always report effect sizes with 95% CIs. Never report p-values alone.

```python
def calculate_effect_sizes(group_a: np.ndarray, 
                          group_b: np.ndarray,
                          paired: bool = False) -> Dict:
    """
    Calculate effect sizes with confidence intervals
    
    Returns all relevant metrics:
    - Hedges' g (bias-corrected Cohen's d)
    - 95% confidence interval
    - Common Language Effect Size (probability of superiority)
    - Interpretation relative to field norms
    """
    from scipy import stats
    import numpy as np
    
    n_a, n_b = len(group_a), len(group_b)
    
    if paired:
        # Within-subjects: use SD of differences
        differences = group_a - group_b
        d = np.mean(differences) / np.std(differences, ddof=1)
        metric = 'd_z'
    else:
        # Between-subjects: Hedges' g (corrected Cohen's d)
        pooled_sd = np.sqrt(((n_a-1)*np.var(group_a, ddof=1) + 
                             (n_b-1)*np.var(group_b, ddof=1)) / (n_a+n_b-2))
        d = (np.mean(group_a) - np.mean(group_b)) / pooled_sd
        
        # Hedges' correction for small samples
        correction = 1 - (3 / (4*(n_a + n_b) - 9))
        g = d * correction
        metric = 'g'
    
    # Bootstrap 95% CI
    from scipy.stats import bootstrap
    def effect_size_stat(a, b):
        return calculate_hedges_g(a, b)
    
    ci = bootstrap((group_a, group_b), effect_size_stat, 
                   n_resamples=10000, confidence_level=0.95)
    
    # Common Language Effect Size
    # Probability that random sample from A > random sample from B
    cles = np.mean([a > b for a in group_a for b in group_b])
    
    # Interpret relative to SE field norms (Kampenes et al. 2007)
    interpretation = interpret_effect_size(g, domain='software_engineering')
    
    return {
        'metric': metric,
        'value': g if not paired else d,
        'ci_lower': ci.confidence_interval.low,
        'ci_upper': ci.confidence_interval.high,
        'cles': cles,  # Probability of superiority
        'interpretation': interpretation,
        'sample_sizes': (n_a, n_b)
    }

def interpret_effect_size(g: float, domain: str = 'software_engineering') -> str:
    """
    Interpret effect size relative to FIELD-SPECIFIC norms
    
    Software Engineering norms (based on meta-analyses):
    Small: |g| ≈ 0.20
    Medium: |g| ≈ 0.50  
    Large: |g| ≈ 0.80
    
    Do NOT use generic Cohen benchmarks (0.2/0.5/0.8) without domain context!
    """
    abs_g = abs(g)
    
    if domain == 'software_engineering':
        if abs_g < 0.20: return 'negligible'
        elif abs_g < 0.50: return 'small'
        elif abs_g < 0.80: return 'medium'
        else: return 'large'
    
    # Add other domain norms as needed
    return 'unknown_domain'
```

**ANOVA Effect Sizes (Report BOTH)**
```python
def calculate_anova_effect_sizes(groups: List[np.ndarray]) -> Dict:
    """
    Calculate η² variants for ANOVA
    
    CRITICAL: Report BOTH η²_p and η²_G
    - η²_p (partial): For power analysis
    - η²_G (generalized): For meta-analysis (preferred)
    """
    from statsmodels.stats.anova import anova_lm
    
    # ... ANOVA calculation ...
    
    return {
        'eta_squared_partial': eta_p_squared,  # Report for power
        'eta_squared_generalized': eta_g_squared,  # Report for meta-analysis
        'ci_90': confidence_interval,  # Use 90% for effect sizes
        'interpretation': interpret_eta_squared(eta_g_squared)
    }
```

### 3.6 Reporting Engine

**Responsibilities:**
- Generate leaderboards with confidence intervals
- Produce Pareto frontier plots
- Export detailed analytics
- Create publication-ready figures

**Output Formats:**

1. **Terminal Output** (default)
2. **JSON** (machine-readable)
3. **HTML Report** (interactive)
4. **LaTeX Tables** (publication)
5. **CSV** (for custom analysis)

---

## 4. CLI Interface

### Philosophy
- Unix-style: composable, pipeable, follows conventions
- Sensible defaults, explicit overrides
- Follows `--flag=value` and `-f value` patterns
- Exit codes: 0 (success), 1 (error), 2 (invalid usage)

### Command Structure

```bash
codegen-bench [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### Global Options

```bash
--config FILE, -c FILE         # Configuration file (YAML)
--verbose, -v                  # Verbose output (can stack: -vv, -vvv)
--quiet, -q                    # Suppress non-error output
--log-file FILE                # Write logs to file
--cache-dir DIR                # Solution cache location
                              # Default: ~/.cache/codegen-bench
--no-cache                     # Disable solution caching
--seed INT                     # Global random seed (reproducibility)
--parallel INT, -j INT         # Parallel workers (default: CPU count)
```

### Commands

#### 4.1 `init` - Initialize Benchmark Suite

```bash
codegen-bench init [OPTIONS] OUTPUT_DIR

Options:
  --tasks TASK_SET            # Predefined task set: 'core', 'embedded', 'all'
  --download-projects         # Download reference projects
  --calibration-set           # Include calibration tasks (ground truth)
```

**Example:**
```bash
codegen-bench init --tasks=core --download-projects ./benchmark
```

Creates:
```
./benchmark/
├── tasks/
│   ├── task_001_ffmpeg_codec.yaml
│   ├── task_002_numpy_optimization.yaml
│   └── ...
├── projects/
│   ├── ffmpeg/
│   ├── numpy/
│   └── ...
├── config.yaml
└── README.md
```

#### 4.2 `generate` - Generate Solutions

```bash
codegen-bench generate [OPTIONS] TASK_ID [TASK_ID...]

Options:
  --dut NAME                  # Approach to use (required)
  --dut-config FILE           # DUT configuration file
  --output DIR, -o DIR        # Output directory for solutions
  --samples INT, -n INT       # Number of solutions per task (default: 3)
  --seeds INT[,INT...]        # Specific seeds (comma-separated)
  --timeout SECONDS           # Per-task timeout (default: 3600)
  --all-tasks                 # Generate for all tasks in suite
```

**Example:**
```bash
# Generate 5 solutions with specific approach
codegen-bench generate \
  --dut=simple-chat \
  --dut-config=configs/claude-sonnet.yaml \
  --samples=5 \
  --output=./solutions/ \
  task_001 task_002

# Generate for all tasks in parallel
codegen-bench generate \
  --dut=elaborate-prompt \
  --all-tasks \
  --parallel=8
```

#### 4.3 `judge` - Evaluate Solutions

```bash
codegen-bench judge [OPTIONS] SOLUTION_A SOLUTION_B

Options:
  --arena NAME                # Arena to evaluate (default: all)
  --judges INT                # Number of judges (default: 3)
  --judge-config FILE         # Judge configuration
  --samples INT, -n INT       # Repeat comparison N times (default: 20)
  --sequential-test           # Use sequential testing (early stopping)
  --alpha FLOAT               # Significance level (default: 0.05)
  --output FILE, -o FILE      # Save results to file
```

**Example:**
```bash
# Compare two solutions in all arenas
codegen-bench judge \
  solutions/simple-chat/task_001_0.json \
  solutions/elaborate/task_001_0.json \
  --samples=30

# Compare in specific arena with sequential testing
codegen-bench judge \
  --arena=maintainability \
  --sequential-test \
  --alpha=0.01 \
  sol_a.json sol_b.json
```

#### 4.4 `tournament` - Run Full Tournament

```bash
codegen-bench tournament [OPTIONS]

Options:
  --duts NAME[,NAME...]       # Approaches to compare (required)
  --tasks TASK_SET            # Task set: 'core', 'embedded', 'all', or file
  --arenas ARENA[,ARENA...]   # Arenas to evaluate (default: all)
  --tier INT                  # Evaluation tier (1=quick, 2=main, 3=deep)
                              # Controls sample sizes
  --adaptive                  # Enable adaptive designs (MAMS + sequential)
  --samples INT               # Override samples per comparison
  --sequential-test           # Enable sequential testing with early stopping
  --output-dir DIR, -o DIR    # Results directory (default: ./results)
  --report-format FORMAT      # Output format: 'terminal', 'html', 'json', 'all'
  --alpha FLOAT               # Significance level (default: 0.05)
  --correction METHOD         # Multiple testing: 'fdr_bh' (default), 'holm', 'dunnett'
  --rating-system SYSTEM      # 'trueskill' (default), 'glicko2', 'bayesian-elo'
  --effect-sizes              # Always compute (MANDATORY, always enabled)
  --preregistration FILE      # Load preregistered analysis plan
```

**Adaptive Design Options:**

When `--adaptive` flag is used, tournament runs in three phases following medical trial methodology:

**Phase 1: MAMS Screening (Multi-Arm Multi-Stage)**
- Evaluate all DUTs with cheap proxy metrics
- Use Dunnett's test for many-to-one comparisons vs baseline
- Select top 2-3 performers
- Cost: ~$5K, Duration: 1 week

**Phase 2: Sequential Testing**
- Full evaluation of selected DUTs
- Group sequential design with O'Brien-Fleming boundaries
- Interim analyses at 33%, 67%, 100%
- Early stopping if efficacy/futility detected
- Cost: ~$7K expected (vs $10K without early stopping)
- Duration: 2-3 weeks

**Phase 3: Non-Inferiority Testing** (optional)
- Test if cheaper DUT is non-inferior to expensive baseline
- Requires `--baseline` and `--margin` options
- Cost: ~$3K, Duration: 1 week

**Total expected cost with --adaptive: ~$15K vs $25K+ naive**
**Power maintained: ≥0.80, FWER: ≤0.05**

**Tier Presets:**
- Tier 1: 5 tasks × 10 samples = quick screen (~$50)
- Tier 2: 10 tasks × 20 samples = main eval (~$300)
- Tier 3: 20 tasks × 50 samples = deep dive (~$1,500)

**Example:**
```bash
# Quick comparison of 3 approaches
codegen-bench tournament \
  --duts=simple-chat,elaborate,multi-agent \
  --tier=1 \
  --output-dir=./results/quick-test

# Full adaptive tournament (RECOMMENDED)
codegen-bench tournament \
  --duts=human-baseline,simple-chat,elaborate,agentic,swarm \
  --adaptive \
  --tier=2 \
  --tasks=./my-tasks.yaml \
  --correction=fdr_bh \
  --rating-system=trueskill \
  --report-format=all \
  --preregistration=./preregistered-plan.yaml \
  --output-dir=./results/main-eval

# Non-inferiority test
codegen-bench tournament \
  --duts=gpt-3.5-turbo,gpt-4 \
  --baseline=gpt-4 \
  --margin=0.05 \
  --test=non-inferiority \
  --tier=2
```

#### 4.5 `leaderboard` - Display Rankings

```bash
codegen-bench leaderboard [OPTIONS] RESULTS_DIR

Options:
  --arena NAME                # Show specific arena (default: all)
  --sort-by METRIC            # Sort by: 'elo', 'efficiency', 'cost'
  --confidence FLOAT          # CI confidence level (default: 0.95)
  --format FORMAT             # Output: 'terminal', 'json', 'csv', 'latex'
  --pareto                    # Show Pareto frontier plot
  --significance-matrix       # Show pairwise significance matrix
```

**Example:**
```bash
# Display overall leaderboard
codegen-bench leaderboard ./results/main-eval

# Show maintainability arena with Pareto plot
codegen-bench leaderboard \
  --arena=maintainability \
  --pareto \
  ./results/main-eval

# Export to LaTeX for paper
codegen-bench leaderboard \
  --format=latex \
  --confidence=0.99 \
  ./results > table.tex
```

#### 4.6 `analyze` - Statistical Analysis

```bash
codegen-bench analyze [OPTIONS] RESULTS_DIR

Options:
  --variance-decomposition    # Show variance components
  --power-analysis            # Compute statistical power achieved
  --judge-reliability         # Analyze judge agreement rates
  --effect-sizes              # Report effect sizes (Cohen's h)
  --export-data FILE          # Export raw data for custom analysis
  --plot-elo-history          # Plot ELO evolution over tournament
```

**Example:**
```bash
# Full statistical report
codegen-bench analyze \
  --variance-decomposition \
  --power-analysis \
  --judge-reliability \
  --effect-sizes \
  ./results/main-eval

# Export data for R/Python analysis
codegen-bench analyze \
  --export-data=./data.csv \
  ./results
```

#### 4.7 `calibrate` - Judge Calibration

```bash
codegen-bench calibrate [OPTIONS]

Options:
  --ground-truth FILE         # File with expert-labeled pairs
  --judges INT                # Number of judges to test (default: 3)
  --judge-config FILE         # Judge configuration to test
  --arena NAME                # Arena to calibrate (default: all)
  --min-agreement FLOAT       # Minimum acceptable agreement (default: 0.80)
  --output FILE               # Save calibration report
```

**Example:**
```bash
# Calibrate judges against ground truth
codegen-bench calibrate \
  --ground-truth=./calibration-set.yaml \
  --min-agreement=0.85 \
  --output=calibration-report.json
```

#### 4.7 `calibrate` - Judge Calibration

```bash
codegen-bench calibrate [OPTIONS]

Options:
  --ground-truth FILE         # File with expert-labeled pairs
  --judges INT                # Number of judges to test (default: 3)
  --judge-config FILE         # Judge configuration to test
  --arena NAME                # Arena to calibrate (default: all)
  --min-agreement FLOAT       # Minimum acceptable agreement (default: 0.80)
  --output FILE               # Save calibration report
```

**Example:**
```bash
# Calibrate judges against ground truth
codegen-bench calibrate \
  --ground-truth=./calibration-set.yaml \
  --min-agreement=0.85 \
  --output=calibration-report.json
```

#### 4.8 `preregister` - Pre-register Analysis Plan

```bash
codegen-bench preregister [OPTIONS] OUTPUT_FILE

Options:
  --duts NAME[,NAME...]       # Approaches to compare
  --hypotheses FILE           # Hypotheses file
  --primary-outcome NAME      # Primary outcome metric
  --secondary-outcomes LIST   # Secondary metrics
  --sample-size INT           # Planned sample size
  --alpha FLOAT               # Significance level
  --correction METHOD         # Multiple testing correction
  --power FLOAT               # Target statistical power
  --stopping-rules FILE       # Early stopping criteria
  --exclusion-criteria FILE   # Data exclusion rules
  --timestamp                 # Add timestamp (default: true)
  --osf                       # Upload to OSF (requires auth)
```

**Pre-registration includes:**
- Research question and hypotheses (directional when possible)
- Planned sample size with power justification
- Stopping rules (fixed, sequential, or Bayesian adaptive)
- Exclusion criteria applied before seeing results
- Primary and secondary outcomes (prioritized)
- Statistical tests with multiple comparison correction
- Effect size calculations planned
- Inference criteria (what constitutes "success")

**Example:**
```bash
# Create pre-registration document
codegen-bench preregister \
  --duts=gpt-4,claude-opus,gemini-pro \
  --hypotheses=hypotheses.yaml \
  --primary-outcome=correctness \
  --secondary-outcomes=efficiency,security,maintainability \
  --sample-size=300 \
  --alpha=0.05 \
  --correction=fdr_bh \
  --power=0.80 \
  --stopping-rules=sequential.yaml \
  --timestamp \
  --osf \
  preregistration.yaml

# Use pre-registered plan in tournament
codegen-bench tournament \
  --preregistration=preregistration.yaml \
  --verify-adherence
```

**OSF Integration:**
Pre-registration automatically timestamps and can upload to Open Science Framework (OSF) for public pre-commitment, preventing HARKing (Hypothesizing After Results Known) and p-hacking.

#### 4.9 `validate` - Validate Solutions

```bash
codegen-bench validate [OPTIONS] SOLUTION_FILE [SOLUTION_FILE...]

Options:
  --compile                   # Check if solution compiles
  --run-tests                 # Run test suite
  --static-analysis           # Run static analyzers
  --all                       # Run all validation checks
  --fail-fast                 # Stop on first failure
  --report FILE               # Save validation report
```

**Example:**
```bash
# Validate all solutions
codegen-bench validate --all solutions/**/*.json

# Quick compile check
codegen-bench validate --compile --fail-fast solutions/task_001_*.json
```

---

## 5. Configuration Files

### 5.1 Global Config (`config.yaml`)

```yaml
# Global configuration
cache_dir: ~/.cache/codegen-bench
log_level: INFO
parallel_workers: 8

# API keys (or use environment variables)
anthropic_api_key: ${ANTHROPIC_API_KEY}
openai_api_key: ${OPENAI_API_KEY}

# Default settings
default_tier: 2
default_samples: 20
default_alpha: 0.05
correction_method: fdr_bh

# Judge configuration
judges:
  - model: claude-sonnet-4.5
    temperature: 0.3
    system_prompt_variant: 0
  - model: claude-sonnet-4.5
    temperature: 0.3
    system_prompt_variant: 1
  - model: claude-opus-4.1
    temperature: 0.2
    system_prompt_variant: 0

# Cost tracking
cost_per_1k_input_tokens:
  claude-sonnet-4.5: 0.003
  claude-opus-4.1: 0.015

cost_per_1k_output_tokens:
  claude-sonnet-4.5: 0.015
  claude-opus-4.1: 0.075
```

### 5.2 Task Definition (`task.yaml`)

```yaml
id: task_001
name: "Add deadline scheduling to audio pipeline"
project: audio-pipeline
domain: signal_processing
difficulty: hard

specification: |
  Add deadline-aware scheduling to the real-time audio processing pipeline.
  Requirements:
  - Maintain zero-copy semantics
  - Support per-buffer deadlines
  - Graceful degradation on deadline miss
  - No impact on fast path latency

codebase:
  path: ./projects/audio-pipeline
  entry_points:
    - src/scheduler.c
    - src/pipeline.c
  key_files:
    - src/scheduler.h
    - src/buffer.c
    - include/pipeline.h

constraints:
  - "Must maintain ABI compatibility"
  - "No dynamic allocation in fast path"
  - "Thread-safe without locks where possible"

validation:
  compile: make -C projects/audio-pipeline
  tests: make -C projects/audio-pipeline test
  performance_regression: ./bench.sh --max-latency=10ms

expected_human_time_minutes: 240
estimated_tokens: 8000

gotchas:
  - "Buffer pool is shared between contexts"
  - "Existing priority queue has O(log n) insertion"
  - "Scheduler runs in separate thread, synchronization needed"

reference_solution:
  path: ./reference-solutions/task_001.diff
  author: expert_programmer_001
  metrics:
    lines_changed: 156
    files_changed: 4
    cyclomatic_complexity_delta: 8
```

### 5.3 DUT Configuration (`dut-config.yaml`)

```yaml
id: elaborate-prompt
name: "Claude with Elaborate System Prompt"
type: chat-based
model: claude-sonnet-4.5

system_prompt: |
  You are an expert systems programmer tasked with modifying a 
  production codebase. Focus on:
  
  1. Maintainability: Code that will be maintained for years
  2. Performance: This is real-time software
  3. Safety: Memory safety, thread safety, error handling
  4. Integration: Match existing conventions and patterns
  
  Before writing code:
  - Analyze the existing architecture
  - Identify potential gotchas
  - Plan minimal changes
  
  Your output should be production-ready.

temperature: 0.3
max_tokens: 8000

preprocessing:
  - analyze_existing_code
  - identify_patterns
  - extract_conventions

postprocessing:
  - validate_syntax
  - run_formatter
  - generate_tests
```

#### Variance Decomposition via Mixed Models

```python
def decompose_variance_mixed_model(results: pd.DataFrame) -> Dict:
    """
    Linear Mixed Model variance decomposition
    
    Explicitly models hierarchical structure:
    - Fixed effects: Approach (population parameters)
    - Random effects: Task, Arena, Judge (group-level variation)
    
    Returns ICC (Intraclass Correlation) for each random effect
    """
    import statsmodels.formula.api as smf
    from statsmodels.regression.mixed_linear_model import MixedLM
    
    # Fit mixed model
    # ELO ~ Approach + (1|Task) + (1|Arena) + (1|Judge)
    model = MixedLM.from_formula(
        'elo ~ approach',
        groups=results['task'],  # Primary grouping
        re_formula='1',
        data=results
    )
    fitted = model.fit()
    
    # Extract variance components
    sigma2_between = fitted.cov_re.iloc[0, 0]  # Random effect variance
    sigma2_within = fitted.scale  # Residual variance
    
    # Intraclass Correlation Coefficient
    icc = sigma2_between / (sigma2_between + sigma2_within)
    
    # Interpretation: ICC
    # <0.5: Poor reliability
    # 0.5-0.75: Moderate
    # 0.75-0.9: Good
    # ≥0.9: Excellent
    
    # Marginal R² (fixed effects only)
    # Conditional R² (fixed + random)
    r2_marginal = calculate_r2_marginal(fitted)
    r2_conditional = calculate_r2_conditional(fitted)
    
    return {
        'icc': icc,
        'interpretation': interpret_icc(icc),
        'variance_between': sigma2_between,
        'variance_within': sigma2_within,
        'r2_marginal': r2_marginal,  # Fixed effects
        'r2_conditional': r2_conditional,  # Fixed + random
        'aic': fitted.aic,
        'bic': fitted.bic
    }
```

#### Pareto Frontier Analysis (pymoo)

```python
def generate_pareto_frontier(
    approaches: List[str],
    objectives: Dict[str, List[float]]  # quality, cost, speed
) -> Dict:
    """
    Generate Pareto frontier using NSGA-II
    
    Uses pymoo framework for multi-objective optimization
    """
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
    from pymoo.indicators.hv import HV
    import numpy as np
    
    class BenchmarkProblem(Problem):
        def __init__(self, data):
            self.data = data
            super().__init__(
                n_var=len(approaches),
                n_obj=3,  # quality, cost, speed
                n_constr=1,  # quality >= threshold
                xl=np.zeros(len(approaches)),
                xu=np.ones(len(approaches))
            )
        
        def _evaluate(self, x, out):
            # Evaluate objectives for configuration x
            quality = -self.calculate_quality(x)  # Negative (minimize)
            cost = self.calculate_cost(x)
            speed = self.calculate_speed(x)
            
            out["F"] = [quality, cost, speed]
            out["G"] = [0.7 - (-quality)]  # Constraint: quality >= 0.7
    
    problem = BenchmarkProblem(objectives)
    algorithm = NSGA2(pop_size=100)
    
    res = minimize(
        problem,
        algorithm,
        ('n_gen', 50),
        seed=42,
        verbose=False
    )
    
    # Extract Pareto front
    pareto_front = res.F
    pareto_configs = res.X
    
    # Calculate hypervolume (quality metric)
    ref_point = np.array([0, 1000, 1000])  # Worst possible
    hv = HV(ref_point=ref_point)
    hypervolume = hv(pareto_front)
    
    # Identify dominated solutions
    is_dominated = np.ones(len(objectives['quality']), dtype=bool)
    is_dominated[res.opt] = False
    
    return {
        'pareto_front': pareto_front,
        'pareto_configs': pareto_configs,
        'hypervolume': hypervolume,
        'dominated_solutions': is_dominated,
        'reference_point': ref_point
    }

def visualize_pareto_frontier(pareto_data: Dict, 
                              objectives: Dict) -> None:
    """Create interactive Pareto frontier visualization"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=('Quality vs Cost', 'Quality vs Speed', 'Cost vs Speed')
    )
    
    # Add dominated solutions
    fig.add_trace(
        go.Scatter(
            x=objectives['cost'],
            y=objectives['quality'],
            mode='markers',
            marker=dict(color='lightgray', size=8),
            name='Dominated',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Add Pareto front
    pareto_front = pareto_data['pareto_front']
    fig.add_trace(
        go.Scatter(
            x=pareto_front[:, 1],  # cost
            y=-pareto_front[:, 0],  # quality (negate back)
            mode='markers+lines',
            marker=dict(color='red', size=12),
            name='Pareto Optimal',
            showlegend=True
        ),
        row=1, col=1
    )
    
    fig.update_xaxes(title_text="Cost ($)", row=1, col=1)
    fig.update_yaxes(title_text="Quality Score", row=1, col=1)
    
    return fig
```

### 6.1 Terminal Output (Default)

```
┌─────────────────────────────────────────────────────────────┐
│            CODEGEN-BENCH TOURNAMENT RESULTS                  │
│                                                               │
│ Tasks: 10 | Arenas: 6 | Samples/Pairing: 20                 │
│ Correction: FDR (Benjamini-Hochberg) | α = 0.05             │
│ Total Comparisons: 7,234 | Total Cost: $289.36              │
└─────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
                     OVERALL ELO RANKINGS                       
═══════════════════════════════════════════════════════════════

Rank  Approach                 ELO      95% CI         Sig vs #1
────  ─────────────────────  ──────  ─────────────  ─────────────
  1   Human Expert            1650   [1610, 1690]         -
  2   Elaborate Prompt        1580   [1535, 1625]    p = 0.012 *
  3   Multi-Agent Swarm       1520   [1465, 1575]    p < 0.001 ***
  4   Simple Chat             1515   [1470, 1560]    p < 0.001 ***
  5   Autonomous AI           1420   [1375, 1465]    p < 0.001 ***

* p < 0.05  ** p < 0.01  *** p < 0.001

═══════════════════════════════════════════════════════════════
                      PER-ARENA BREAKDOWN                       
═══════════════════════════════════════════════════════════════

Approach           │ Maint │ Arch │ Surg │ Test │ Perf │ Safe │ Avg
─────────────────  │ ───── │ ──── │ ──── │ ──── │ ──── │ ──── │ ────
Human Expert       │  1680 │ 1640 │ 1620 │ 1710 │ 1650 │ 1690 │ 1665
Elaborate Prompt   │  1590 │ 1570 │ 1550 │ 1620 │ 1580 │ 1570 │ 1580
Multi-Agent Swarm  │  1480 │ 1520 │ 1440 │ 1600 │ 1530 │ 1510 │ 1513
Simple Chat        │  1510 │ 1480 │ 1520 │ 1490 │ 1470 │ 1500 │ 1495
Autonomous AI      │  1390 │ 1420 │ 1460 │ 1380 │ 1450 │ 1400 │ 1417

═══════════════════════════════════════════════════════════════
                 COST-EFFECTIVENESS ANALYSIS                    
═══════════════════════════════════════════════════════════════

Approach              Quality    Cost      Efficiency   Time
                      (ELO)      (USD)     (ELO/$)      (min)
──────────────────  ─────────  ────────  ───────────  ───────
Human Expert          1650      $150.00       11.0      180
Elaborate Prompt      1580        $0.75    2,107.0       12
Simple Chat           1515        $0.24    6,313.0        8
Multi-Agent Swarm     1520        $7.50      203.0       45
Autonomous AI         1420        $1.50      947.0       15

═══════════════════════════════════════════════════════════════
                 COST-EFFECTIVENESS ANALYSIS (ICER)                  
═══════════════════════════════════════════════════════════════

Approach              Quality    Cost      ICER         Decision
                      (QAEU)     (USD)     ($/QAEU)     
──────────────────  ─────────  ────────  ───────────  ─────────────
Human Expert          0.825      $150.00       -        Reference
Elaborate Prompt      0.790        $0.75    -$4,271    Dominated by Simple
Simple Chat           0.758        $0.24    -$1,940    Cost-effective
Multi-Agent Swarm     0.760        $7.50    $1,086     High cost, low gain
Autonomous AI         0.710        $1.50       -        Dominated

QAEU = Quality-Adjusted Evaluation Unit (quality × utility_weight)
ICER = Incremental Cost-Effectiveness Ratio = ΔCost / ΔQAEU

Cost-Effectiveness Plane:
    Quality
       ↑
  0.85 │                Expert ●
  0.80 │          Elaborate ●
  0.75 │     Simple ●                 
  0.70 │                    Swarm ●
  0.65 │         Autonomous ●
       └──────────────────────────────→ Cost ($)
          0    1    5   10   50  100  150

Quadrant Analysis:
  ✓ SE (Simple): ADOPT - Better quality, lower cost than Autonomous
  ✓ NE (Expert): EVALUATE - Best quality, highest cost (ICER: Reference)
  ✗ NW (None): DOMINATED - Reject immediately
  ? SW (Autonomous): CONSIDER IF - Willing to accept lower quality for savings

Willingness-to-Pay Threshold: $100 per QAEU
  → Simple Chat: Most cost-effective below threshold
  → Expert: Only justified if WTP > $4,271/QAEU

═══════════════════════════════════════════════════════════════
                    PARETO FRONTIER                             
═══════════════════════════════════════════════════════════════

Quality
   ↑
1700│                        Expert ●
1600│                   Elaborate ●
1500│          Simple ●    
1400│                         Swarm ●
1300│              Autonomous ●
1200│
    └─────────────────────────────────────→ Cost ($)
       0      1      5     10    50   100   150

Pareto Optimal: Expert, Elaborate, Simple

═══════════════════════════════════════════════════════════════
                  STATISTICAL SUMMARY                           
═══════════════════════════════════════════════════════════════

Effect Sizes (with 95% CIs):
  Expert vs Simple:     Hedges' g = 0.92 [0.65, 1.19] (large)
  Expert vs Elaborate:  Hedges' g = 0.45 [0.18, 0.72] (medium)
  Elaborate vs Simple:  Hedges' g = 0.47 [0.20, 0.74] (medium)

  Interpretation: Software Engineering field norms
  CLES (Expert vs Simple): 82% probability Expert > Simple

Variance Decomposition (Mixed Model):
  Between Approaches:  42.3% ████████████  (Signal)
  Between Tasks:       28.1% ████████      (Task difficulty)
  Between Arenas:      18.5% █████         (Dimension variance)
  Residual (noise):    11.1% ███           (Judge + measurement)

  ICC (Intraclass Correlation): 0.73 (Good reliability)
  Marginal R² (fixed effects):  0.62
  Conditional R² (fixed+random): 0.89

Power Analysis:
  Minimum Detectable Effect: Hedges' g = 0.42 (medium)
  Achieved Power: 0.87 (target: 0.80) ✓
  Observed win rate difference: 15% (detectable at 0.80 power)
  
  Sensitivity: Can detect ELO differences ≥95 points

Multiple Comparison Correction:
  Method: Benjamini-Hochberg FDR (q < 0.05)
  Comparisons: 10 pairwise × 6 arenas = 60 tests
  Significant after correction: 42 (70%)
  Estimated proportion of true nulls (π₀): 0.15
  
  Alternative (if used): Dunnett's test for MAMS
  Power gain vs Bonferroni: ~12%

Judge Reliability:
  Inter-judge Agreement: 87.3% (target: >85%) ✓
  Fleiss' Kappa: 0.71 (substantial agreement)
  Consistency (test-retest): 89.1%
  Calibration Accuracy: 86.2% vs expert ground truth ✓
  
  Position bias detected: Yes (2.3% effect)
  Length bias detected: Yes (4.1% effect) - controlled via regression
  
  Panel composition:
    - GPT-4 (security): 82% agreement
    - Claude Sonnet (quality): 84% agreement  
    - Claude Sonnet v2 (quality): 85% agreement
    - Consensus (3/5): 87% agreement ✓

Adaptive Design Performance:
  MAMS Phase 1: Eliminated 3/5 approaches ($5K spent)
  Sequential Phase 2: Early stopping at 67% checkpoint ($7K vs $10K budgeted)
  Total cost: $12K vs $25K naive approach (52% savings)
  
  O'Brien-Fleming boundary crossed at: n=200 (efficacy)
  Statistical guarantees maintained: FWER ≤ 0.05, Power ≥ 0.80

Pre-registration:
  ✓ Hypotheses pre-registered (OSF: osf.io/abc123)
  ✓ Analysis plan followed (1 minor deviation documented)
  ✓ Primary outcome: Correctness (as planned)
  ✓ Sample size justified via power analysis

Open Science:
  ✓ Data: github.com/user/codegen-bench-data
  ✓ Code: github.com/user/codegen-bench  
  ✓ Materials: osf.io/abc123
  ✓ Preprint: arxiv.org/abs/2025.xxxxx

For detailed analysis: codegen-bench analyze ./results
```

### 6.2 JSON Output

```json
{
  "meta": {
    "version": "0.1.0",
    "timestamp": "2025-10-06T15:23:45Z",
    "config": {
      "tasks": 10,
      "arenas": 6,
      "samples_per_pairing": 20,
      "alpha": 0.05,
      "correction": "fdr_bh"
    },
    "total_comparisons": 7234,
    "total_cost_usd": 289.36
  },
  
  "rankings": [
    {
      "rank": 1,
      "approach": "Human Expert",
      "elo": {
        "mean": 1650,
        "std": 20,
        "ci_lower": 1610,
        "ci_upper": 1690,
        "confidence": 0.95
      },
      "per_arena": {
        "maintainability": 1680,
        "architecture": 1640,
        "surgical": 1620,
        "testability": 1710,
        "performance": 1650,
        "safety": 1690
      },
      "cost_metrics": {
        "cost_usd": 150.0,
        "time_minutes": 180,
        "tokens": 1000,
        "efficiency_elo_per_dollar": 11.0
      }
    }
  ],
  
  "pairwise_comparisons": [
    {
      "approach_a": "Human Expert",
      "approach_b": "Elaborate Prompt",
      "arena": "maintainability",
      "samples": 42,
      "wins_a": 28,
      "wins_b": 8,
      "ties": 6,
      "p_value": 0.0003,
      "p_adjusted": 0.018,
      "significant": true,
      "effect_size_cohens_h": 0.64
    }
  ],
  
  "statistical_analysis": {
    "variance_decomposition": {
      "total": 18420,
      "approach": 7790,
      "task": 5174,
      "arena": 3408,
      "residual": 2048
    },
    "power_analysis": {
      "achieved_power": 0.87,
      "minimum_detectable_effect_elo": 95
    },
    "judge_reliability": {
      "agreement_rate": 0.783,
      "consistency": 0.891,
      "calibration_accuracy": 0.842
    }
  }
}
```

### 6.3 HTML Report

Interactive dashboard with:
- Sortable leaderboard tables
- Hoverable Pareto frontier plots
- Expandable per-arena breakdowns
- Significance matrix heatmaps
- ELO history timeline charts
- Cost breakdown pie charts

### 6.4 LaTeX Tables

```latex
\begin{table}[h]
\centering
\caption{Overall ELO Rankings with 95\% Confidence Intervals}
\begin{tabular}{rlrrr}
\toprule
Rank & Approach & ELO & 95\% CI & Sig. vs \#1 \\
\midrule
1 & Human Expert & 1650 & [1610, 1690] & - \\
2 & Elaborate Prompt & 1580 & [1535, 1625] & $p = 0.012^*$ \\
3 & Multi-Agent Swarm & 1520 & [1465, 1575] & $p < 0.001^{***}$ \\
4 & Simple Chat & 1515 & [1470, 1560] & $p < 0.001^{***}$ \\
5 & Autonomous AI & 1420 & [1375, 1465] & $p < 0.001^{***}$ \\
\bottomrule
\end{tabular}
\end{table}
```

---

## 7. Statistical Rigor Requirements

### 7.1 Minimum Standards

**Before publishing results, ensure:**

✓ **Sample Size Adequacy**
  - Power analysis shows ≥80% power to detect 100 ELO difference
  - Minimum 20 comparisons per pairing per arena
  - Sequential testing used to minimize waste

✓ **Multiple Comparison Control**
  - FDR correction applied (Benjamini-Hochberg)
  - All p-values reported are adjusted
  - Family-wise error rate ≤ 0.05

✓ **Confidence Intervals**
  - All ELO scores reported with 95% CI
  - Overlapping CIs flagged as "not significantly different"
  - Bayesian posterior distributions tracked

✓ **Judge Reliability**
  - Inter-judge agreement ≥ 70%
  - Calibration set accuracy ≥ 80%
  - Test-retest consistency ≥ 85%

✓ **Variance Accounting**
  - Solution variance measured (multiple generations)
  - Judge variance isolated (same solutions, multiple judgments)
  - Task variance analyzed (stratified by difficulty)

✓ **Effect Size Reporting**
  - Cohen's h for all significant differences
  - Not just p-values (avoid p-hacking appearance)
  - Practical significance discussed

### 7.2 Reproducibility Checklist

□ All random seeds logged  
□ Exact model versions recorded (claude-sonnet-4.5-20250929)  
□ Judge prompts versioned and stored  
□ Solution cache preserved  
□ Raw data exported for reanalysis  
□ Configuration files included in output  
□ API timestamps recorded (detect model updates)  

---

## 8. Quality Assurance

### 8.1 Unit Tests

**Coverage targets: >90%**

Test categories:
- Statistical calculations (ELO, binomial tests, corrections)
- Judge consensus algorithms
- DUT isolation and caching
- Sequential testing logic
- Pareto frontier computation

### 8.2 Integration Tests

- End-to-end tournament on toy dataset
- Validate output formats (JSON schema validation)
- Test with actual API calls (small scale)
- Calibration set validation

### 8.3 Validation Tests

**Sanity checks:**
- Comparing identical solutions → always TIE
- Comparing obviously better vs worse → correct winner
- Human baseline should beat purely autonomous AI
- Reversed pairs (A vs B, then B vs A) → consistent

### 8.4 Performance Tests

- Tournament with 5 approaches on 10 tasks completes in <2 hours
- Memory usage stays <4GB
- Parallel processing scales linearly up to CPU count

---

## 9. Success Metrics

**The tool succeeds if:**

1. **Calibration**: ≥85% agreement with expert human judgments (raised from 80%)
   - Single judge: 80-85%
   - Panel of 3-5 judges: 85-90% (target)
   - Panel achieves this at 60-80% cost savings vs human-only

2. **Consistency**: Test-retest reliability ≥85% (raised from 85%)
   - Same comparison judged twice yields same result >85% of time
   - Inter-judge agreement (Fleiss' Kappa) >0.6

3. **Cost**: Full tournament (Tier 2) costs <$500
   - With adaptive designs: <$300 typical
   - 30-50% cost reduction vs naive evaluation
   
4. **Efficiency**: Adaptive designs save 30-50% without power loss
   - Sequential testing achieves early stopping 30-40% of time
   - MAMS eliminates 60-70% of poor approaches early
   
5. **Statistical Rigor**: Publications cite methodology
   - Pre-registration standard becomes adopted
   - Effect sizes with CIs reported universally
   - FDR control becomes default for exploratory work
   
6. **Adoption**: Used by ≥3 external research groups
   - Community contributions to task suite
   - Integration with existing tools (BigCode, SWE-bench)
   
7. **Impact**: Produces actionable insights
   - At least one counterintuitive finding published
   - Pareto frontiers influence production deployment decisions
   - Cost-effectiveness analysis changes purchasing behavior
   
8. **Transparency**: Full open science compliance
   - Data, code, and materials publicly available
   - Pre-registrations time-stamped on OSF
   - Reproducible analyses (R Markdown/Jupyter)
   
9. **Practical Utility**: Industry deployment
   - Used in at least 2 company evaluation pipelines
   - Cited in product selection documentation
   - Integrated into CI/CD for quality monitoring

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **AI judges unreliable** | Medium | High | Extensive calibration, multiple judges, consensus voting |
| **Tasks too easy** | Medium | High | Use real brownfield commits, expert validation |
| **High variance in results** | High | Medium | Large sample sizes, sequential testing, confidence intervals |
| **API cost explosion** | Low | High | Sequential testing, caching, budget limits |
| **Model updates break reproducibility** | High | Medium | Pin model versions, timestamp all runs |
| **Judge prompt leakage** | Low | High | Version control prompts, detect contamination |
| **Cherry-picking results** | Medium | High | Pre-register hypotheses, publish all results |

---

## 11. Future Extensions

**Post-MVP features:**

- [ ] Support for more languages (Rust, C++, Java, Go)
- [ ] Interactive mode for debugging approaches
- [ ] Real-time leaderboard server
- [ ] Integration with GitHub Actions (CI benchmarking)
- [ ] Cost prediction before running tournament
- [ ] Automated task extraction from git history
- [ ] Multi-objective optimization (quality + speed + cost)
- [ ] Temporal analysis (does approach quality degrade over time?)
- [ ] Human-in-the-loop validation mode

---

## 12. Development Phases

### Phase 1: MVP (8 weeks)
- [ ] Core architecture (DUT, cache, judge orchestrator)
- [ ] Basic statistical engine (ELO, binomial tests)
- [ ] CLI with `generate`, `judge`, `tournament` commands
- [ ] Terminal output only
- [ ] 5 reference tasks from open-source projects
- [ ] 2 built-in DUTs (simple-chat, elaborate-prompt)

### Phase 2: Statistical Rigor (4 weeks)
- [ ] Bayesian ELO with uncertainty
- [ ] Sequential testing
- [ ] Multiple comparison correction
- [ ] Variance decomposition
- [ ] Judge reliability metrics
- [ ] Calibration framework

### Phase 3: Usability (4 weeks)
- [ ] HTML reports with interactive plots
- [ ] JSON/CSV export
- [ ] Pareto frontier visualization
- [ ] Comprehensive documentation
- [ ] Example configs and tutorials
- [ ] 20 diverse tasks

### Phase 4: Validation (4 weeks)
- [ ] External testing with volunteers
- [ ] Comparison with human expert rankings
- [ ] Publication-ready figures
- [ ] Preprint/paper
- [ ] Public leaderboard

---

## 13. Dependencies

**Core:**
- Python ≥3.10
- numpy, scipy (statistics)
- pandas (data manipulation)
- matplotlib, seaborn, plotly (plotting)
- pyyaml (config parsing)
- click (CLI framework - recommended over argparse for complexity)
- anthropic, openai (AI APIs)

**Statistical & Rating:**
- statsmodels (power analysis, multiple testing, mixed models)
- trueskill (TrueSkill rating system - pip install trueskill)
- glicko2 (Alternative rating - pip install glicko2)
- scikit-learn (optional, for ML-based metrics)
- pingouin (effect sizes, post-hoc tests)

**Multi-Objective Optimization:**
- pymoo (Pareto frontier, NSGA-II - pip install pymoo)

**AI Judge Frameworks:**
- deepeval (G-Eval, pre-built metrics - pip install deepeval)
- langchain (optional, for judge orchestration)

**Development:**
- pytest, pytest-cov (testing)
- black, ruff (formatting, linting)
- mypy (type checking)
- sphinx (documentation)

**Optional:**
- jinja2 (HTML reports)
- streamlit (interactive dashboards)
- tqdm (progress bars)
- wandb or mlflow (experiment tracking)

---

## 14. Open Questions

1. **How to handle non-deterministic models?**
   - Some APIs don't support seeds
   - Solution: Generate multiple times, report distribution

2. **What if human baseline is expensive?**
   - Pay expert developers?
   - Use historical commits as proxy?

3. **How to validate judge prompts aren't biased?**
   - Red-teaming: adversarial prompt testing
   - Compare multiple prompt formulations

4. **Should we weight arenas differently?**
   - Some users care more about maintainability than performance
   - Solution: Allow custom weights in config

5. **How to handle tasks with no clear answer?**
   - Multiple valid approaches
   - Judge on principles, not exact solution match

---

## 15. References

- SWE-bench: https://www.swebench.com/
- Chatbot Arena: https://chat.lmsys.org/
- ELO rating system: https://en.wikipedia.org/wiki/Elo_rating_system
- Multiple testing correction: Benjamini & Hochberg (1995)
- Sequential analysis: Wald (1945)

---

## Appendix A: Recommended Workflow (Research-Informed)

This workflow integrates best practices from medical trials, software engineering experiments, and AI evaluation frameworks.

### Phase 1: Planning (2-3 weeks)

**Week 1: Goal Definition & Pre-registration**
```bash
# 1. Define goals using GQM framework
codegen-bench init --tasks=core ./my-benchmark

# 2. Create pre-registration document
codegen-bench preregister \
  --duts=gpt-4,claude-opus,gemini-pro \
  --hypotheses=hypotheses.yaml \
  --primary-outcome=correctness \
  --secondary-outcomes=efficiency,security,maintainability \
  --sample-size=300 \
  --alpha=0.05 \
  --correction=fdr_bh \
  --power=0.80 \
  --stopping-rules=sequential.yaml \
  --osf \
  preregistration.yaml

# 3. Power analysis
codegen-bench power-analysis \
  --effect-size=0.5 \
  --alpha=0.05 \
  --power=0.80 \
  --design=sequential \
  --output=power-analysis.pdf
```

**Week 2-3: Infrastructure Setup**
```bash
# 4. Calibrate AI judges
codegen-bench calibrate \
  --ground-truth=./gold-standard-100.yaml \
  --min-agreement=0.85 \
  --output=calibration-report.json

# Expected: 85%+ agreement with 3-5 judge panel
# If <85%, iterate on judge prompts

# 5. Validate infrastructure
codegen-bench validate --all ./infrastructure-tests/
```

### Phase 2: Initial Screening via MAMS (1 week, ~$5K)

```bash
# Multi-Arm Multi-Stage design
codegen-bench tournament \
  --duts=approach1,approach2,approach3,approach4,approach5 \
  --adaptive \
  --phase=mams-screening \
  --cheap-metrics=correctness,basic-tests \
  --samples=50 \
  --correction=dunnett \
  --output-dir=./results/phase1-mams

# Dunnett's test: 10-15% more powerful than Bonferroni
# Select top 2-3 approaches for Phase 2
```

**Expected Output:**
- 5 approaches compared vs baseline
- Top 2-3 selected based on cheap proxies
- Cost: ~$5K (50 samples × $10/eval × 10 approaches)
- Time: 1 week

### Phase 3: Sequential Evaluation (2-3 weeks, ~$7K expected)

```bash
# Group sequential design with early stopping
codegen-bench tournament \
  --duts=selected-approach1,selected-approach2,baseline \
  --adaptive \
  --phase=sequential \
  --full-metrics=all \
  --max-samples=100 \
  --interim-analyses=33,67,100 \
  --boundaries=obrien-fleming \
  --rating-system=trueskill \
  --correction=fdr_bh \
  --preregistration=preregistration.yaml \
  --output-dir=./results/phase2-sequential

# O'Brien-Fleming: Conservative early stopping
# Expected: Stop at 67% checkpoint (n=67) with 30% probability
```

**Expected Output:**
- Detailed evaluation with all metrics
- Early stopping if clear winner emerges
- Cost: $7K expected (vs $10K budgeted)
- Time: 2-3 weeks
- TrueSkill ratings with uncertainty

### Phase 4: Non-Inferiority & Cost-Effectiveness (1 week, ~$3K)

```bash
# Test if cheaper approach is "good enough"
codegen-bench tournament \
  --duts=selected-winner,expensive-baseline \
  --test=non-inferiority \
  --baseline=expensive-baseline \
  --margin=0.05 \
  --samples=50 \
  --output-dir=./results/phase3-noninf

# ICER calculation
codegen-bench analyze \
  --icer \
  --wtp-threshold=100 \
  ./results/phase3-noninf
```

**Expected Output:**
- Non-inferiority determination
- ICER (cost per quality unit)
- Cost-effectiveness plane
- Production deployment recommendation

### Phase 5: Comprehensive Analysis (1 week)

```bash
# Pareto frontier
codegen-bench analyze \
  --pareto \
  --objectives=quality,cost,speed \
  ./results/**/*

# Variance decomposition
codegen-bench analyze \
  --variance-decomposition \
  --mixed-model \
  ./results/**/*

# Effect sizes
codegen-bench analyze \
  --effect-sizes \
  --all-pairwise \
  --ci=0.95 \
  ./results/**/*

# Full report
codegen-bench leaderboard \
  --format=html \
  --include-all-metrics \
  --pareto \
  --effect-sizes \
  --icer \
  ./results > final-report.html
```

### Phase 6: Open Science & Dissemination (Ongoing)

```bash
# Export data
codegen-bench export \
  --format=csv \
  --anonymize=false \
  --include-raw \
  ./results ./data-release/

# Upload to repositories
git add data-release/
git commit -m "Release benchmark data"
git push

# OSF upload
codegen-bench upload-osf \
  --project=abc123 \
  --data=./data-release/ \
  --code=./src/ \
  --materials=./materials/

# Generate preprint
codegen-bench generate-manuscript \
  --template=arxiv \
  --results=./results \
  --output=manuscript.tex
```

### Complete Timeline & Budget

**Total Duration:** 8-10 weeks
**Total Budget:** ~$15K

| Phase | Duration | Cost | Key Outputs |
|-------|----------|------|-------------|
| Planning | 2-3 weeks | $0 | Pre-registration, calibrated judges |
| MAMS Screening | 1 week | $5K | Top 2-3 approaches selected |
| Sequential Evaluation | 2-3 weeks | $7K | Winner identified, ratings |
| Non-Inferiority | 1 week | $3K | Production decision |
| Analysis | 1 week | $0 | Pareto frontiers, reports |
| Dissemination | Ongoing | $0 | Papers, data release |

**Cost Savings:** 40-50% vs naive evaluation (~$25K)
**Statistical Guarantees Maintained:** FWER ≤ 0.05, Power ≥ 0.80

### Critical Success Factors

✓ **Pre-register before data collection** - prevents p-hacking
✓ **Calibrate judges to 85%+ agreement** - ensures validity
✓ **Use adaptive designs** - maximizes efficiency
✓ **Always report effect sizes with CIs** - enables meta-analysis
✓ **FDR control for exploratory** - balances discovery and rigor
✓ **Share data and code openly** - enables verification
✓ **Document all deviations** - maintains credibility

---

## Appendix B: Example Usage Workflow

```bash
# 1. Initialize benchmark
codegen-bench init --tasks=core ./my-benchmark
cd my-benchmark

# 2. Generate solutions with different approaches
codegen-bench generate --dut=simple-chat --all-tasks --samples=3
codegen-bench generate --dut=elaborate-prompt --all-tasks --samples=3
codegen-bench generate --dut=multi-agent --all-tasks --samples=3

# 3. Run tournament
codegen-bench tournament \
  --duts=simple-chat,elaborate-prompt,multi-agent \
  --tier=2 \
  --sequential-test \
  --output-dir=./results

# 4. View results
codegen-bench leaderboard --pareto ./results

# 5. Deep dive into statistics
codegen-bench analyze \
  --variance-decomposition \
  --power-analysis \
  --judge-reliability \
  ./results

# 6. Export for publication
codegen-bench leaderboard --format=latex ./results > paper/table.tex
codegen-bench leaderboard --format=json ./results > paper/data.json
```

---

**End of PRD**