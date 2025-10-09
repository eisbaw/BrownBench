# API Reference

This document provides an overview of the BrownBench API and links to auto-generated API documentation.

## Auto-Generated Documentation

The full API reference is auto-generated from source code docstrings using `pdoc`. To generate or update the API documentation:

```bash
just docs-api
```

This creates HTML documentation in `docs/api/` with full module, class, and function documentation.

You can browse the generated documentation by opening `docs/api/index.html` in a web browser.

## Core Modules

### Task Management

- **`codegen_bench.core.task`**: Task dataclass and validation
  - `Task`: Benchmark task specification with validation
  - `Task.from_yaml()`: Load tasks from YAML files
  - `Task.validate()`: Validate task structure and paths

- **`codegen_bench.tasks.loader`**: Task loading and management
  - `load_task()`: Load a single task from file
  - `load_task_set()`: Load multiple tasks from a directory

### DUT (Device Under Test)

- **`codegen_bench.dut.base`**: Base classes for DUT implementations
  - `CodeGenerationApproach`: Abstract base class for all DUTs
  - `ApproachMetadata`: Metadata about a code generation approach
  - `solve()`: Generate solution for a task

- **`codegen_bench.dut.simple_chat`**: Simple chat-based DUT
  - `SimpleChatDUT`: Basic implementation using LLM chat APIs

- **`codegen_bench.dut.elaborate_prompt`**: Enhanced prompt DUT
  - `ElaboratePromptDUT`: DUT with brownfield-focused prompts

- **`codegen_bench.dut.registry`**: DUT registry and management
  - `DUTRegistry`: Global registry for DUT implementations
  - `register_dut()`: Register a new DUT class
  - `get_dut()`: Retrieve a registered DUT

### Arena & Judgment

- **`codegen_bench.core.arena`**: Quality dimensions for evaluation
  - `Arena`: Defines a quality dimension (e.g., correctness, maintainability)

- **`codegen_bench.core.judgment`**: Judgment results
  - `JudgmentResult`: Result of comparing two solutions
  - `winner`: 'A', 'B', or 'TIE'
  - `agreement_rate`: Agreement between judges
  - `confidence`: Confidence level of judgment

- **`codegen_bench.judge.base`**: Base classes for judges
  - `Judge`: Abstract base class for judge implementations

- **`codegen_bench.judge.claude_judge`**: Claude-based judge
  - `ClaudeJudge`: Judge using Claude API for comparisons

- **`codegen_bench.judge.orchestrator`**: Judge orchestration
  - `JudgeOrchestrator`: Manages multiple judges and consensus

### Configuration

- **`codegen_bench.core.config`**: Configuration dataclasses
  - `TournamentConfig`: Tournament-level configuration
    - `base_seed`: Master seed for reproducibility
    - `samples_per_pairing`: Number of samples per (DUT, task) pair
    - `checkpoint_interval`: How often to save checkpoints
  - `TrueSkillConfig`: TrueSkill rating system configuration
    - `initial_mu`: Initial mean skill rating
    - `initial_sigma`: Initial skill uncertainty
    - `beta`: Distance for 76% win probability
    - `tau`: Skill dynamics factor
    - `draw_probability`: Expected probability of draws
  - `PricingConfig`: API pricing configuration
    - `claude_sonnet_4_5_input_per_1k`: Cost per 1,000 input tokens ($0.003 default)
    - `claude_sonnet_4_5_output_per_1k`: Cost per 1,000 output tokens ($0.015 default)

### Tournament

- **`codegen_bench.core.tournament`**: Tournament execution
  - `TournamentRunner`: Run tournaments comparing multiple DUTs
  - `TournamentResult`: Tournament results with ratings and comparisons
  - `DUTRating`: ELO rating and statistics for a DUT
  - `run()`: Execute full tournament with checkpointing

- **`codegen_bench.core.solution`**: Solution representation
  - `Solution`: Generated code solution with metadata

### Statistical Analysis

- **`codegen_bench.stats.ratings.bayesian_elo`**: Bayesian ELO rating system
  - `BayesianELO`: Bayesian approach to ELO with uncertainty

- **`codegen_bench.stats.ratings.trueskill_rating`**: TrueSkill rating
  - `TrueSkillRating`: Microsoft TrueSkill rating wrapper

- **`codegen_bench.stats.correction`**: Multiple testing correction
  - `correct_pvalues()`: Apply FDR correction (Benjamini-Hochberg)
  - `dunnett_test()`: Dunnett's test for MAMS
  - `estimate_fdr()`: False discovery rate estimation

- **`codegen_bench.stats.effect_size`**: Effect size calculations
  - `cohens_d()`: Cohen's d effect size
  - `interpret_cohens_d()`: Interpretation of effect size

- **`codegen_bench.stats.power`**: Statistical power analysis
  - `calculate_sample_size()`: Required sample size for power
  - `calculate_achieved_power()`: Achieved power for sample
  - `minimum_detectable_effect()`: Minimum effect detectable

