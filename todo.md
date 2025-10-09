# BrownBench Todo

## Phase 1: Task Curation ✅ COMPLETE

### Infrastructure Setup ✅
- [x] Add 13 git submodules (git, redis, nginx, sqlite, curl, openssh, haproxy, tmux, jq, zstd, containerd, etcd, ripgrep)
- [x] Create commit analysis script (`scripts/analyze_commits.py`)
- [x] Create validation script (`scripts/validate_commit_tests.py`)
- [x] Create task creation script (`scripts/create_task_from_commit.py`)
- [x] Identify 390 candidate commits (50-500 LoC changes) - see `COMMIT_ANALYSIS_SUMMARY.md`
- [x] Document build requirements per project - see `docs/BUILD_TEST_COMMANDS.md`

### Task Creation ✅
- [x] Task 1-5: Original tasks (git, redis, nginx, sqlite, curl)
- [x] Task 6: zstd - Refactor timefn (200 LoC, medium)
- [x] Task 7: ripgrep - Parallel traversal fix (193 LoC, medium)
- [x] Task 8: jq - Non-integer indices (194 LoC, medium)
- [x] Task 9: Redis - Stream consumers (201 LoC, hard)
- [x] Task 10: git - Reflog subcommand (201 LoC, hard)
- [x] Task 11: nginx - ioctl FIONREAD (205 LoC, medium)
- [x] Task 12: sqlite - fts5 updates (197 LoC, medium)
- [x] Task 13: curl - SSL signature algorithms (205 LoC, medium)
- [x] Task 14: openssh - Move agent sockets (193 LoC, medium)
- [x] Task 15: containerd - Streaming proxy (200 LoC, medium)
- [x] Task 16: haproxy - Add strict-maxconn (201 LoC, medium)
- [x] Task 17: haproxy - httpclient htx data (195 LoC, medium)
- [x] Task 18: tmux - Typed arguments parser (201 LoC, medium)
- [x] Task 19: tmux - Tidy tparm wrappers (197 LoC, medium)
- [x] Task 20: etcd - Refactor IPv6 comparison (201 LoC, medium)
- [x] Task 21: etcd - Add downgrade request (198 LoC, medium)

### DUT Development ✅
- [x] ElaboratePromptDUT - Enhanced system prompt with brownfield focus
- [x] ElaboratePromptDUT - Codebase context reading functionality
- [x] ElaboratePromptDUT - Unit tests (15 tests, 94% coverage)

### Tournament Validation ✅
- [x] Run mini-tournament on 2 DUTs, 5 tasks
- [x] Validate tournament outputs (26/26 integration tests passing)
- [x] Fix bugs discovered in tournament (Mock response sequencing)
- [x] Document validation results - see `docs/MINI_TOURNAMENT_VALIDATION.md`
- [x] Document Phase 1 progress - see `docs/PHASE1_PROGRESS.md`

### Summary ✅
**Phase 1 Complete:** 21 high-quality tasks from 13 projects across 13 domains
- See `docs/PHASE1_PROGRESS.md` for full details
- Infrastructure validated with 26/26 integration tests passing
- Tournament module: 93% test coverage
- Ready for Phase 2: Statistical Rigor

## Phase 2: Statistical Rigor ✅ COMPLETE

### Core Statistical Foundations ✅
- [x] TrueSkillRating wrapper (100% coverage)
- [x] TrueSkill update mechanism
- [x] TrueSkill conservative estimate (mu - 2*sigma)
- [x] TrueSkill match quality prediction
- [x] TrueSkill unit tests (16 tests)
- [x] Mixed linear models with statsmodels (91% coverage)
- [x] ICC calculation
- [x] Variance components (approach, task, arena, residual)
- [x] Variance decomposition unit tests (18 tests)
- [x] FDR (Benjamini-Hochberg) correction (98% coverage)
- [x] Holm-Bonferroni correction
- [x] Dunnett's test for MAMS
- [x] Wrapper function for correction methods
- [x] Correction methods unit tests (24 tests)
- [x] Sample size calculation (94% coverage)
- [x] Power calculation for achieved samples
- [x] Minimum detectable effect calculation
- [x] Power analysis unit tests (30 tests)

**Summary:** 132/132 tests passing, 97% average coverage
See `docs/PHASE2_PROGRESS.md` for full details

