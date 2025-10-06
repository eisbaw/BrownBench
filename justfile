# justfile
# Task automation for codegen-bench

# Variables
python := ".venv/bin/python"
pytest := ".venv/bin/pytest"
# Use nix-provided tools to avoid dynamic linking issues on NixOS
ruff := `echo $PATH | tr ":" "\n" | grep -m1 ruff | xargs -I{} echo {}/ruff`
mypy := `echo $PATH | tr ":" "\n" | grep -m1 mypy | xargs -I{} echo {}/mypy`

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

# Release (tag and push)
release VERSION:
    git tag -a v{{VERSION}} -m "Release v{{VERSION}}"
    git push origin v{{VERSION}}
