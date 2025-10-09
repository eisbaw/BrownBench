# BrownBench: AI Code Generation Benchmark Suite

A statistically rigorous benchmark for evaluating AI-assisted code generation approaches in brownfield software projects.

## 📚 Documentation

**[View Full Documentation](docs/)** | [Quick Start](docs/QUICKSTART.md) | [Installation](docs/INSTALLATION.md) | [CLI Reference](docs/CLI_REFERENCE.md)

## 🚀 Features

- **Multi-arena evaluation**: Assess code across 6 quality dimensions (maintainability, architecture, surgical precision, testability, performance, safety)
- **AI-as-judge**: Use AI judges with consensus voting for scalable evaluation
- **Statistical rigor**: TrueSkill ratings, effect sizes, multiple comparison correction
- **Adaptive designs**: MAMS and sequential testing for cost-efficient evaluation
- **Reproducible**: Solution caching (with TTL), seed control, configuration versioning
- **Production-ready**: Budget enforcement, circuit breakers, comprehensive error handling

## 📦 Installation

```bash
# Using nix-shell (recommended)
nix-shell

# Or with uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## ⚡ Quick Start

```bash
# Initialize benchmark suite
codegen-bench init ./my-benchmark

# Run a quick tournament (Tier 1: ~10 min, ~$2)
codegen-bench tournament --duts simple-chat,elaborate-prompt --tier 1

# Estimate costs before running
codegen-bench estimate --duts 5 --tasks 20 --samples 3

# Export results
codegen-bench export results.json ./reports --format all
```

See the [Quick Start Guide](docs/QUICKSTART.md) for a detailed walkthrough.

## 🛠️ Development

```bash
# Run tests
just test

# Format and lint code
just fmt
just lint

# Type checking
just typecheck

# Run all checks
just check
```

## 📖 Documentation

- **Getting Started**
  - [Installation](docs/INSTALLATION.md)
  - [Quick Start](docs/QUICKSTART.md)
  - [CLI Reference](docs/CLI_REFERENCE.md)
  - [Configuration](docs/CONFIGURATION.md)

- **Core Concepts**
  - [Architecture](docs/ARCHITECTURE.md)
  - [Statistical Methods](docs/STATISTICS_GUIDE.md)
  - [Cost Estimation](docs/TOURNAMENT_COST_ESTIMATION.md)

- **Extending BrownBench**
  - [Adding DUTs](docs/ADDING_DUTS.md)
  - [Adding Arenas](docs/ADDING_ARENAS.md)
  - [Adding Judges](docs/ADDING_JUDGES.md)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and architectural principles.

## 📋 Project Status

BrownBench is actively maintained with:
- 21 benchmark tasks from 13 open-source projects
- 2 DUT implementations (SimpleChatDUT, ElaboratePromptDUT)
- 6 evaluation arenas
- Comprehensive statistical analysis toolkit
- ~95% test coverage

## 📄 License

MIT - See [LICENSE](LICENSE) file for details
