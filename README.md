# BrownBench: AI Code Generation Benchmark Suite

A statistically rigorous benchmark for evaluating AI-assisted code generation approaches in brownfield software projects.

## Features

- **Multi-arena evaluation**: Assess code across 6 quality dimensions (maintainability, architecture, surgical precision, testability, performance, safety)
- **AI-as-judge**: Use AI judges with consensus voting for scalable evaluation
- **Statistical rigor**: TrueSkill ratings, effect sizes, multiple comparison correction
- **Adaptive designs**: MAMS and sequential testing for cost-efficient evaluation
- **Reproducible**: Solution caching, seed control, configuration versioning

## Installation

```bash
# Using nix-shell (recommended)
nix-shell

# Or with uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Quick Start

```bash
# Initialize benchmark
codegen-bench init --tasks=core ./benchmark

# Generate solutions
codegen-bench generate --dut=simple-chat --all-tasks

# Run tournament
codegen-bench tournament --duts=simple-chat,elaborate-prompt --tier=2

# View results
codegen-bench leaderboard ./results
```

## Development

```bash
# Run tests
just test

# Run linter
just lint

# Type check
just typecheck

# All checks
just check
```

## Project Status

This project is in early development (Phase 0: Foundations).

## License

MIT
