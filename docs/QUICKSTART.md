# BrownBench Quickstart Guide

Get started with BrownBench in 5 minutes. This guide walks you through running your first benchmark evaluation.

## Prerequisites

- BrownBench installed (see [Installation Guide](INSTALLATION.md))
- Anthropic API key configured (`ANTHROPIC_API_KEY` environment variable)
- Git submodules initialized (for reference projects)

## 5-Minute Quickstart

###  1. Setup Project Submodules

Brown Bench uses real open-source projects as test codebases. Initialize them:

```bash
# Initialize all git submodules
git submodule update --init --recursive

# This downloads: git, redis, nginx, sqlite, curl, openssh, haproxy, tmux, jq, zstd, containerd, etcd, ripgrep
# Takes ~2-5 minutes depending on connection
```

### 2. Verify Installation

```bash
# Check CLI is working
codegen-bench --help

# Verify API key is set
echo $ANTHROPIC_API_KEY  # Should show your key
```

### 3. Generate Your First Solution

Let's generate a solution for a simple task:

```bash
# Generate solution for task 1 (git project) using simple-chat DUT
codegen-bench generate --dut simple-chat --task-id task_001 --seed 42

# Expected output:
# Generating solution with simple-chat
# Task: Add .gitattributes support
# Using cached solution  (if previously run)
#
# Solution generated!
# Files changed: 3
# Tokens: 2,450
# Cost: $0.0428
# Time: 12.34s
```