### Sequential Testing & Adaptive Designs ✅
- [x] GroupSequentialDesign class (100% coverage)
- [x] O'Brien-Fleming boundaries
- [x] Interim analysis checkpoints
- [x] Early stopping logic (efficacy/futility)
- [x] Conditional power calculation
- [x] Sequential design unit tests (23 tests)
- [x] MAMS Phase 1: screening with cheap metrics (98% coverage)
- [x] MAMS Phase 2: full evaluation of selected DUTs
- [x] MAMS integration with Dunnett's test
- [x] MAMS end-to-end tests (21 tests)

### Optional Future Work 📋
- [ ] Integrate sequential testing into TournamentRunner (deferred)
- [ ] Checkpoint evaluation hooks (deferred)
- [ ] Early stop reporting utilities (deferred)
- [ ] Sequential tournament integration tests (deferred)
- [ ] Add 10 more tasks across domains (deferred to future phases)
- [ ] Validate test suites for new tasks (deferred)
- [ ] Update task set configurations (deferred)

## Phase 3: Judge Calibration (40% Complete)

### Calibration Metrics ✅
- [x] Agreement rate calculation
- [x] Fleiss' Kappa (inter-rater reliability)
- [x] Position bias detection (A vs B)
- [x] Confusion matrix analysis
- [x] Calibration report generation
- [x] Calibration metrics unit tests (29 tests, 99% coverage)

**Summary:** All statistical metrics for judge calibration implemented and tested.

### CLI Integration ✅
- [x] `codegen-bench calibrate` CLI command
- [x] Ground truth YAML format definition
- [x] Load ground truth file with validation
- [x] Generate calibration report
- [x] Calibration command integration tests (7 tests)
- [x] Simulation mode (85% agreement rate)
- [ ] Run judges on calibration set (requires judge implementation)

**Summary:** CLI command complete with ground truth format, validation, and simulation mode.

### Web Interface & Data Collection 📋
- [ ] Create web interface for comparisons
- [ ] Simple A/B comparison UI
- [ ] Response collection backend
- [ ] Authentication for participants
- [ ] Select 50-100 comparison pairs
- [ ] Ensure diverse difficulty levels
- [ ] Ensure multiple arenas covered
- [ ] Include edge cases
- [ ] Document selection criteria
- [ ] Recruit 10 mid-level programmers
- [ ] Set up payment system ($10 per comparison)
- [ ] Limit sessions to 30 minutes
- [ ] Rotate task order to prevent fatigue
- [ ] Length bias detection & correction
- [ ] Regression-based adjustment
- [ ] Bias reporting in results
- [ ] Identify disagreement patterns
- [ ] Find ambiguous criteria
- [ ] Document failure modes
- [ ] Update arena prompts based on findings
- [ ] Add clarifying examples to prompts
- [ ] Test revised prompts on calibration set
- [ ] Iterate until ≥85% agreement achieved
- [ ] Git tag each prompt version
- [ ] Record which prompt version used in judgments
- [ ] Changelog for prompt evolution

## Phase 4: Security & Robustness ✅ COMPLETE

### Budget Management ✅ DONE
- [x] DONE: BudgetEnforcer class
- [x] DONE: Per-DUT cost limits
- [x] DONE: Global tournament budget
- [x] DONE: Warnings at thresholds
- [x] DONE: Hard stops when exceeded
- [x] DONE: Thread-safe cost tracking
- [x] DONE: Budget unit tests (20 tests, 98% coverage)

**Summary:** Complete budget enforcement system with pre-flight checks and configurable limits.

### Container Isolation ✅ DONE
- [x] DONE: ContainerIsolation class
- [x] DONE: Build DUT container images
- [x] DONE: Network restriction (API proxy only)
- [x] DONE: Resource limits (CPU, memory)
- [x] DONE: Read-only mounts
- [x] DONE: Container cleanup after execution
- [x] DONE: Validation of mount paths
- [x] DONE: Immutable configuration dataclasses
- [x] DONE: Unit tests (33 tests, 78% coverage)
- [x] DONE: Docker file template and documentation

**Summary:** Complete Docker-based container isolation with resource limits, network restrictions, and comprehensive testing.

### API Proxy ✅ DONE
- [x] DONE: APIProxy server
- [x] DONE: Temporary key generation
- [x] DONE: Request forwarding with real key
- [x] DONE: Cost tracking per DUT (integrated with BudgetEnforcer)
- [x] DONE: API proxy integration tests (25 tests, 82% coverage)

**Summary:** Complete HTTP proxy server with temporary key management, request forwarding, and budget integration. All tests passing.

