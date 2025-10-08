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

## Phase 4: Security & Robustness (Started)

### Budget Management ✅
- [x] BudgetEnforcer class
- [x] Per-DUT cost limits
- [x] Global tournament budget
- [x] Warnings at thresholds
- [x] Hard stops when exceeded
- [x] Thread-safe cost tracking
- [x] Budget unit tests (20 tests, 98% coverage)

**Summary:** Complete budget enforcement system with pre-flight checks and configurable limits.

### Container Isolation 📋
- [ ] ContainerIsolation class
- [ ] Build DUT container images
- [ ] Network restriction (API proxy only)
- [ ] Resource limits (CPU, memory)
- [ ] Read-only mounts
- [ ] Container cleanup after execution

### API Proxy 📋
- [ ] APIProxy server
- [ ] Temporary key generation
- [ ] Request forwarding with real key
- [ ] Cost tracking per DUT (integrated with BudgetEnforcer)
- [ ] API proxy integration tests

### DUT Auditing ✅
- [x] DUTAuditor class
- [x] Static analysis for dangerous patterns
- [x] Network access detection
- [x] Audit report generation
- [x] Integration with DUT loading
- [x] Unit tests for DUTAuditor (19 tests, 97% coverage)
- [x] Integration tests with DUTRegistry (7 tests, 95% coverage)

### Tournament Checkpointing ✅
- [x] CheckpointManager class
- [x] CheckpointState dataclass (immutable)
- [x] Atomic save operations
- [x] Progress tracking and resume support
- [x] Checkpoint unit tests (19 tests, 90% coverage)
- [x] Integrate checkpointing into TournamentRunner
- [x] Handle resume from checkpoint in tournament
- [x] Checkpointing integration tests (6 tests, basic functionality verified)
- [ ] Comprehensive error taxonomy
- [ ] Actionable error messages
- [ ] Retry strategies
- [ ] Graceful degradation
- [ ] Error reporting in results

## Phase 5: Usability & Polish

### Additional DUT and Judge Implementations 📋
- [ ] ClaudeCodeDUT - Use Claude Code as a code generation approach
  - [ ] Implement ClaudeCodeDUT class
  - [ ] Handle tool use and file operations
  - [ ] Capture generated code from Claude Code
  - [ ] Unit tests for ClaudeCodeDUT
  - [ ] Integration tests with real tasks
- [ ] ClaudeCodeJudge - Use Claude Code as a judge
  - [ ] Implement ClaudeCodeJudge class
  - [ ] Provide comparison context to Claude Code
  - [ ] Extract judgment from Claude Code output
  - [ ] Unit tests for ClaudeCodeJudge
  - [ ] Calibration testing with ground truth

### Visualization & Reporting 📋
- [ ] Jinja2 template for HTML output
- [ ] Interactive Plotly charts
- [ ] Sortable leaderboard tables
- [ ] Per-arena breakdowns
- [ ] Cost analysis charts
- [ ] Multi-objective optimization with pymoo
- [ ] Pareto frontier calculation
- [ ] Hypervolume metric
- [ ] Dominated solution identification
- [ ] Pareto visualization with Plotly
- [ ] Pareto frontier unit tests

### Export Formats 📋
- [ ] JSON exporter with schema
- [ ] CSV exporter for custom analysis
- [ ] LaTeX table generator
- [ ] Export CLI options

### Documentation 📋
- [ ] Installation guide
- [ ] Quickstart tutorial (5-min)
- [ ] CLI reference
- [ ] Configuration guide
- [ ] Troubleshooting guide
- [ ] Architecture overview
- [ ] Adding new DUTs guide (include ClaudeCodeDUT example)
- [ ] Adding new arenas guide
- [ ] Adding new judges guide (include ClaudeCodeJudge example)
- [ ] Contributing guidelines
- [ ] API reference (auto-generated)
- [ ] Explain rating systems
- [ ] Effect size interpretation
- [ ] Multiple testing rationale
- [ ] Adaptive design benefits
- [ ] References to literature

