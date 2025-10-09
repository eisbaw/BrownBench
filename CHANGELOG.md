# Changelog

All notable changes to BrownBench will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- PricingConfig dataclass for centralized API pricing configuration
- Cache size limit documentation and management recommendations
- Thundering herd mitigation documentation for RateLimiter
- TrueSkillConfig dataclass for configurable rating system parameters
- O(1) rate limiter documentation explaining alternative implementations
- Comprehensive Phase 5 documentation (43 files, 35K+ lines)
  - ADDING_ARENAS.md, ADDING_DUTS.md, ADDING_JUDGES.md guides
  - API_REFERENCE.md and full HTML API documentation
  - ARCHITECTURE.md system overview
  - TASK_022-026_SUMMARY.md for additional C/C++ tasks
- Example configurations for tournaments
  - default_tournament.py, quick_eval.py, full_research.py
  - per_dut_simple_chat.py
- DUT templates and documentation
  - CUSTOM_DUT_TEMPLATE.py
  - ELABORATE_PROMPT_DUT.md, SIMPLE_CHAT_DUT.md
- Circuit breaker pattern implementation (utils/circuit_breaker.py)
- Timeout utilities with DUTTimeoutError (utils/timeout.py)
- HTML reporting with Jinja2 templates (reporting/html.py)
- Five additional C/C++ tasks (task_022-026)

### Fixed
- Exception handling to always show actionable suggestions
- DUTTimeoutError properly displaying retry suggestions
- Tournament checkpointing with checkpoint_interval parameter

### Changed
- SimpleChatDUT now uses PricingConfig from centralized configuration module
- TrueSkillRating now uses configurable TrueSkillConfig
- Exception messages improved for clarity and actionability

## [0.5.0] - 2025-01-09

### Added
- **Phase 5: Usability & Polish** - Complete
  - Interactive Plotly visualizations for tournament results
  - Pareto frontier calculation and visualization
  - HTMLReporter for comprehensive tournament reports
  - Export functionality (JSON, CSV, LaTeX)
  - Comprehensive documentation suite
  - Example configurations and templates

### Added
- **Phase 4: Security & Robustness** - Complete
  - BudgetEnforcer for API cost control
  - Docker container isolation for secure DUT execution
  - DUT auditing for security analysis
  - API proxy server with temporary key management
  - CheckpointManager for resumable tournaments
  - Graceful shutdown handler (SIGINT/SIGTERM)
  - Comprehensive error taxonomy with actionable messages

### Added
- **Phase 3: Judge Calibration** - 40% Complete
  - Agreement rate calculation
  - Fleiss' Kappa inter-rater reliability
  - Position bias detection
  - Confusion matrix analysis
  - CLI `calibrate` command with ground truth support
  - Simulation mode for testing

## [0.4.0] - 2025-01-08

### Added
- **Phase 2: Statistical Rigor** - Complete
  - TrueSkillRating system with uncertainty tracking
  - Mixed linear models with variance decomposition
  - Multiple testing correction methods (FDR, Holm-Bonferroni, Dunnett)
  - Power analysis and sample size calculation
  - Group sequential design for adaptive testing
  - MAMS (Multi-Arm Multi-Stage) design implementation

### Added
- **Phase 1: Task Curation** - Complete
  - 21 high-quality programming tasks from 13 open-source projects
  - ElaboratePromptDUT implementation with codebase context
  - Task validation infrastructure
  - Mini-tournament validation framework
  - Comprehensive test coverage (>90%)

## [0.3.0] - 2025-01-07

### Added
- Core tournament infrastructure
  - TournamentRunner with round-robin comparison
  - Arena system for quality dimensions
  - Judge orchestrator for consensus
  - Solution caching system
- SimpleChatDUT implementation
- ClaudeJudge implementation
- Basic CLI commands (generate, compare, tournament)
- Rate limiting for API calls
- Cost tracking and reporting

### Changed
- Refactored DUT interface for better extensibility
- Improved error handling throughout

### Fixed
- Mock response sequencing in tests
- Cache key generation issues
- Rate limiter race conditions

## [0.2.0] - 2025-01-06

### Added
- Initial project structure
- Base classes for DUTs, Judges, and Tasks
- YAML task loading
- Basic solution validation
- Git worktree management
- Initial test suite

## [0.1.0] - 2025-01-05

### Added
- Project inception
- Initial README and documentation
- Basic dependency management with poetry
- Nix shell configuration
- Pre-commit hooks setup

[Unreleased]: https://github.com/yourusername/brownbench/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/yourusername/brownbench/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/yourusername/brownbench/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/yourusername/brownbench/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yourusername/brownbench/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/brownbench/releases/tag/v0.1.0