### DUT Auditing ✅ DONE
- [x] DONE: DUTAuditor class
- [x] DONE: Static analysis for dangerous patterns
- [x] DONE: Network access detection
- [x] DONE: Audit report generation
- [x] DONE: Integration with DUT loading
- [x] DONE: Unit tests for DUTAuditor (19 tests, 97% coverage)
- [x] DONE: Integration tests with DUTRegistry (7 tests, 95% coverage)

### Tournament Checkpointing ✅ DONE
- [x] DONE: CheckpointManager class
- [x] DONE: CheckpointState dataclass (immutable)
- [x] DONE: Atomic save operations
- [x] DONE: Progress tracking and resume support
- [x] DONE: Checkpoint unit tests (19 tests, 90% coverage)
- [x] DONE: Integrate checkpointing into TournamentRunner
- [x] DONE: Handle resume from checkpoint in tournament
- [x] DONE: Checkpointing integration tests (6 tests, basic functionality verified)
- [x] DONE: Comprehensive error taxonomy (with 8 categories, severity levels, retry hints)
- [x] DONE: Actionable error messages (get_actionable_message() with suggestions)
- [x] DONE: Retry strategies (SimpleChatDUT has retry with tenacity, exponential backoff)
- [x] DONE: Graceful degradation (tournament continues on DUT/judge failures, errors logged)
- [x] DONE: Error reporting in results (ErrorRecord tracking, included in TournamentResult)

## Phase 5: Usability & Polish

### Additional DUT and Judge Implementations 📋
- [x] SKIPPED: ClaudeCodeDUT - Not feasible (circular dependency, no non-interactive CLI mode)
  - [x] SKIPPED: Implement ClaudeCodeDUT class
  - [x] SKIPPED: Handle tool use and file operations
  - [x] SKIPPED: Capture generated code from Claude Code
  - [x] SKIPPED: Unit tests for ClaudeCodeDUT
  - [x] SKIPPED: Integration tests with real tasks
- [x] SKIPPED: ClaudeCodeJudge - Not feasible (same reasons as ClaudeCodeDUT)
  - [x] SKIPPED: Implement ClaudeCodeJudge class
  - [x] SKIPPED: Provide comparison context to Claude Code
  - [x] SKIPPED: Extract judgment from Claude Code output
  - [x] SKIPPED: Unit tests for ClaudeCodeJudge
  - [x] SKIPPED: Calibration testing with ground truth

### Visualization & Reporting ✅ DONE
- [x] DONE: Jinja2 template for HTML output
- [x] DONE: Interactive Plotly charts
- [x] DONE: Sortable leaderboard tables
- [x] DONE: Per-arena breakdowns
- [x] DONE: Cost analysis charts
- [x] DONE: Multi-objective optimization with pymoo
- [x] DONE: Pareto frontier calculation
- [x] DONE: Hypervolume metric
- [x] DONE: Dominated solution identification
- [x] DONE: Pareto visualization with Plotly
- [x] DONE: Pareto frontier unit tests
- [x] DONE: HTMLReporter class with comprehensive test suite (17 tests, 94% coverage)
- [x] DONE: Fixed Pareto reference point calculation for numerical stability

### Export Formats ✅ DONE
- [x] DONE: JSON exporter with schema
- [x] DONE: CSV exporter for custom analysis
- [x] DONE: LaTeX table generator
- [x] DONE: ExportConfig for customization
- [x] DONE: export_all_formats convenience function
- [x] DONE: Unit tests (22 tests, 98% coverage)
- [x] DONE: Export CLI options
- [x] DONE: TournamentResult.from_dict() method for deserialization

### Documentation ✅ DONE
- [x] DONE: Installation guide
- [x] DONE: Quickstart tutorial (5-min)
- [x] DONE: CLI reference
- [x] DONE: Configuration guide
- [x] DONE: Troubleshooting guide
- [x] DONE: Architecture overview
- [x] DONE: Adding new DUTs guide (include ClaudeCodeDUT example)
- [x] DONE: Adding new arenas guide
- [x] DONE: Adding new judges guide (include ClaudeCodeJudge example)
- [x] DONE: Contributing guidelines (with MPED architectural principles)
- [x] DONE: API reference (auto-generated)
- [x] DONE: Explain rating systems (STATISTICS_GUIDE.md)
- [x] DONE: Effect size interpretation (STATISTICS_GUIDE.md)
- [x] DONE: Multiple testing rationale (STATISTICS_GUIDE.md)
- [x] DONE: Adaptive design benefits (STATISTICS_GUIDE.md)
- [x] DONE: References to literature (STATISTICS_GUIDE.md)