- **`codegen_bench.stats.variance`**: Variance decomposition
  - `fit_mixed_model()`: Fit mixed linear model
  - `calculate_icc()`: Intraclass correlation coefficient
  - `decompose_variance()`: Variance components analysis

- **`codegen_bench.stats.adaptive.sequential`**: Sequential testing
  - `GroupSequentialDesign`: O'Brien-Fleming boundaries
  - `check_stopping()`: Early stopping criteria

- **`codegen_bench.stats.adaptive.mams`**: Multi-arm multi-stage design
  - `MAMSDesign`: Two-stage adaptive design
  - `screen_phase()`: Phase 1 screening
  - `evaluation_phase()`: Phase 2 full evaluation

- **`codegen_bench.stats.calibration`**: Judge calibration
  - `calculate_agreement_rate()`: Agreement with ground truth
  - `calculate_fleiss_kappa()`: Inter-rater reliability
  - `detect_position_bias()`: Position bias detection
  - `generate_calibration_report()`: Full calibration report

- **`codegen_bench.stats.ground_truth`**: Ground truth management
  - `GroundTruthComparison`: Ground truth judgment
  - `load_ground_truth()`: Load from YAML file

- **`codegen_bench.stats.pareto`**: Pareto frontier analysis
  - `compute_pareto_frontier()`: Identify Pareto-optimal solutions
  - `calculate_hypervolume()`: Hypervolume metric
  - `identify_dominated()`: Find dominated solutions

### Reporting & Visualization

- **`codegen_bench.reporting.terminal`**: Terminal output
  - `print_leaderboard()`: Display results in terminal

- **`codegen_bench.reporting.exporters`**: Export formats
  - `export_to_json()`: Export results to JSON
  - `export_to_csv()`: Export results to CSV
  - `export_to_latex()`: Export results to LaTeX table
  - `export_all_formats()`: Export to all formats

- **`codegen_bench.reporting.visualization`**: Visualization
  - `plot_elo_ratings()`: Plot ELO ratings with uncertainty
  - `plot_arena_breakdown()`: Per-arena performance
  - `plot_cost_analysis()`: Cost analysis charts

- **`codegen_bench.reporting.html`**: HTML reports
  - `HTMLReporter`: Generate interactive HTML reports
  - `generate()`: Create HTML report with Plotly charts

### Security & Safety

- **`codegen_bench.security.isolation`**: Container isolation
  - `ContainerIsolation`: Docker-based DUT isolation
  - `build_container()`: Build DUT container image
  - `run_isolated()`: Execute DUT in container

- **`codegen_bench.security.api_proxy`**: API proxy
  - `APIProxy`: HTTP proxy for API key management
  - `start()`: Start proxy server
  - `create_temp_key()`: Generate temporary API key

- **`codegen_bench.security.auditor`**: DUT auditing
  - `DUTAuditor`: Static analysis for dangerous patterns
  - `audit()`: Audit DUT code for safety

- **`codegen_bench.budget.enforcer`**: Budget enforcement
  - `BudgetEnforcer`: Cost tracking and limits
  - `check_budget()`: Check if operation allowed
  - `record_cost()`: Track API costs

### Validation & Testing

- **`codegen_bench.validation.executor`**: Test execution
  - `ValidationExecutor`: Execute test suites
  - `compile()`: Compile code with timeout
  - `run_tests()`: Run test suite with timeout

- **`codegen_bench.validation.worktree`**: Git worktree management
  - `WorktreeManager`: Safe git worktree operations
  - `create()`: Create worktree for testing
  - `cleanup()`: Remove worktree

- **`codegen_bench.validation.applicator`**: Apply solutions
  - `SolutionApplicator`: Apply generated code to codebase

### Caching & State

- **`codegen_bench.cache.store`**: Solution caching
  - `SolutionCache`: Cache for generated solutions
    - `get()`: Retrieve cached solution
    - `put()`: Store solution in cache (atomic write with temp file)
    - `clear()`: Clear all cached solutions
    - `size()`: Get number of cached solutions
    - `invalidate()`: Remove specific cached entry

  **⚠️ Important Cache Management Notes:**
  - **No Size Limits**: The cache has no built-in size limits and will grow unbounded
  - **Disk Space**: Monitor disk usage as cache can consume significant space over time
  - **Manual Cleanup**: Use `clear()` method or manually delete `.cache/` directory
  - **Atomic Writes**: Uses temp file + atomic rename for concurrent write safety
  - **Cache Keys**: SHA-256 hashes of (dut_id, dut_version, task_id, seed)
  - **No TTL/Expiration**: Cache entries persist indefinitely until manually cleared

  **Recommended Cache Management Practices:**
  ```python
  # Monitor cache size
  cache = SolutionCache(Path(".cache"))
  if cache.size() > 10000:  # Threshold for your use case
      cache.clear()  # Or implement selective eviction

  # Periodic cleanup (e.g., in CI/CD)
  find .cache -type f -mtime +30 -delete  # Remove files older than 30 days

  # Size monitoring
  du -sh .cache  # Check total cache directory size
  ```

