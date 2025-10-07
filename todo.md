# BrownBench Todo

## Phase 1: Task Curation (Current Priority)

- [ ] Add DUT: submodule clone and analyze git repository commit history
- [ ] Add DUT: submodule clone and analyze Redis repository commit history
- [ ] Add DUT: submodule clone and analyze nginx repository commit history
- [ ] Add DUT: submodule clone and analyze SQLite repository commit history
- [ ] Add DUT: submodule clone and analyze curl/libcurl repository commit history
- [ ] Add DUT: submodule clone and analyze OpenSSH repository commit history
- [ ] Add DUT: submodule clone and analyze HAProxy repository commit history
- [ ] Add DUT: submodule clone and analyze tmux repository commit history
- [ ] Add DUT: submodule clone and analyze jq repository commit history
- [ ] Add DUT: submodule clone and analyze zstd repository commit history
- [ ] Add DUT: submodule clone and analyze containerd repository commit history
- [ ] Add DUT: submodule clone and analyze etcd repository commit history
- [ ] Add DUT: submodule clone and analyze ripgrep repository commit history
- [ ] Identify 20-30 candidate commits (50-500 LoC changes)
- [ ] Filter commits with passing tests before and after
- [ ] Filter commits that are self-contained
- [ ] Task 1: git - Memory management or data structure refactoring
- [ ] Task 2: Redis - Concurrent data structure or command implementation
- [ ] Task 3: nginx - Performance optimization or error handling
- [ ] Task 4: SQLite - Query optimization or edge case bug fix
- [ ] Task 5: curl/libcurl - Protocol implementation or API improvement
- [ ] Write task specifications from commit messages
- [ ] Validate test suites pass on original code
- [ ] Document build requirements per task
- [ ] Document test execution per task
- [ ] ElaboratePromptDUT - Enhanced system prompt
- [ ] ElaboratePromptDUT - Codebase analysis integration
- [ ] ElaboratePromptDUT - Unit tests
- [ ] Run mini-tournament on 2 DUTs, 5 tasks
- [ ] Validate tournament outputs
- [ ] Fix bugs discovered in tournament
- [ ] Document edge cases from tournament
- [x] Retry logic with tenacity
- [x] Rate limiting implementation
- [x] Prompt versioning with SHA-256

## Phase 2: Statistical Rigor

- [ ] TrueSkillRating wrapper
- [ ] TrueSkill update mechanism
- [ ] TrueSkill conservative estimate (mu - 2*sigma)
- [ ] TrueSkill match quality prediction
- [ ] TrueSkill unit tests
- [ ] Mixed linear models with statsmodels
- [ ] ICC calculation
- [ ] Variance components (approach, task, arena, residual)
- [ ] Variance decomposition unit tests
- [ ] FDR (Benjamini-Hochberg) correction
- [ ] Holm-Bonferroni correction
- [ ] Dunnett's test for MAMS
- [ ] Wrapper function for correction methods
- [ ] Correction methods unit tests
- [ ] Sample size calculation
- [ ] Power calculation for achieved samples
- [ ] Minimum detectable effect calculation
- [ ] Power analysis unit tests
- [ ] GroupSequentialDesign class
- [ ] O'Brien-Fleming boundaries
- [ ] Interim analysis checkpoints
- [ ] Early stopping logic (efficacy/futility)
- [ ] Conditional power calculation
- [ ] Sequential design unit tests
- [ ] Integrate sequential testing into TournamentRunner
- [ ] Checkpoint evaluation
- [ ] Early stop reporting
- [ ] Sequential tournament integration tests
- [ ] MAMS Phase 1: screening with cheap metrics
- [ ] MAMS Phase 2: full evaluation of selected DUTs
- [ ] MAMS integration with sequential testing
- [ ] MAMS end-to-end test
- [ ] Add 10 more tasks across domains
- [ ] Validate test suites for new tasks
- [ ] Update task set configurations

## Phase 3: Judge Calibration

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
- [ ] Agreement rate with ground truth metric
- [ ] Fleiss' Kappa (inter-rater reliability)
- [ ] Per-judge accuracy tracking
- [ ] Confusion matrix analysis
- [ ] Calibration metrics unit tests
- [ ] Position bias measurement (A vs B)
- [ ] Length bias detection & correction
- [ ] Regression-based adjustment
- [ ] Bias reporting in results
- [ ] `codegen-bench calibrate` CLI command
- [ ] Load ground truth file
- [ ] Run judges on calibration set
- [ ] Generate calibration report
- [ ] Calibration command integration tests
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

## Phase 4: Security & Robustness

- [ ] ContainerIsolation class
- [ ] Build DUT container images
- [ ] Network restriction (API proxy only)
- [ ] Resource limits (CPU, memory)
- [ ] Read-only mounts
- [ ] Container cleanup after execution
- [ ] APIProxy server
- [ ] Temporary key generation
- [ ] Request forwarding with real key
- [ ] Cost tracking per DUT
- [ ] Budget enforcement
- [ ] API proxy integration tests
- [ ] DUTAuditor class
- [ ] Static analysis for dangerous patterns
- [ ] Network access detection
- [ ] Audit report generation
- [ ] Integration with DUT loading
- [ ] TournamentCheckpoint class
- [ ] Serialize tournament state to disk
- [ ] Resume from checkpoint
- [ ] Handle partial results
- [ ] Checkpointing integration tests
- [ ] BudgetEnforcer class
- [ ] Per-DUT cost limits
- [ ] Global tournament budget
- [ ] Warnings at thresholds
- [ ] Hard stops when exceeded
- [ ] Comprehensive error taxonomy
- [ ] Actionable error messages
- [ ] Retry strategies
- [ ] Graceful degradation
- [ ] Error reporting in results

## Phase 5: Usability & Polish

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
- [ ] JSON exporter with schema
- [ ] CSV exporter for custom analysis
- [ ] LaTeX table generator
- [ ] Export CLI options
- [ ] Installation guide
- [ ] Quickstart tutorial (5-min)
- [ ] CLI reference
- [ ] Configuration guide
- [ ] Troubleshooting guide
- [ ] Architecture overview
- [ ] Adding new DUTs guide
- [ ] Adding new arenas guide
- [ ] Contributing guidelines
- [ ] API reference (auto-generated)
- [ ] Explain rating systems
- [ ] Effect size interpretation
- [ ] Multiple testing rationale
- [ ] Adaptive design benefits
- [ ] References to literature
- [ ] Add 5 additional C/C++ tasks
- [ ] Add 5 additional Python tasks
- [ ] Document each task thoroughly
- [ ] Default tournament config
- [ ] Quick evaluation config
- [ ] Full research config
- [ ] Per-DUT example configs
- [ ] Document SimpleChatDUT
- [ ] Document ElaboratePromptDUT
- [ ] Template for custom DUTs
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
- [x] Rate limiting implementation
- [ ] Graceful shutdown handling (SIGINT/SIGTERM)
- [ ] TournamentConfig dataclass for base_seed, consensus_threshold
- [ ] TrueSkill defaults to configuration
- [ ] Streaming approach for large tournaments
- [ ] Store solution IDs and load from cache on demand
- [ ] Troubleshooting guide for worktree issues
- [ ] Manual cleanup commands documentation
- [x] Rate limiter: Single-lock design for atomic acquire() operations
- [x] Rate limiter: Add release() method for failed request idempotency
- [ ] Rate limiter: Consider bucket-based O(1) implementation
- [x] Rate limiter: Add observability logging when limits hit

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