### Additional Tasks & Configs 📋
- [x] DONE: Add 5 additional C/C++ tasks (task_022-026)
- [x] SKIPPED: Add 5 additional Python tasks (no Python projects in submodules)
- [x] DONE: Document each task thoroughly (docs/TASK_022-026_SUMMARY.md)
- [x] DONE: Default tournament config (examples/configs/default_tournament.py)
- [x] DONE: Quick evaluation config (examples/configs/quick_eval.py)
- [x] DONE: Full research config (examples/configs/full_research.py)
- [x] DONE: Per-DUT example configs (examples/configs/per_dut_simple_chat.py)
- [x] DONE: Document SimpleChatDUT (examples/duts/SIMPLE_CHAT_DUT.md)
- [x] DONE: Document ElaboratePromptDUT (examples/duts/ELABORATE_PROMPT_DUT.md)
- [x] SKIPPED: Document ClaudeCodeDUT (not feasible - circular dependency)
- [x] DONE: Template for custom DUTs (examples/duts/CUSTOM_DUT_TEMPLATE.py)

### CLI/UX Improvements ✅ DONE
- [x] DONE: Improve progress indicators (Rich progress bars in tournament command)
- [x] DONE: Better error messages (comprehensive, actionable error messages throughout)
- [x] DONE: Consistent formatting (standardized across all commands)
- [x] DONE: Help text for all commands (enhanced help text for all CLI commands)
- [x] DONE: Add tournament CLI command (comprehensive implementation with tier presets)

**Summary:** All CLI/UX improvements complete! Tournament command now has:
- Comprehensive help text and examples
- Rich progress indicators with spinner, bar, and time elapsed
- Tier-based presets (1=quick, 2=standard, 3=full)
- Arena registry for proper Arena instance lookup
- Judge orchestrator with proper type handling
- Graceful error handling with actionable messages
- Checkpoint and resume support
- Results export integration

## Phase 6: Validation & Publication

- [ ] Recruit 3-5 research groups
- [ ] Provide onboarding
- [ ] Collect feedback
- [ ] Fix critical issues
- [ ] Design comparison with human experts
- [ ] Select test cases
- [ ] Recruit expert evaluators
- [ ] Plan statistical analysis
- [ ] Collect expert judgments
- [ ] Run automated benchmarks
- [ ] Compare results
- [ ] Statistical analysis
- [ ] Agreement metrics
- [ ] Identify discrepancies
- [ ] Root cause analysis
- [ ] Document limitations
- [ ] Introduction & motivation
- [ ] Related work
- [ ] Methodology
- [ ] Results & validation
- [ ] Discussion & limitations
- [ ] Future work
- [ ] Leaderboard tables
- [ ] Pareto frontiers
- [ ] Statistical analyses
- [ ] Architecture diagrams
- [ ] Anonymize data if needed
- [ ] Package datasets
- [ ] Write data documentation
- [ ] Choose license (MIT/Apache 2.0)
- [ ] PyPI package publication
- [ ] GitHub public repository
- [ ] Documentation site (readthedocs)
- [ ] Announcement blog post
- [ ] Public leaderboard website
- [ ] Submission system
- [ ] Automated benchmarking
- [ ] Community moderation
- [ ] Submit to conference/arxiv
- [ ] Preprint release
- [ ] Social media announcement

## Ongoing

- [ ] Maintain >90% code coverage
- [x] DONE: Add integration tests for new features ✅
- [x] DONE: Run test suite before all commits (pre-commit hook added) ✅
- [ ] Fix flaky tests immediately
- [x] DONE: Run ruff linter regularly ✅
- [x] DONE: Type check with mypy ✅
- [ ] Review code for maintainability
- [ ] Refactor technical debt
- [ ] Use record/replay for development
- [ ] Monitor spending weekly
- [x] DONE: Optimize prompts for token efficiency (created OptimizedPromptDUT, OptimizedClaudeJudge, PromptOptimizer) ✅
- [ ] Budget reviews at phase boundaries
- [x] DONE: Update docs with new features ✅ (PricingConfig, DUTRegistry improvements documented)
- [x] DONE: Fix outdated information ✅ (checked and updated)
- [x] DONE: Add examples as features stabilize ✅ (added 3 new example files)
- [x] DONE: Maintain changelog ✅

## Technical Debt