- **`codegen_bench.checkpoint.manager`**: Tournament checkpointing
  - `CheckpointManager`: Save/restore tournament state
  - `save()`: Save checkpoint
  - `load()`: Load checkpoint
  - `is_comparison_completed()`: Check completion status

### Utilities

- **`codegen_bench.utils.rate_limiter`**: Rate limiting
  - `RateLimiter`: Token bucket rate limiter
  - `acquire()`: Acquire token (wait if needed)

- **`codegen_bench.utils.shutdown_handler`**: Graceful shutdown
  - `ShutdownHandler`: Handle SIGINT/SIGTERM signals
  - `register()`: Register signal handlers
  - `shutdown_requested`: Check if shutdown requested

- **`codegen_bench.utils.hashing`**: Hashing utilities
  - `compute_prompt_hash()`: SHA-256 hash of prompts

### Exceptions

- **`codegen_bench.exceptions`**: Exception hierarchy
  - `BrownBenchError`: Base exception with context
  - `ValidationError`: Validation failures
  - `ExecutionError`: Execution failures
  - `BudgetExceededError`: Budget limit exceeded
  - `CacheError`: Cache operation failures
  - `WorktreeError`: Git worktree failures
  - `ContainerError`: Container operation failures
  - `ErrorContext`: Error context with severity

## CLI

- **`codegen_bench.cli.main`**: Command-line interface
  - `tournament`: Run tournaments
  - `calibrate`: Calibrate judges
  - `export`: Export results

See [CLI Reference](CLI_REFERENCE.md) for detailed command documentation.

## Usage Examples

### Basic Tournament

```python
from pathlib import Path
from codegen_bench.core.task import Task
from codegen_bench.core.arena import Arena
from codegen_bench.core.tournament import TournamentRunner
from codegen_bench.core.config import TournamentConfig
from codegen_bench.dut.simple_chat import SimpleChatDUT
from codegen_bench.judge.orchestrator import JudgeOrchestrator
from codegen_bench.judge.claude_judge import ClaudeJudge
from codegen_bench.cache.store import SolutionCache

# Configure tournament
config = TournamentConfig(
    base_seed=42,
    samples_per_pairing=3,
    checkpoint_interval=10
)

# Load tasks
task = Task.from_yaml(Path("tasks/task-001.yaml"))
task.validate()

# Setup DUT
dut = SimpleChatDUT(config={
    "model": "claude-3-5-sonnet-20241022",
    "provider": "anthropic"
})

# Setup judge
judge = ClaudeJudge(api_key="your-key")
judges = JudgeOrchestrator([judge], consensus_threshold=1)

# Setup arena
arena = Arena(
    name="correctness",
    description="Does the code work?",
    criteria=["Passes all tests", "No errors"]
)

# Run tournament
cache = SolutionCache(Path(".cache"))
runner = TournamentRunner(
    duts=[dut],
    tasks=[task],
    judges=judges,
    arenas=[arena],
    cache=cache,
    config=config  # Pass the config
)

result = runner.run(output_dir=Path("results"))
print(result.get_leaderboard())
```

### TrueSkill Rating Example

```python
from codegen_bench.core.config import TrueSkillConfig
from codegen_bench.stats.ratings.trueskill_rating import TrueSkillRating

# Configure TrueSkill for your environment
config = TrueSkillConfig(
    initial_mu=30.0,
    initial_sigma=10.0,
    draw_probability=0.15  # 15% draws expected
)

# Set as default for all new ratings
TrueSkillRating.set_default_config(config)

# Create players
player_a = TrueSkillRating()  # Uses config defaults
player_b = TrueSkillRating()

# After match (A beats B)
player_a.update(player_b, "win")

print(f"Player A: {player_a}")  # Higher mu, lower sigma
print(f"Player B: {player_b}")  # Lower mu, lower sigma
```

### Export Results

```python
from codegen_bench.reporting.exporters import export_all_formats
from codegen_bench.core.tournament import TournamentResult

# Load results
result = TournamentResult.from_dict(data)

# Export to all formats
export_all_formats(
    result,
    output_dir=Path("exports"),
    include_pareto=True
)
```

### Generate HTML Report

```python
from codegen_bench.reporting.html import HTMLReporter

reporter = HTMLReporter()
html_path = reporter.generate(
    result=result,
    output_dir=Path("reports"),
    include_pareto=True
)
```

## Type Annotations

All public APIs include type annotations and are checked with `mypy` in strict mode. You can run type checking with:

```bash
just typecheck
```

## Testing

All modules have comprehensive test coverage (>90%). Run tests with:

```bash
just test
```

## Extending BrownBench

See the following guides for extending BrownBench:

- [Adding DUTs](ADDING_DUTS.md)
- [Adding Arenas](ADDING_ARENAS.md)
- [Adding Judges](ADDING_JUDGES.md)
- [Contributing](../CONTRIBUTING.md)

## Further Reading

- [Architecture Overview](ARCHITECTURE.md)
- [Configuration Guide](CONFIGURATION.md)
- [Statistics Guide](STATISTICS_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
