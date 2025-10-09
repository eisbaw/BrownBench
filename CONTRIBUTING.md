# Contributing to BrownBench

Thank you for your interest in contributing to BrownBench! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Code Standards](#code-standards)
5. [Testing Requirements](#testing-requirements)
6. [Documentation](#documentation)
7. [Pull Request Process](#pull-request-process)
8. [Types of Contributions](#types-of-contributions)
9. [Getting Help](#getting-help)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and respectful environment for all contributors. We expect all participants to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the project and community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, trolling, or discriminatory comments
- Publishing others' private information without permission
- Other conduct that could reasonably be considered inappropriate in a professional setting

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- (Optional) Nix for reproducible development environment
- (Optional) Docker for container isolation features

### Setting Up Your Development Environment

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/yourusername/brownbench.git
   cd brownbench
   ```

2. **Set up development environment** (choose one):

   **Option A: Using Nix (Recommended)**
   ```bash
   nix-shell
   ```

   **Option B: Using uv**
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```

   **Option C: Using pip**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Verify installation**:
   ```bash
   pytest
   just check
   ```

4. **Set up pre-commit hooks** (strongly recommended for fail-fast quality):
   ```bash
   pre-commit install
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation only changes
- `refactor/` - Code refactoring without functionality changes
- `test/` - Adding or updating tests
- `perf/` - Performance improvements

### 2. Make Your Changes

- Write clean, readable code following our [code standards](#code-standards)
- Add tests for new functionality (>90% coverage target)
- Update documentation as needed
- Keep commits focused and atomic

#### Starting New Features (Bottom-Up Development)

When implementing new functionality, follow this bottom-up approach:

1. **Proof of concept first**: Start with minimal code to validate the core idea works
2. **Fail fast**: If the concept is flawed, abandon it early before investing time
3. **Iterate**: Once core works, add error handling, logging, and tests
4. **Avoid premature optimization**: Make it work, then make it right, then make it fast (only after profiling)

### 3. Run Quality Checks

Before committing, run all checks:

```bash
# Run all checks (lint, typecheck, test)
just check

# Or individually:
just lint      # Run ruff linter
just typecheck # Run mypy type checker
just test      # Run pytest
```

### 4. Commit Your Changes

Follow conventional commit format:

```bash
git commit -m "feat: add new feature X"
git commit -m "fix: resolve issue with Y"
git commit -m "docs: update contributing guide"
git commit -m "test: add tests for Z"
```

Commit message prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/updates
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Build/tooling changes
- `style:` - Code style changes (formatting, etc.)

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Standards

### Python Style

- **PEP 8** compliance enforced by `ruff`
- **Type hints** required for all public functions and methods
- **Docstrings** required for all public classes and methods (Google style)
- **Line length**: 100 characters maximum

### Architectural Principles

BrownBench follows MPED (Mark Pedersen) architectural principles emphasizing fundamentals, composability, and proper data design. These principles guide all code contributions:

1. **Data design first**: Think about data layout, encoding, storage, caching, and access patterns before implementing algorithms. Consider read/write races and synchronization needs upfront.

2. **Fail-fast error handling**: Validate inputs early at boundaries, raise specific exceptions with actionable messages. Never silently swallow errors.

3. **Immutable data structures**: Prefer `@dataclass(frozen=True)` for data classes. Use mutable state only when absolutely necessary and document why.

4. **Single source of truth**: Maintain canonical state in one place. Compute derived views on-demand rather than storing them. Avoid caching derived state unless profiling proves it necessary.

5. **Composability**: Write small, focused functions that compose well. Each function should do one thing and do it well. Functions should be testable in isolation.

6. **Libraries over frameworks**: Use composable libraries that you control rather than frameworks that control you. Avoid framework lock-in and "magic" behavior.

7. **Explicit over implicit**: Use clear parameter names and explicit types. Avoid magic values, global state, or implicit behaviors. Code should be obvious, not clever.

8. **Readability over cleverness**: Clear variable names and straightforward logic beat clever one-liners. Only optimize performance after profiling shows bottlenecks.

9. **Security-first**: Validate and sanitize all external inputs. Treat user-provided paths, API responses, and configuration as untrusted. Design for safe failure modes.

10. **Idempotent operations**: Design operations to be safely retryable where possible. This improves reliability and simplifies error recovery.

### Example Code Style

```python
"""Module docstring explaining purpose."""

from typing import Any
from dataclasses import dataclass

import structlog

from codegen_bench.exceptions import ValidationError

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MyDataClass:
    """Brief description of this class.

    Attributes:
        field1: Description of field1
        field2: Description of field2
    """

    field1: str
    field2: int

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.field2 < 0:
            raise ValidationError(f"field2 must be non-negative, got {self.field2}")


def my_function(param1: str, param2: int) -> dict[str, Any]:
    """Brief description of function.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Dictionary containing result data

    Raises:
        ValidationError: If param2 is negative
    """
    if param2 < 0:
        raise ValidationError(f"param2 must be non-negative, got {param2}")

    # Use appropriate log levels:
    # - logger.debug() for detailed diagnostic info
    # - logger.info() for key state changes and progress
    # - logger.warning() for recoverable issues
    # - logger.error() for failures that need attention
    logger.info("processing", param1=param1, param2=param2)

    return {"result": param1 * param2}
```

## Testing Requirements

### Test Coverage

- **Target**: >90% code coverage
- **Required**: All new features must have tests
- **Test types**: Unit tests, integration tests where appropriate

### Writing Tests

1. **Test file location**: `tests/unit/test_<module>.py` or `tests/integration/test_<feature>.py`
2. **Test naming**: `test_<behavior>_<scenario>` - Focus on behaviors, not functions (e.g., `test_validation_fails_with_missing_api_key`)
3. **Use fixtures**: Create reusable fixtures in `conftest.py`
4. **Mock wisely**: Mock external dependencies (APIs, filesystem), but test real interactions between your own components when possible. Don't over-mock.

### Running Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=src/codegen_bench --cov-report=term-missing

# Specific test file
pytest tests/unit/test_arena.py

# Specific test
pytest tests/unit/test_arena.py::test_arena_initialization

# Watch mode (re-run on file changes)
pytest-watch
```

### Example Test

```python
"""Unit tests for my_module."""

import pytest
from codegen_bench.my_module import MyClass
from codegen_bench.exceptions import ValidationError


@pytest.fixture
def my_class_instance():
    """Fixture for MyClass instance."""
    return MyClass(config={"key": "value"})


def test_my_class_initialization():
    """Test MyClass initializes correctly."""
    instance = MyClass(config={"key": "value"})
    assert instance.config == {"key": "value"}


def test_my_class_invalid_config():
    """Test MyClass raises error with invalid config."""
    with pytest.raises(ValidationError, match="key is required"):
        MyClass(config={})


def test_my_class_method(my_class_instance):
    """Test my_method returns expected result."""
    result = my_class_instance.my_method("input")
    assert result == "expected output"
```

## Documentation

### Documentation Requirements

- **Docstrings**: All public classes, methods, and functions
- **Type hints**: All function signatures
- **Examples**: Include usage examples in docstrings for complex features
- **Updates**: Update relevant docs when changing functionality

### Documentation Files

- `README.md` - Project overview, quick start
- `docs/INSTALLATION.md` - Installation instructions
- `docs/QUICKSTART.md` - 5-minute tutorial
- `docs/ARCHITECTURE.md` - System design and architecture
- `docs/CLI_REFERENCE.md` - CLI command reference
- `docs/CONFIGURATION.md` - Configuration guide
- `docs/ADDING_DUTS.md` - Guide for adding new DUTs
- `docs/ADDING_ARENAS.md` - Guide for adding new arenas
- `docs/ADDING_JUDGES.md` - Guide for adding new judges
- `docs/TROUBLESHOOTING.md` - Common issues and solutions

### Docstring Style (Google Format)

```python
def function(arg1: str, arg2: int, optional: bool = False) -> dict[str, Any]:
    """Brief one-line description.

    More detailed description if needed. Can span multiple lines
    and include usage examples.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        optional: Description of optional parameter (default: False)

    Returns:
        Dictionary with keys 'key1' and 'key2' containing result data

    Raises:
        ValueError: If arg2 is negative
        ConfigError: If configuration is invalid

    Example:
        >>> result = function("test", 42)
        >>> result['key1']
        'expected value'
    """
```

## Pull Request Process

### Before Submitting

1. **Run all checks**: `just check` must pass
2. **Update tests**: Add/update tests for your changes
3. **Update docs**: Update relevant documentation
4. **Update CHANGELOG**: Add entry to CHANGELOG.md (if exists)
5. **Rebase on main**: `git rebase main` to ensure clean history

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement

## Related Issue
Fixes #<issue_number>

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing (`pytest`)
- [ ] Coverage >90% (`pytest --cov`)

## Quality Checks
- [ ] Linting passes (`just lint`)
- [ ] Type checking passes (`just typecheck`)
- [ ] All checks pass (`just check`)

## Documentation
- [ ] Docstrings added/updated
- [ ] Documentation files updated
- [ ] CHANGELOG updated (if applicable)

## Additional Notes
Any additional context, screenshots, or information.
```

### Review Process

1. **Automated checks**: GitHub Actions will run tests, linting, type checking
2. **Code review**: At least one maintainer will review your PR
3. **Feedback**: Address feedback and push updates
4. **Approval**: Once approved, a maintainer will merge your PR

### Review Criteria

- Code quality and style compliance
- Test coverage and test quality
- Documentation completeness
- No breaking changes (unless discussed)
- Performance considerations
- Security considerations

## Types of Contributions

### Adding New Tasks

See `docs/ADDING_TASKS.md` for detailed guide. Summary:

1. Identify suitable commit from supported project
2. Ensure 50-500 LoC change
3. Create task YAML file
4. Add test suite validation
5. Document task thoroughly

### Adding New DUTs (Code Generation Approaches)

See `docs/ADDING_DUTS.md` for detailed guide. Summary:

1. Subclass `CodeGenerationApproach`
2. Implement `solve()` and `get_metadata()`
3. Add configuration file
4. Write comprehensive tests (>90% coverage)
5. Document usage and configuration

### Adding New Arenas (Evaluation Criteria)

See `docs/ADDING_ARENAS.md` for detailed guide. Summary:

1. Subclass `Arena`
2. Implement `get_instructions()`
3. Define criteria and scoring rubric
4. Add example comparisons
5. Test with calibration set

### Adding New Judges

See `docs/ADDING_JUDGES.md` for detailed guide. Summary:

1. Subclass `Judge`
2. Implement `judge()` method
3. Add configuration
4. Calibrate against ground truth
5. Test for bias and reliability

### Documentation Improvements

- Fix typos or unclear explanations
- Add examples and tutorials
- Improve API documentation
- Add troubleshooting guides
- Create video tutorials

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the bug
2. **Reproduction steps**: Minimal steps to reproduce
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Environment**: Python version, OS, installation method
6. **Error messages**: Full error traceback if applicable
7. **Configuration**: Relevant config files (sanitize API keys!)

Use the bug report template in GitHub Issues.

### Feature Requests

When requesting features, include:

1. **Problem statement**: What problem does this solve?
2. **Proposed solution**: How should it work?
3. **Alternatives considered**: Other approaches considered
4. **Use cases**: Concrete examples of usage
5. **Impact**: Who benefits and how?

Use the feature request template in GitHub Issues.

## Project Structure

```
brownbench/
├── src/
│   └── codegen_bench/
│       ├── core/           # Core abstractions (Task, Solution, Arena)
│       ├── dut/            # DUT implementations
│       ├── judge/          # Judge implementations
│       ├── stats/          # Statistical analysis
│       ├── reporting/      # Results reporting
│       ├── security/       # Security features (isolation, auditing)
│       ├── validation/     # Solution validation
│       ├── checkpoint/     # Checkpointing support
│       ├── parsing/        # Code extraction
│       └── cli/            # CLI commands
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docs/                  # Documentation
├── configs/               # Configuration files
├── tasks/                 # Task definitions
└── submodules/           # Git submodules for task codebases
```

## Development Tools

### Just Commands

```bash
just test          # Run pytest
just lint          # Run ruff linter
just typecheck     # Run mypy
just check         # Run all checks
just format        # Format code with ruff
just clean         # Clean build artifacts
```

### Useful Development Commands

```bash
# Run specific test with output
pytest -v -s tests/unit/test_arena.py::test_specific_function

# Run with debugger on failure
pytest --pdb

# Generate coverage HTML report
pytest --cov=src/codegen_bench --cov-report=html
open htmlcov/index.html

# Watch mode (re-run tests on changes)
pytest-watch

# Type check specific file
mypy src/codegen_bench/core/arena.py

# Format specific file
ruff format src/codegen_bench/core/arena.py

# Lint with auto-fix
ruff check --fix src/
```

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag -a v1.2.3 -m "Release v1.2.3"`
4. Push tag: `git push origin v1.2.3`
5. GitHub Actions will build and publish to PyPI
6. Create GitHub Release with changelog

## Getting Help

- **Documentation**: Check `docs/` directory
- **GitHub Discussions**: Ask questions and discuss ideas
- **GitHub Issues**: Report bugs or request features
- **Email**: contact@brownbench.dev (if available)

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- GitHub Contributors page
- Release notes for significant contributions

## License

By contributing to BrownBench, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Your contributions make BrownBench better for everyone. We appreciate your time and effort!