- [ ] Async support for API calls (3-5x speedup potential - defer to Phase 7)
- [x] DONE: Graceful shutdown handling (SIGINT/SIGTERM) ✅
- [x] DONE: TournamentConfig dataclass for base_seed, checkpoint_interval ✅
- [x] DONE: TrueSkill defaults to configuration ✅
- [ ] Streaming approach for large tournaments
- [ ] Store solution IDs and load from cache on demand
- [x] DONE: Troubleshooting guide for worktree issues
- [x] DONE: Manual cleanup commands documentation
- [x] DONE: Rate limiter: Bucket-based O(1) implementation (BucketRateLimiter, MultiTierRateLimiter) ✅
- [x] DONE: Cache: Add lock-free concurrent write protection ✅ (uses atomic rename - documented)
- [ ] Cache: Consider TTL/expiration for stale cache entries
- [x] DONE: Worktree: Add retry logic for transient git failures ✅
- [x] DONE: Worktree: Document manual cleanup procedure in case of failures (duplicate - see line 369) ✅
- [x] DONE: Tournament: Add checkpoint/resume functionality for long-running tournaments ✅
- [x] DONE: DUT: Add timeout protection for solve() method ✅
- [x] DONE: Judge: Add circuit breaker for repeated API failures ✅
- [x] DONE: Add tests for edge-case exception handlers in cache.py (lines 113-114, 120, 176-177, 192-194) ✅
- [ ] Cache: Add size limits and LRU eviction (DEFER - major feature)
- [x] DONE: Registry: Class-level state may cause issues in parallel testing ✅ (refactored to support instance-based design)
- [ ] Cache: No TTL/expiration mechanism - stale cache could accumulate indefinitely (DEFER - major feature)

## Missing Functionality

- [ ] No async support for concurrent API calls (3-5x speedup potential)
- [x] No graceful shutdown handling (SIGINT/SIGTERM signals) ✅
- [x] DONE: No checkpoint/resume for long-running tournaments (CheckpointManager done, integration complete) ✅
- [x] DONE: No timeout protection for DUT.solve() method ✅
- [x] DONE: No circuit breaker pattern for repeated API failures ✅
- [ ] No metrics/observability for production deployments (DEFER - Phase 5+ feature)

## Documentation Gaps

- [x] DONE: Worktree: No troubleshooting guide for manual cleanup (now in TROUBLESHOOTING.md)
- [x] DONE: Cache: No documentation on size limits or cache management ✅
- [x] DONE: RateLimiter: No explanation of bucket-based O(1) alternative ✅
- [ ] Tournament: No guide on cost estimation for different scales (DEFER - Phase 5 documentation)

## Potential Bugs/Edge Cases

- [ ] Cache: No size limit enforcement - could fill disk (DEFER - major feature)
- [x] DONE: RateLimiter: Potential thundering herd on rate limit reset ✅ (documented in code)
- [x] DONE: Worktree: No retry logic for transient git failures ✅ (duplicate - see line 373)
- [x] DONE: SimpleChatDUT: Request timeout configuration ✅ (already implemented in base class, documented)

## Security/Safety

- [ ] Worktree: git commands use user-provided paths - validate/sanitize inputs (DEFER - needs input sanitization framework)
- [ ] API keys: No key rotation mechanism (DEFER - feature request)
- [ ] Rate limiting: No per-user quotas for shared deployments (DEFER - feature request)

## Milestones

- [ ] Week 7: Mini-tournament successful?
- [ ] Week 12: Adaptive designs work correctly?
- [ ] Week 15: Judges achieve ≥85% agreement?
- [ ] Week 17: Container isolation working?
- [ ] Week 22: Validation study shows statistical rigor?

## Success Criteria

- [ ] Judges ≥85% agreement with ground truth
- [ ] Test-retest reliability ≥85%
- [ ] Tier 2 tournament costs <$500
- [ ] Adaptive designs save 30-50% cost
- [ ] All statistical tests properly powered
- [ ] Pre-registered hypotheses
- [ ] Effect sizes with CIs reported
- [ ] FDR control maintained
- [ ] Reproducible results
- [ ] Open data & code
- [ ] ≥3 external research groups using it
- [ ] Community task contributions
- [ ] Paper accepted/published
- [ ] ≥100 GitHub stars
- [ ] Integration in ≥1 company pipeline

## Risk Mitigation

- [ ] API rate limits mapped and respected
- [ ] Fallback isolation strategy if Docker unavailable
- [ ] Alternative if judge calibration fails (<85% agreement)
- [ ] Budget buffer for unexpected API costs
- [ ] Backup plan if task creation takes too long
- [ ] Contingency if beta testers don't materialize
- [ ] Plan B if validation study shows major issues