**What just happened?**
- BrownBench loaded task_001 (a real commit from git's history)
- The `simple-chat` DUT (Device Under Test) analyzed the task
- Claude generated code changes to solve the task
- The solution was cached for future use

### 4. Validate the Solution

Check if the generated code actually works:

```bash
# Validate by running compilation and tests
codegen-bench validate solution_task_001_seed_42.json --all

# Possible outcomes (all are valuable data):
# - Compilation: PASSED, Tests: PASSED (ideal but not guaranteed)
# - Compilation: PASSED, Tests: FAILED (common - some tests may fail)
# - Compilation: FAILED (LLM made syntax/semantic errors)
#
# Example successful output:
# Validating solution: solution_task_001_seed_42.json
# Created worktree at: /tmp/worktree_xyz
# Solution applied
# Compilation: PASSED
# Tests: PASSED
#   Passed: 1523, Failed: 0
# Cleaned up worktree
#
# Note: Failures are expected and useful for comparing DUT quality!
```

**What's happening?**
- BrownBench creates an isolated git worktree
- Applies your generated changes
- Runs the project's build and test suite
- Reports results
- Cleans up automatically

### 5. Run a Mini Tournament

Compare two different code generation approaches:

```bash
# Run a mini tournament: 2 DUTs × 3 tasks
codegen-bench tournament \
  --duts simple-chat,elaborate-prompt \
  --tasks task_001,task_002,task_003 \
  --seed 42 \
  --output results/my_first_tournament.json

# This will:
# 1. Generate solutions (6 total: 2 DUTs × 3 tasks)
# 2. Run pairwise comparisons across arenas
# 3. Compute TrueSkill ratings
# 4. Generate statistical reports
#
# Expected time: ~5-10 minutes
```

### 6. View Results

```bash
# Export results to readable formats
codegen-bench export results/my_first_tournament.json ./reports/

# Creates:
# - reports/tournament.json (complete data)
# - reports/leaderboard.csv (rankings)
# - reports/comparisons.csv (detailed judgments)
# - reports/leaderboard.tex (LaTeX table)
```

View the leaderboard:

```bash
cat reports/leaderboard.csv
```

Expected output:
```csv
approach,rating,rating_std,wins,losses,ties,win_rate,avg_cost_usd,avg_time_sec
elaborate-prompt,27.45,2.31,8,1,1,0.889,0.0523,15.2
simple-chat,22.78,2.45,1,8,1,0.111,0.0412,11.8
```

## Understanding the Results

### Leaderboard Metrics

- **rating**: TrueSkill rating (higher = better, starts at 25)
- **rating_std**: Uncertainty (lower = more confident)
- **win_rate**: Fraction of comparisons won
- **avg_cost_usd**: Average API cost per solution
- **avg_time_sec**: Average generation time

### Interpreting Ratings

- **Rating difference < 3**: Approaches are roughly equivalent
- **Rating difference 3-6**: Noticeable difference, but not decisive
- **Rating difference > 6**: Strong evidence of superiority

## Next Steps

### Try Different DUTs

```bash
# List available DUTs
python -c "from codegen_bench.dut.registry import DUTRegistry; print(DUTRegistry.list())"

# Compare different approaches
codegen-bench tournament --duts simple-chat,elaborate-prompt --tier 1
```

### Explore More Tasks

```bash
# List available tasks
ls tasks/core/

# View task details
cat tasks/core/task_005.yaml
```

### Run Larger Tournaments

```bash
# Tier 1: Quick eval (5 tasks, ~10 min, ~$2)
codegen-bench tournament --tier 1 --duts simple-chat,elaborate-prompt

# Tier 2: Standard eval (10 tasks, ~30 min, ~$10)
codegen-bench tournament --tier 2 --duts simple-chat,elaborate-prompt

# Tier 3: Full eval (21 tasks, ~2 hours, ~$50)
codegen-bench tournament --tier 3 --duts simple-chat,elaborate-prompt
```

### Customize DUT Configuration

Create a config file:

```yaml
# my_config.yaml
duts:
  simple-chat:
    model: claude-sonnet-4-20250514
    temperature: 0.1  # More deterministic
    max_tokens: 4000

  elaborate-prompt:
    model: claude-sonnet-4-20250514
    include_codebase_context: true
    max_context_files: 10  # Read more files
```

Run with custom config:

```bash
codegen-bench --config my_config.yaml tournament --tier 1
```

## Common Workflows

### Workflow 1: Test a New Prompting Strategy

```bash
# 1. Create new DUT class (see Architecture docs)
# 2. Register DUT
# 3. Generate solutions
codegen-bench generate --dut my-new-dut --task-id task_001 --seed 42

# 4. Validate manually
codegen-bench validate solution.json --all

# 5. Run mini tournament
codegen-bench tournament --duts my-new-dut,simple-chat --tier 1

# 6. Analyze results
codegen-bench export results.json ./reports/
```

### Workflow 2: Evaluate on Specific Domain

```bash
# Run tournament on specific project tasks (e.g., all git tasks)
codegen-bench tournament \
  --duts simple-chat,elaborate-prompt \
  --tasks task_001,task_010 \
  --output results/git_tasks.json
```

### Workflow 3: Cost-Conscious Development

```bash
# Start with smallest tier
codegen-bench tournament --tier 1 --duts my-dut

# If promising, scale up
codegen-bench tournament --tier 2 --duts my-dut

# Final validation
codegen-bench tournament --tier 3 --duts my-dut
```

## Tips & Best Practices

### Caching

Solutions are cached by default. This means:

```bash
# First run: Makes API call (~15s, costs money)
codegen-bench generate --dut simple-chat --task-id task_001 --seed 42

# Second run: Instant, free (uses cache)
codegen-bench generate --dut simple-chat --task-id task_001 --seed 42

# Force regeneration: Use --no-cache
codegen-bench generate --dut simple-chat --task-id task_001 --seed 42 --no-cache
```

**Cache location**: `~/.cache/codegen-bench/`

### Reproducibility

Always use seeds for reproducible results:

```bash
# Good: Reproducible
codegen-bench generate --dut simple-chat --task-id task_001 --seed 42

# Bad: Non-reproducible (LLM sampling variance)
codegen-bench generate --dut simple-chat --task-id task_001  # Random seed
```

### Cost Management

Monitor costs before large runs:

```bash
# Estimate cost for tier 1 (5 tasks × 2 DUTs = 10 solutions)
# Avg solution cost: ~$0.05
# Estimated total: ~$0.50

# Estimate cost for tier 3 (21 tasks × 2 DUTs = 42 solutions)
# Estimated total: ~$2.10
```

Budget-conscious tips:
- Start with tier 1
- Use cache aggressively
- Use smaller `max_tokens` in config
- Consider using cheaper models for prototyping

### Debugging

Run with verbose logging:

```bash
# -v: Info level
codegen-bench -v generate --dut simple-chat --task-id task_001 --seed 42

# -vv: Debug level
codegen-bench -vv generate --dut simple-chat --task-id task_001 --seed 42
```

Inspect cached solutions:

```bash
# Find cached solutions
ls ~/.cache/codegen-bench/solutions/

# View solution JSON
cat ~/.cache/codegen-bench/solutions/simple-chat_task_001_42.json | jq
```

## Troubleshooting

### "Task not found" Error

```bash
# Problem: Task file doesn't exist
# Solution: Verify task exists
ls tasks/core/task_001.yaml

# If missing, you may need to run task creation scripts
```

### "Codebase not found" Error

```bash
# Problem: Git submodule not initialized
# Solution: Initialize submodules
git submodule update --init --recursive
```

### "API key not found" Error

```bash
# Problem: ANTHROPIC_API_KEY not set
# Solution: Export API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Make it permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
```

### Tests Failing

```bash
# Problem: Tests fail during validation
# Solution: This is expected! Not all generated solutions are perfect.

# Check what failed:
codegen-bench validate solution.json --test  # See test output

# This is actually valuable data for comparing DUTs
```

## What's Next?

Now that you've run your first benchmark:

1. **Read the [CLI Reference](CLI_REFERENCE.md)** - Learn all available commands
2. **Check [Configuration Guide](CONFIGURATION.md)** - Customize DUT behavior
3. **See [Architecture Overview](ARCHITECTURE.md)** - Understand how it works
4. **Try [Adding a New DUT](ADDING_DUTS.md)** - Implement your own approach

## Getting Help

- **Documentation**: Check other guides in `docs/`
- **Issues**: [GitHub Issues](https://github.com/your-org/brownbench/issues)
- **Examples**: See `examples/` directory for sample configs
- **Tests**: Read `tests/` for usage examples

Happy benchmarking!
