# BrownBench CLI Reference

Complete reference for all `codegen-bench` commands and options.

## Table of Contents

- [Global Options](#global-options)
- [Commands](#commands)
  - [init](#init)
  - [generate](#generate)
  - [validate](#validate)
  - [tournament](#tournament)
  - [export](#export)
  - [calibrate](#calibrate)
- [Environment Variables](#environment-variables)
- [Exit Codes](#exit-codes)

## Global Options

These options are available for all commands:

```bash
codegen-bench [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### `--config`, `-c PATH`

Path to configuration file (YAML or JSON).

```bash
codegen-bench --config my_config.yaml generate ...
```

**Example config.yaml**:
```yaml
cache_dir: /custom/cache
log_level: DEBUG

duts:
  simple-chat:
    model: claude-sonnet-4-20250514
    temperature: 0.3
```

### `--verbose`, `-v`

Enable verbose logging. Can be specified multiple times for increased verbosity.

```bash
codegen-bench -v generate ...     # INFO level
codegen-bench -vv generate ...    # DEBUG level
```

**Logging levels**:
- Default: WARNING
- `-v`: INFO (shows progress, decisions)
- `-vv`: DEBUG (shows all details, API calls)

### `--quiet`, `-q`

Suppress all output except errors.

```bash
codegen-bench -q generate ...
```

Useful for:
- Scripting and automation
- CI/CD pipelines
- Cron jobs

### `--cache-dir PATH`

Override default cache directory.

```bash
codegen-bench --cache-dir /tmp/bench-cache generate ...
```

**Default**: `~/.cache/codegen-bench/`

## Commands

### init

Initialize a benchmark suite directory with tasks and project structure.

```bash
codegen-bench init [OPTIONS] OUTPUT_DIR
```

#### Arguments

- `OUTPUT_DIR` (required): Directory to initialize

#### Options

- `--tasks TEXT`: Task set to initialize (default: `core`)
  - Options: `core`, `extended`, `custom`
- `--download-projects`: Download reference project repositories

#### Examples

```bash
# Initialize with core task set
codegen-bench init ./my-benchmark

# Initialize and download projects
codegen-bench init --download-projects --tasks core ./my-benchmark
```

#### Output Structure

```
my-benchmark/
├── tasks/           # Task YAML files
│   ├── task_001.yaml
│   ├── task_002.yaml
│   └── ...
├── projects/        # Reference codebases (if --download-projects)
│   ├── git/
│   ├── redis/
│   └── ...
└── results/         # Tournament results (created on first run)
```

---

### generate

Generate a code solution for a specific task using a DUT (Device Under Test).

```bash
codegen-bench generate [OPTIONS]
```

#### Options

- `--dut TEXT` (required): Device under test approach ID
  - Built-in DUTs: `simple-chat`, `elaborate-prompt`
  - Custom DUTs: Register in `codegen_bench/dut/registry.py`

- `--task-id TEXT` (required): Task identifier (e.g., `task_001`)

- `--seed INTEGER`: Random seed for reproducibility (default: `42`)

- `--output`, `-o PATH`: Save solution to JSON file

- `--no-cache`: Force regeneration, ignore cached solutions

#### Examples

```bash
# Generate solution with default options
codegen-bench generate --dut simple-chat --task-id task_001

# Generate with custom seed and save to file
codegen-bench generate --dut simple-chat --task-id task_001 --seed 123 -o solution.json

# Force regeneration (ignore cache)
codegen-bench generate --dut elaborate-prompt --task-id task_005 --no-cache
```

#### Output

```
Generating solution with simple-chat
Task: Add .gitattributes support

Solution generated!
Files changed: 3
Tokens: 2,450
Cost: $0.0428
Time: 12.34s

Saved to: solution.json  (if --output specified)
```

#### Solution JSON Format

```json
{
  "approach_id": "simple-chat",
  "task_id": "task_001",
  "seed": 42,
  "timestamp": "2025-10-09T12:34:56.789Z",
  "changed_files": {
    "src/main.c": "int main() { ... }",
    "src/utils.c": "void helper() { ... }"
  },
  "generation_time_seconds": 12.34,
  "total_tokens": 2450,
  "prompt_tokens": 1200,
  "completion_tokens": 1250,
  "api_calls": 1,
  "cost_usd": 0.0428
}
```

---

### validate

Validate a generated solution by applying it to a worktree and running tests.

```bash
codegen-bench validate [OPTIONS] SOLUTION_FILE
```

#### Arguments

- `SOLUTION_FILE` (required): Path to solution JSON file

#### Options

- `--compile`: Run compilation command only
- `--test`: Run test command only
- `--all`: Run both compilation and tests (recommended)

#### Examples

```bash
# Validate solution (compile + test)
codegen-bench validate solution.json --all

# Only check compilation
codegen-bench validate solution.json --compile

# Only run tests
codegen-bench validate solution.json --test
```

#### Output

```
Validating solution: solution.json
Created worktree at: /tmp/worktree_abc123
Solution applied
Compilation: PASSED
Tests: PASSED
  Passed: 1523, Failed: 0
Cleaned up worktree
```

#### How It Works

1. Creates isolated git worktree from project repository
2. Applies code changes from solution
3. Runs compile command (if specified in task)
4. Runs test command (if specified in task)
5. Parses output for pass/fail metrics
6. Automatically cleans up worktree

#### Exit Codes

- `0`: Validation successful (compile + tests pass)
- `1`: Validation failed or error occurred

---

### tournament

Run a full tournament evaluation comparing multiple DUTs.

```bash
codegen-bench tournament [OPTIONS]
```

**Note**: This command is not yet fully implemented in the CLI. Use the Python API for now:

```python
from codegen_bench.tournament.runner import TournamentRunner
from codegen_bench.tournament.config import TournamentConfig

config = TournamentConfig(
    dut_ids=["simple-chat", "elaborate-prompt"],
    task_ids=["task_001", "task_002", "task_003"],
    base_seed=42,
    # ... other config
)

runner = TournamentRunner(config)
result = runner.run()
```

#### Planned Options

- `--duts TEXT`: Comma-separated list of DUT IDs
- `--tasks TEXT`: Comma-separated list of task IDs
- `--tier INTEGER`: Preset tier configuration (1, 2, 3)
- `--seed INTEGER`: Base random seed
- `--output`, `-o PATH`: Output file for results
- `--parallel INTEGER`: Number of parallel workers

#### Tier Configurations

- **Tier 1**: Quick eval (5 tasks, ~10 min, ~$2)
- **Tier 2**: Standard eval (10 tasks, ~30 min, ~$10)
- **Tier 3**: Full eval (21 tasks, ~2 hours, ~$50)

---

### export

Export tournament results to various output formats.

```bash
codegen-bench export [OPTIONS] TOURNAMENT_RESULT_FILE OUTPUT_DIR
```

#### Arguments

- `TOURNAMENT_RESULT_FILE` (required): Path to tournament result JSON
- `OUTPUT_DIR` (required): Directory for output files

#### Options

- `--format`, `-f FORMAT`: Output format(s) (can specify multiple)
  - Options: `json`, `csv`, `latex`, `all` (default: `all`)

- `--no-comparisons`: Exclude detailed comparison data from exports

- `--no-errors`: Exclude error records from exports

- `--decimal-places INTEGER`: Number of decimal places for numeric values (default: `4`)

#### Examples

```bash
# Export all formats
codegen-bench export results.json ./reports/

# Export specific formats
codegen-bench export results.json ./reports/ --format csv --format latex

# Export JSON only, exclude detailed comparisons
codegen-bench export results.json ./reports/ --format json --no-comparisons

# Export with 2 decimal places
codegen-bench export results.json ./reports/ --decimal-places 2
```

#### Output Files

When `--format all` or multiple formats specified:

```
reports/
├── tournament.json          # Complete tournament data (JSON)
├── leaderboard.csv          # Rankings and metrics (CSV)
├── comparisons.csv          # Detailed judgments (CSV, unless --no-comparisons)
├── errors.csv               # Error records (CSV, unless --no-errors)
├── leaderboard.tex          # Publication table (LaTeX)
└── summary.tex              # Summary statistics (LaTeX)
```

#### File Formats

**JSON** (`tournament.json`):
- Complete tournament data
- Can be reloaded for further analysis
- Includes all metadata, comparisons, ratings

**CSV** (`leaderboard.csv`):
```csv
approach,rating,rating_std,wins,losses,ties,win_rate,avg_cost_usd,avg_time_sec
elaborate-prompt,27.45,2.31,8,1,1,0.889,0.0523,15.2
simple-chat,22.78,2.45,1,8,1,0.111,0.0412,11.8
```

**CSV** (`comparisons.csv`):
```csv
comparison_id,task_id,arena,approach_a,approach_b,winner,confidence
cmp_001,task_001,maintainability,simple-chat,elaborate-prompt,B,high
cmp_002,task_001,architecture,simple-chat,elaborate-prompt,TIE,medium
```

**LaTeX** (`leaderboard.tex`):
```latex
\begin{table}[h]
\centering
\begin{tabular}{lrrrrr}
\toprule
Approach & Rating & $\pm$ & Wins & Losses & Win Rate \\
\midrule
elaborate-prompt & 27.45 & 2.31 & 8 & 1 & 0.889 \\
simple-chat & 22.78 & 2.45 & 1 & 8 & 0.111 \\
\bottomrule
\end{tabular}
\caption{Tournament Leaderboard}
\end{table}
```

---

### calibrate

Calibrate a judge against ground truth judgments.

```bash
codegen-bench calibrate [OPTIONS] GROUND_TRUTH_FILE
```

#### Arguments

- `GROUND_TRUTH_FILE` (required): Path to ground truth YAML file

#### Options

- `--judge TEXT`: Judge identifier to calibrate (default: `claude`)

- `--output`, `-o PATH`: Save calibration report to file

- `--verbose-report`: Include detailed comparison-by-comparison results

- `--simulate`: Use simulated judge decisions (for testing, 85% agreement rate)

#### Examples

```bash
# Calibrate with simulated decisions (for testing)
codegen-bench calibrate ground_truth.yaml --simulate

# Calibrate with verbose output
codegen-bench calibrate ground_truth.yaml --verbose-report --simulate

# Save calibration report
codegen-bench calibrate ground_truth.yaml --simulate -o calibration_report.txt
```

#### Ground Truth Format

```yaml
name: "Core Task Calibration Set"
version: "1.0"
description: "50 curated comparisons for judge calibration"
comparisons:
  - id: "gt_001"
    task_id: "task_001"
    arena: "maintainability"
    approach_a: "simple-chat"
    approach_b: "elaborate-prompt"
    solution_a: "solutions/simple-chat_task_001_42.json"
    solution_b: "solutions/elaborate-prompt_task_001_42.json"
    ground_truth: "B"  # A, B, or TIE
    rationale: "Approach B has better error handling and follows existing patterns"
```

#### Output

```
Calibrating judge: claude
Ground truth: ground_truth.yaml

Dataset: Core Task Calibration Set (v1.0)
Description: 50 curated comparisons for judge calibration
Comparisons: 50

Simulating judge decisions (85% agreement rate)...

Calibration Results:
============================================================
Judge: claude
Total Comparisons: 50
Agreement Rate: 84.0%

Fleiss' Kappa: 0.78 (Substantial agreement)

Position Bias:
  P(A wins | A in position A): 0.45
  P(B wins | B in position B): 0.42
  Bias Score: 0.03 (Negligible)

Confusion Matrix:
           Predicted
           A    B    TIE
Actual
A          8    2    1
B          1    16   2
TIE        2    1    17
```

**Interpretation**:
- **Agreement ≥85%**: Judge is well-calibrated
- **Fleiss' Kappa**:
  - `< 0.40`: Poor agreement
  - `0.40-0.60`: Moderate agreement
  - `0.60-0.80`: Substantial agreement
  - `> 0.80`: Nearly perfect agreement
- **Position Bias < 0.10**: Acceptable bias level

---

## Environment Variables

BrownBench respects these environment variables:

### `ANTHROPIC_API_KEY`

**Required**. API key for Anthropic's Claude models.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### `CODEGEN_BENCH_CACHE_DIR`

Override default cache directory.

```bash
export CODEGEN_BENCH_CACHE_DIR="/custom/cache/path"
```

**Default**: `~/.cache/codegen-bench/`

### `CODEGEN_BENCH_LOG_LEVEL`

Set logging level (overridden by `-v` flags).

```bash
export CODEGEN_BENCH_LOG_LEVEL="DEBUG"
```

**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`

### `CODEGEN_BENCH_CONFIG`

Default configuration file path.

```bash
export CODEGEN_BENCH_CONFIG="/path/to/config.yaml"
```

---

## Exit Codes

BrownBench uses standard exit codes:

- **0**: Success
- **1**: General error (task not found, API error, etc.)
- **2**: Usage error (missing required argument, invalid option)

### Examples

```bash
# Check if command succeeded
codegen-bench generate --dut simple-chat --task-id task_001
if [ $? -eq 0 ]; then
  echo "Success!"
fi

# Script with error handling
#!/bin/bash
set -e  # Exit on error

codegen-bench generate --dut simple-chat --task-id task_001
codegen-bench validate solution.json --all
codegen-bench export results.json ./reports/

echo "All steps completed successfully"
```

---

## Common Patterns

### Batch Generation

Generate solutions for multiple tasks:

```bash
#!/bin/bash
for task in task_001 task_002 task_003 task_004 task_005; do
  codegen-bench generate --dut simple-chat --task-id $task --seed 42
done
```

### Parallel Generation

Use GNU parallel for faster generation:

```bash
# Generate solutions in parallel (4 workers)
parallel -j 4 "codegen-bench generate --dut simple-chat --task-id {} --seed 42" \
  ::: task_001 task_002 task_003 task_004 task_005
```

### Validation Pipeline

Generate and validate in one pipeline:

```bash
#!/bin/bash
DUT="simple-chat"
TASK="task_001"
SEED=42

# Generate
codegen-bench generate --dut $DUT --task-id $TASK --seed $SEED -o solution.json

# Validate
if codegen-bench validate solution.json --all; then
  echo "✓ Solution valid"
else
  echo "✗ Solution failed validation"
  exit 1
fi
```

### Export All Results

Export results from multiple tournaments:

```bash
#!/bin/bash
for result_file in results/*.json; do
  base_name=$(basename "$result_file" .json)
  mkdir -p "reports/$base_name"
  codegen-bench export "$result_file" "reports/$base_name/" --format all
done
```

### Quiet Mode for Scripting

Run silently, check exit code:

```bash
#!/bin/bash
if codegen-bench -q generate --dut simple-chat --task-id task_001 --seed 42; then
  # Success - solution is cached
  echo "Solution ready"
else
  # Error occurred
  echo "Failed to generate solution" >&2
  exit 1
fi
```

---

## See Also

- [Quickstart Guide](QUICKSTART.md) - Get started quickly
- [Configuration Guide](CONFIGURATION.md) - Detailed config options
- [Architecture Overview](ARCHITECTURE.md) - How BrownBench works
- [Adding DUTs Guide](ADDING_DUTS.md) - Create custom approaches

---

## Getting Help

```bash
# Show help for any command
codegen-bench COMMAND --help

# Examples:
codegen-bench --help
codegen-bench generate --help
codegen-bench validate --help
```

For issues or questions:
- Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
- Open an issue on [GitHub](https://github.com/your-org/brownbench/issues)