### Additional Tasks & Configs 📋
- [ ] Add 5 additional C/C++ tasks
- [ ] Add 5 additional Python tasks
- [ ] Document each task thoroughly
- [ ] Default tournament config
- [ ] Quick evaluation config
- [ ] Full research config
- [ ] Per-DUT example configs
- [ ] Document SimpleChatDUT
- [ ] Document ElaboratePromptDUT
- [ ] Document ClaudeCodeDUT (once implemented)
- [ ] Template for custom DUTs

### CLI/UX Improvements 📋
- [ ] Improve progress indicators
- [ ] Better error messages
- [ ] Consistent formatting
- [ ] Help text for all commands

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
- [ ] Add integration tests for new features
- [ ] Run test suite before all commits
- [ ] Fix flaky tests immediately
- [ ] Run ruff linter regularly
- [ ] Type check with mypy
- [ ] Review code for maintainability
- [ ] Refactor technical debt
- [ ] Use record/replay for development
- [ ] Monitor spending weekly
- [ ] Optimize prompts for token efficiency
- [ ] Budget reviews at phase boundaries
- [ ] Update docs with new features
- [ ] Fix outdated information
- [ ] Add examples as features stabilize
- [ ] Maintain changelog

## Technical Debt

- [ ] Async support for API calls (3-5x speedup potential)
- [x] Graceful shutdown handling (SIGINT/SIGTERM) ✅
- [ ] TournamentConfig dataclass for base_seed, consensus_threshold
- [ ] TrueSkill defaults to configuration
- [ ] Streaming approach for large tournaments
- [ ] Store solution IDs and load from cache on demand
- [ ] Troubleshooting guide for worktree issues
- [ ] Manual cleanup commands documentation
- [ ] Rate limiter: Consider bucket-based O(1) implementation
- [ ] Cache: Add lock-free concurrent write protection (currently uses atomic rename)
- [ ] Cache: Consider TTL/expiration for stale cache entries
- [ ] Worktree: Add retry logic for transient git failures
- [ ] Worktree: Document manual cleanup procedure in case of failures
- [ ] Tournament: Add checkpoint/resume functionality for long-running tournaments
- [ ] DUT: Add timeout protection for solve() method
- [ ] Judge: Add circuit breaker for repeated API failures
- [ ] Add tests for edge-case exception handlers in cache.py (lines 113-114, 120, 176-177, 192-194)
- [ ] Cache: Add size limits and LRU eviction (DEFER - major feature)
- [ ] Registry: Class-level state may cause issues in parallel testing - consider instance-based design
- [ ] Cache: No TTL/expiration mechanism - stale cache could accumulate indefinitely (DEFER - major feature)

## Missing Functionality

- [ ] No async support for concurrent API calls (3-5x speedup potential)
- [x] No graceful shutdown handling (SIGINT/SIGTERM signals) ✅
- [~] No checkpoint/resume for long-running tournaments (CheckpointManager done, integration pending)
- [ ] No timeout protection for DUT.solve() method
- [ ] No circuit breaker pattern for repeated API failures
- [ ] No metrics/observability for production deployments (DEFER - Phase 5+ feature)

## Documentation Gaps

- [ ] Worktree: No troubleshooting guide for manual cleanup
- [ ] Cache: No documentation on size limits or cache management (DEFER - pending cache size feature)
- [ ] RateLimiter: No explanation of bucket-based O(1) alternative
- [ ] Tournament: No guide on cost estimation for different scales (DEFER - Phase 5 documentation)

## Potential Bugs/Edge Cases

- [ ] Cache: No size limit enforcement - could fill disk (DEFER - major feature)
- [ ] RateLimiter: Potential thundering herd on rate limit reset (DEFER - edge case optimization)
- [ ] Worktree: No retry logic for transient git failures
- [ ] SimpleChatDUT: No request timeout configuration (DEFER - feature request)

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
