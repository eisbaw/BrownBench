# BrownBench Installation Guide

This guide covers all installation methods for BrownBench, from quick setup to development environments.

## Table of Contents

- [Quick Installation](#quick-installation)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Using Nix (Recommended)](#using-nix-recommended)
  - [Using uv](#using-uv)
  - [Using pip](#using-pip)
- [Verification](#verification)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Quick Installation

For most users, the fastest path is using Nix:

```bash
# Clone the repository
git clone https://github.com/your-org/brownbench.git
cd brownbench

# Enter development environment
nix-shell

# Verify installation
codegen-bench --help
```

## Prerequisites

### Required

- **Python 3.11 or newer** - BrownBench uses modern Python features
- **Git** - For version control and submodule management
- **API Keys**:
  - Anthropic API key (for Claude-based DUTs and judges)
  - Set as environment variable: `export ANTHROPIC_API_KEY=your_key_here`

### Optional

- **Docker** - For containerized DUT execution (security isolation)
- **Nix** - For reproducible development environments

### System Requirements

- **Operating System**: Linux, macOS, or Windows (WSL2)
- **Memory**: Minimum 4GB RAM (8GB recommended for tournament execution)
- **Disk Space**: ~500MB for installation, additional space for project submodules
- **Network**: Internet connection for API calls to LLM providers

## Installation Methods

### Using Nix (Recommended)

Nix provides the most reproducible and isolated environment.

#### Install Nix

If you don't have Nix installed:

```bash
# Install Nix (multi-user installation)
# Download installer first for security
curl -L https://nixos.org/nix/install -o /tmp/nix-install.sh

# Review the installer if desired
# less /tmp/nix-install.sh

# Run installer
sh /tmp/nix-install.sh --daemon

# Clean up
rm /tmp/nix-install.sh

# Restart shell
exec $SHELL
```

#### Setup Environment

```bash
# Navigate to project directory
cd brownbench

# Enter nix shell (first time will download dependencies)
nix-shell

# You're now in a development environment with all dependencies
```

The `shell.nix` file defines all dependencies including Python packages, system libraries, and development tools.

**Benefits of Nix:**
- Reproducible builds across machines
- Isolated environment (doesn't pollute system Python)
- All development tools pre-configured
- Easy to share with team members

### Using uv

`uv` is a fast Python package installer and virtual environment manager.

#### Install uv

```bash
# Install uv (if not already installed)
# Download installer first
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh

# Review if desired, then run
sh /tmp/uv-install.sh

# Clean up
rm /tmp/uv-install.sh

# Add to PATH (add to your shell rc file for persistence)
export PATH="$HOME/.cargo/bin:$PATH"
```

#### Setup Project

```bash
# Navigate to project directory
cd brownbench

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install BrownBench with development dependencies
uv pip install -e ".[dev]"
```

**Benefits of uv:**
- Much faster than pip (~10-100x speedup)
- Compatible with existing pip workflows
- Modern resolver algorithm
- Lightweight compared to Nix

### Using pip

Traditional pip installation works but is slower.

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip

# Install BrownBench with development dependencies
pip install -e ".[dev]"
```

## Verification

After installation, verify BrownBench is working:

### Check CLI Access

```bash
# Should display help text
codegen-bench --help

# Should show version info
codegen-bench --version
```

Expected output:
```
AI Code Generation Benchmark Suite.

Options:
  -c, --config PATH       Configuration file
  -v, --verbose           Verbose output (-vv for debug)
  -q, --quiet             Suppress output
  --cache-dir PATH        Cache directory
  --help                  Show this message and exit.

Commands:
  calibrate  Calibrate a judge against ground truth judgments.
  export     Export tournament results to various formats (JSON, CSV, LaTeX).
  generate   Generate solution for a task using specified DUT.
  init       Initialize benchmark suite.
  validate   Validate a solution by running compile/test commands.
```

### Run Tests

```bash
# Using just (if in nix-shell)
just test

# Or directly with pytest
pytest tests/

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
```

Expected: All tests should pass (100+ tests).

### Check API Access

```bash
# Verify API key is configured
echo $ANTHROPIC_API_KEY

# Should output your API key
```

If empty, set your API key:

```bash
# Add to shell profile (~/.bashrc, ~/.zshrc, etc.)
export ANTHROPIC_API_KEY="sk-ant-..."

# Or create .env file in project root
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

## Configuration

### Environment Variables

BrownBench respects these environment variables:

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."          # Anthropic API key

# Optional
export CODEGEN_BENCH_CACHE_DIR="$HOME/.cache/codegen-bench"  # Cache location
export CODEGEN_BENCH_LOG_LEVEL="INFO"          # Logging level (DEBUG, INFO, WARNING)
```

### Cache Directory

By default, BrownBench caches solutions in `~/.cache/codegen-bench/`.

To use a custom location:

```bash
# Via environment variable
export CODEGEN_BENCH_CACHE_DIR="/path/to/cache"

# Via CLI flag
codegen-bench --cache-dir /path/to/cache generate ...
```

### Configuration File

You can create a configuration file (YAML or JSON) for persistent settings:

```yaml
# config.yaml
cache_dir: /custom/cache
log_level: DEBUG

duts:
  simple-chat:
    model: claude-sonnet-4-20250514
    max_tokens: 8000
    temperature: 0.3

  elaborate-prompt:
    model: claude-sonnet-4-20250514
    include_codebase_context: true
    max_context_files: 5
```

Use with:

```bash
codegen-bench --config config.yaml generate ...
```

## Troubleshooting

### Command Not Found: codegen-bench

**Problem**: Shell can't find the `codegen-bench` command.

**Solutions**:
1. **Virtual environment not activated**:
   ```bash
   source .venv/bin/activate  # Activate venv first
   ```

2. **Installation incomplete**:
   ```bash
   pip install -e ".[dev]"  # Reinstall
   ```

3. **PATH issues**:
   ```bash
   # Find where it's installed
   which codegen-bench

   # Should be in .venv/bin/codegen-bench
   # If not found, check installation completed successfully
   ```

### Import Errors

**Problem**: `ModuleNotFoundError` or import failures.

**Solutions**:
1. **Reinstall dependencies**:
   ```bash
   pip install -e ".[dev]"  # Reinstall all deps
   ```

2. **Check Python version**:
   ```bash
   python --version  # Should be 3.11+
   ```

3. **Clear cache and reinstall**:
   ```bash
   pip cache purge
   pip install -e ".[dev]" --force-reinstall
   ```

### API Key Errors

**Problem**: `DUTConfigError: ANTHROPIC_API_KEY not found`

**Solutions**:
1. **Set environment variable**:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. **Verify key is set**:
   ```bash
   echo $ANTHROPIC_API_KEY  # Should print your key
   ```

3. **Add to shell profile** for persistence:
   ```bash
   echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
   source ~/.bashrc
   ```

### Nix Issues

**Problem**: Nix installation or shell issues.

**Solutions**:
1. **Nix daemon not running**:
   ```bash
   sudo systemctl start nix-daemon  # Linux
   ```

2. **Clear Nix cache**:
   ```bash
   nix-collect-garbage
   ```

3. **Rebuild shell**:
   ```bash
   nix-shell --pure  # Pure environment
   ```

### Permission Errors

**Problem**: Permission denied when writing to cache.

**Solutions**:
1. **Check cache directory permissions**:
   ```bash
   ls -la ~/.cache/codegen-bench/
   ```

2. **Create directory with correct permissions**:
   ```bash
   mkdir -p ~/.cache/codegen-bench
   chmod 755 ~/.cache/codegen-bench
   ```

3. **Use custom cache directory**:
   ```bash
   export CODEGEN_BENCH_CACHE_DIR="$HOME/my-cache"
   ```

### Test Failures

**Problem**: Tests failing after installation.

**Solutions**:
1. **Check test dependencies installed**:
   ```bash
   pip install -e ".[dev]"  # Includes test dependencies
   ```

2. **Run tests with verbose output**:
   ```bash
   pytest -v tests/  # See detailed failure info
   ```

3. **Run specific failing test**:
   ```bash
   pytest tests/unit/test_specific.py -v
   ```

## Next Steps

After successful installation:

1. Read the [Quickstart Guide](QUICKSTART.md) for your first benchmark run
2. Review the [CLI Reference](CLI_REFERENCE.md) for available commands
3. Check the [Configuration Guide](CONFIGURATION.md) for advanced settings
4. See [Contributing Guide](../CONTRIBUTING.md) if you want to contribute

## Getting Help

If you encounter issues not covered here:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Search [existing GitHub issues](https://github.com/your-org/brownbench/issues)
3. Open a [new issue](https://github.com/your-org/brownbench/issues/new) with:
   - Your operating system
   - Python version (`python --version`)
   - Installation method used
   - Full error message
   - Steps to reproduce
