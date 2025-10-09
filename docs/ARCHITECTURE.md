# BrownBench Architecture Overview

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Module Organization](#module-organization)
5. [Key Design Decisions](#key-design-decisions)
6. [Extension Points](#extension-points)

## System Overview

BrownBench is a statistically rigorous benchmark suite for evaluating AI-assisted code generation approaches in brownfield (existing) software projects. The system follows a tournament-style evaluation where different AI approaches (DUTs - Devices Under Test) generate solutions for real-world programming tasks, and those solutions are judged across multiple quality dimensions.

### High-Level Architecture

```
┌─────────────┐
│   CLI       │  Entry point for all user interactions
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────────┐
│            Tournament Runner                     │
│  Orchestrates the entire benchmark process      │
└──────┬──────────────────────────────────────────┘
       │
       ├─────► DUT Registry ──► DUTs (AI approaches)
       │
       ├─────► Task Registry ──► Tasks (coding challenges)
       │
       ├─────► Arena ──► Quality dimensions
       │
       ├─────► Judge ──► Solution evaluation
       │
       └─────► Stats Engine ──► Statistical analysis
```

## Core Components

### 1. Domain Models (`codegen_bench/core/`)

Core domain entities that represent the fundamental concepts:

- **Task**: A programming challenge extracted from real OSS commits
  - Contains: original code, diff, commit message, test suite
  - Immutable dataclass with validation
  - Supports cloning for isolated execution

- **Solution**: Generated code from a DUT for a specific task
  - Contains: generated code, task reference, DUT metadata
  - Immutable with hash-based identity
  - Cacheable for reproducibility

- **Arena**: Quality evaluation dimension
  - Examples: maintainability, architecture, surgical_precision
  - Contains: name, description, judging prompt
  - Defines what aspects to evaluate

- **JudgmentResult**: Outcome of comparing two solutions
  - Contains: winner (A/B/tie), confidence, reasoning
  - Supports consensus from multiple judges
  - Immutable record of evaluation

### 2. DUT (Device Under Test) System (`codegen_bench/dut/`)

Abstracts different AI code generation approaches:

- **BaseDUT**: Abstract interface
  - `solve(task: Task, arena: Arena) -> Solution`
  - Defines contract for all AI approaches

- **DUTRegistry**: Plugin system for DUT discovery
  - Decorator-based registration: `@register_dut("name")`
  - Automatic loading from entry points
  - Type-safe retrieval

- **Implementations**:
  - `SimpleChatDUT`: Basic chat-based approach
  - `ElaboratePromptDUT`: Enhanced prompts with codebase context
  - *Future*: ClaudeCodeDUT, custom approaches

### 3. Judge System (`codegen_bench/judge/`)

Evaluates solution quality:

- **BaseJudge**: Abstract evaluator interface
  - `judge(solution_a, solution_b, arena) -> JudgmentResult`
  - Side-by-side comparison model

- **ClaudeJudge**: AI-powered evaluation
  - Uses Anthropic Claude for judgments
  - Arena-specific prompting
  - Consensus voting across multiple judges

- **Prompt Engineering** (`judge/prompts/`):
  - Structured prompts per arena
  - Position bias mitigation
  - Calibrated against ground truth

### 4. Tournament System (`codegen_bench/core/tournament.py`)

Orchestrates the benchmark:

- **TournamentRunner**: Main execution engine
  - Round-robin solution generation
  - Pairwise comparisons in each arena
  - Statistical analysis pipeline
  - Checkpoint/resume support

- **Workflow**:
  1. Load DUTs and tasks
  2. Generate solutions (with caching)
  3. Run pairwise comparisons
  4. Update TrueSkill ratings
  5. Calculate statistics
  6. Generate reports

### 5. Statistical Engine (`codegen_bench/stats/`)

Rigorous statistical analysis:

- **Ratings** (`stats/ratings/`):
  - TrueSkillRating: Bayesian skill estimation
  - Conservative estimates (μ - 2σ)
  - Match quality prediction

- **Effect Sizes** (`stats/effect_size.py`):
  - Cohen's d with confidence intervals
  - Win rate with binomial CI
  - Practical significance thresholds

- **Multiple Comparison Correction** (`stats/correction.py`):
  - Benjamini-Hochberg (FDR control)
  - Holm-Bonferroni (FWER control)
  - Dunnett's test for MAMS

- **Variance Analysis** (`stats/variance.py`):
  - Mixed linear models
  - ICC calculation
  - Variance decomposition (approach, task, arena)

- **Adaptive Designs** (`stats/adaptive/`):
  - Sequential testing with O'Brien-Fleming boundaries
  - MAMS (Multi-Arm Multi-Stage) designs
  - Early stopping for efficiency

### 6. Security & Isolation (`codegen_bench/security/`)

Safe execution of untrusted code:

- **ContainerIsolation**: Docker-based sandboxing
  - Network restrictions (API proxy only)
  - Resource limits (CPU, memory)
  - Read-only mounts
  - Automatic cleanup

- **APIProxy**: Secure API access
  - Temporary key generation per DUT
  - Request forwarding with real keys
  - Cost tracking per DUT
  - Budget enforcement integration

- **DUTAuditor**: Static analysis
  - Dangerous pattern detection
  - Network access analysis
  - Audit report generation
  - Integration with DUT loading

### 7. Budget Management (`codegen_bench/budget/`)

Cost control for API usage:

- **BudgetEnforcer**:
  - Per-DUT cost limits
  - Global tournament budget
  - Thread-safe cost tracking
  - Pre-flight checks
  - Warning thresholds (50%, 75%, 90%)
  - Hard stops when exceeded

### 8. Checkpointing (`codegen_bench/checkpoint/`)

Long-running tournament resilience:

- **CheckpointManager**:
  - Atomic save operations
  - Progress tracking
  - Resume from checkpoint
  - Immutable state snapshots
  - Graceful degradation on errors

### 9. Caching (`codegen_bench/cache/`)

Reproducibility and efficiency:

- **SolutionCache**:
  - Hash-based key generation
  - Atomic file operations
  - Thread-safe reads/writes
  - Disk-based storage
  - Supports deterministic replay

### 10. Reporting (`codegen_bench/reporting/`)

Results presentation:

- **Exporters**:
  - JSON with schema
  - CSV for custom analysis
  - LaTeX tables for papers
  - HTML with interactive visualizations

- **HTMLReporter**:
  - Jinja2 templates
  - Plotly interactive charts
  - Sortable leaderboards
  - Per-arena breakdowns
  - Cost analysis

- **Visualization**:
  - Pareto frontier analysis (pymoo)
  - Multi-objective optimization
  - Hypervolume metrics
  - Dominated solution identification

### 11. CLI (`codegen_bench/cli/`)

User interface:

- **Commands**:
  - `init`: Set up benchmark structure
  - `generate`: Create solutions
  - `tournament`: Run evaluation
  - `leaderboard`: Display results
  - `calibrate`: Judge calibration
  - `export`: Export results

- **Features**:
  - Rich progress indicators
  - Structured logging
  - Configuration validation
  - Error handling with actionable messages

## Data Flow

### Solution Generation Flow

```
User Command
    │
    ▼
CLI (generate)
    │
    ▼
Load Tasks ──► Task Registry
    │
    ▼
Load DUT ──► DUT Registry
    │
    ▼
For each task:
    │
    ▼
Check Cache ──► Solution Cache
    │                 │
    │                 ├─► Hit: Return cached
    │                 │
    │                 └─► Miss:
    ▼                       │
DUT.solve(task) ◄───────────┘
    │
    ▼
Store in Cache
    │
    ▼
Return Solution
```

### Tournament Execution Flow

```
User Command
    │
    ▼
CLI (tournament)
    │
    ▼
Load Configuration
    │
    ▼
Budget Pre-flight Check ──► BudgetEnforcer
    │
    ▼
Load DUTs ──► DUTRegistry ──► DUTAuditor
    │
    ▼
Load Tasks ──► Task Registry
    │
    ▼
Check Checkpoint ──► CheckpointManager
    │                      │
    │                      ├─► Resume: Load state
    │                      │
    │                      └─► New: Initialize
    ▼
Generate Solutions ──► DUT.solve() ──► Cache
    │
    ▼
For each arena:
    │
    ▼
Pairwise Comparisons ──► Judge.judge()
    │                         │
    │                         ▼
    │                    APIProxy (if isolated)
    │                         │
    │                         ▼
    │                    Track Costs ──► BudgetEnforcer
    │
    ▼
Update Ratings ──► TrueSkill
    │
    ▼
Calculate Statistics ──► Stats Engine
    │
    ▼
Save Checkpoint ──► CheckpointManager
    │
    ▼
Generate Reports ──► Exporters
    │
    ▼
Return Results
```

## Module Organization

```
src/codegen_bench/
├── core/               # Domain models
│   ├── task.py
│   ├── solution.py
│   ├── arena.py
│   ├── judgment.py
│   ├── tournament.py
│   └── preregistration.py
│
├── dut/               # AI approach implementations
│   ├── base.py
│   ├── registry.py
│   ├── simple_chat.py
│   └── elaborate_prompt.py
│
├── judge/             # Solution evaluation
│   ├── base.py
│   ├── claude_judge.py
│   └── prompts/
│
├── stats/             # Statistical analysis
│   ├── ratings/      # TrueSkill, Elo
│   ├── adaptive/     # Sequential, MAMS
│   ├── effect_size.py
│   ├── correction.py
│   ├── variance.py
│   ├── calibration.py
│   ├── ground_truth.py
│   └── pareto.py
│
├── security/          # Isolation & safety
│   ├── isolation.py
│   ├── api_proxy.py
│   └── auditor.py
│
├── budget/            # Cost management
│   └── enforcer.py
│
├── checkpoint/        # State persistence
│   └── manager.py
│
├── cache/            # Solution caching
│   └── store.py
│
├── reporting/        # Results output
│   ├── exporters.py
│   ├── html.py
│   ├── visualization.py
│   └── templates/
│
├── validation/       # Solution execution
│   └── executor.py
│
├── utils/            # Shared utilities
│   ├── rate_limiter.py
│   ├── shutdown_handler.py
│   └── worktree.py
│
└── cli/              # Command-line interface
    └── main.py
```

## Key Design Decisions

### 1. Immutable Domain Models

**Decision**: Use frozen dataclasses for core entities (Task, Solution, Arena, etc.)

**Rationale**:
- Thread-safety for parallel execution
- Cacheable with stable hashes
- Prevents accidental mutation bugs
- Clear data flow without side effects

### 2. Registry Pattern for Extensibility

**Decision**: Decorator-based registration for DUTs, judges, and tasks

**Rationale**:
- Easy to add new implementations
- No central import management
- Plugin-style architecture
- Type-safe retrieval

**Example**:
```python
@register_dut("my-approach")
class MyDUT(BaseDUT):
    def solve(self, task: Task, arena: Arena) -> Solution:
        ...
```

### 3. Separation of Generation and Evaluation

**Decision**: Solutions are generated once, then evaluated across all arenas

**Rationale**:
- Efficiency: Don't regenerate for each arena
- Consistency: Same code evaluated by all judges
- Caching: Store solutions for reproducibility
- Modularity: Can change evaluation without regeneration

### 4. Statistical Rigor by Default

**Decision**: Built-in statistical analysis, not an afterthought

**Rationale**:
- TrueSkill ratings with uncertainty
- Effect sizes with confidence intervals
- Multiple comparison correction (FDR/FWER)
- Variance decomposition (ICC)
- Pre-registered hypotheses support

### 5. Security-First Execution

**Decision**: Container isolation and API proxying mandatory for untrusted code

**Rationale**:
- DUTs may contain malicious code
- Prevent network access (except via proxy)
- Resource limits to prevent DoS
- Audit before execution
- Budget enforcement to prevent runaway costs

### 6. Checkpoint-Based Resilience

**Decision**: Automatic checkpointing for long-running tournaments

**Rationale**:
- Tournaments can run for hours/days
- API failures should not lose progress
- Resume from last checkpoint
- Atomic saves prevent corruption

### 7. Multi-Arena Evaluation

**Decision**: Multiple quality dimensions, not a single score

**Rationale**:
- Code quality is multi-faceted
- Different use cases prioritize different dimensions
- Pareto frontier analysis for trade-offs
- More nuanced than single leaderboard

## Extension Points

### Adding a New DUT

1. Subclass `BaseDUT`
2. Implement `solve(task, arena) -> Solution`
3. Register with `@register_dut("name")`
4. Add to DUT documentation

See: [Adding New DUTs Guide](./ADDING_DUTS.md) (to be created)

### Adding a New Judge

1. Subclass `BaseJudge`
2. Implement `judge(solution_a, solution_b, arena) -> JudgmentResult`
3. Handle consensus if using multiple judges
4. Calibrate against ground truth

See: [Adding New Judges Guide](./ADDING_JUDGES.md) (to be created)

### Adding a New Arena

1. Create Arena instance with name, description, prompt
2. Add to arena registry or configuration
3. Optionally create custom judge prompt
4. Document evaluation criteria

See: [Adding New Arenas Guide](./ADDING_ARENAS.md) (to be created)

### Adding a New Task

1. Extract from real OSS commit (50-500 LoC)
2. Ensure test suite exists and passes
3. Create Task instance with metadata
4. Validate with `scripts/validate_commit_tests.py`
5. Document in task catalog

See: Task creation scripts in `scripts/`

### Adding Statistical Methods

1. Add to appropriate `stats/` module
2. Include unit tests with >90% coverage
3. Document mathematical basis
4. Integrate into TournamentRunner if needed
5. Add to statistical reporting

### Adding Export Formats

1. Implement exporter in `reporting/exporters.py`
2. Add format option to CLI
3. Document schema/structure
4. Add unit tests

## Testing Architecture

### Test Organization

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_arena.py
│   ├── test_dut.py
│   ├── test_stats.py
│   └── ...
│
├── integration/       # Multi-component tests
│   ├── test_tournament.py
│   ├── test_cli.py
│   └── ...
│
└── fixtures/          # Shared test data
    └── test_tasks/
```

### Coverage Standards

- Unit tests: >90% coverage per module
- Integration tests: Critical paths covered
- Use mocks for external APIs (Anthropic)
- Property-based testing for statistical code

## Performance Considerations

### Current Bottlenecks

1. **API calls**: Sequential judge calls (3-5 sec each)
   - *Future*: Async support for 3-5x speedup

2. **Solution generation**: Serial per-task
   - *Future*: Parallel generation for independent tasks

3. **Large tournaments**: Memory usage for all solutions
   - *Future*: Streaming approach with on-demand loading

### Optimization Strategies

- **Caching**: Solution cache prevents regeneration
- **Checkpointing**: Resume without recomputation
- **Adaptive designs**: Early stopping saves 30-50% cost
- **Rate limiting**: Token bucket for efficient API usage

## Error Handling

### Error Taxonomy

1. **Transient errors**: Retry with exponential backoff
   - API rate limits
   - Network failures

2. **Configuration errors**: Fail fast with actionable message
   - Invalid DUT/task/arena
   - Missing API keys

3. **Execution errors**: Log and continue
   - DUT solve() failures
   - Judge failures
   - Individual task failures

4. **Budget errors**: Hard stop
   - Per-DUT limit exceeded
   - Global budget exceeded

### Graceful Degradation

- Tournament continues if individual DUT fails
- Missing judgments handled in consensus voting
- Partial results saved to checkpoint
- Error records included in final report

## Security Model

### Threat Model

- **Untrusted DUT code**: May be malicious or buggy
- **API key exposure**: DUTs should not access real keys
- **Resource exhaustion**: Prevent DoS via limits
- **Data exfiltration**: No network access except API

### Mitigations

1. **Static analysis**: DUTAuditor scans before execution
2. **Container isolation**: Docker sandbox with restrictions
3. **API proxy**: Temporary keys, request forwarding
4. **Resource limits**: CPU, memory, time constraints
5. **Network isolation**: Only proxy communication allowed

## Future Architecture Plans

### Phase 6+ Enhancements

- **Async execution**: Concurrent API calls
- **Distributed tournaments**: Multi-machine support
- **Streaming results**: Handle tournaments with 1000+ tasks
- **Advanced caching**: LRU eviction, TTL, size limits
- **Metrics/observability**: Prometheus, OpenTelemetry
- **Web interface**: Real-time tournament monitoring
- **API server**: REST API for programmatic access

## References

- TrueSkill: Herbrich et al., "TrueSkill: A Bayesian Skill Rating System"
- MAMS: Wason & Jaki, "Optimal Design of Multi-Arm Multi-Stage Trials"
- Sequential Testing: Jennison & Turnbull, "Group Sequential Methods"
- Effect Sizes: Cohen, "Statistical Power Analysis for the Behavioral Sciences"
