# BrownBench Task Curation: Commit Analysis Summary

## Overview

This document summarizes the analysis of 13 open-source C/C++ and systems programming projects to identify suitable commits for creating benchmark tasks. The goal is to find 20-30 self-contained commits (50-500 LoC) that can serve as realistic code generation tasks.

## Analysis Methodology

**Criteria:**
- **Size:** 50-500 lines of code changed (insertions + deletions)
- **Scope:** Self-contained commits that modify production code
- **Quality:** Filtered out test-only, documentation-only, and merge commits
- **Preference:** Commits around 200 LoC (medium-sized refactorings or features)

**Repositories Analyzed:**
1. **git** - Version control system (C)
2. **Redis** - In-memory database (C)
3. **nginx** - Web server and reverse proxy (C)
4. **SQLite** - Embedded database (C)
5. **curl/libcurl** - Data transfer library (C)
6. **OpenSSH** - Secure shell implementation (C)
7. **HAProxy** - Load balancer (C)
8. **tmux** - Terminal multiplexer (C)
9. **jq** - JSON processor (C)
10. **zstd** - Compression library (C)
11. **containerd** - Container runtime (Go)
12. **etcd** - Distributed key-value store (Go)
13. **ripgrep** - Fast grep implementation (Rust)

## Results Summary

| Repository  | Candidates Found | Avg LoC | Language | Domain |
|-------------|------------------|---------|----------|--------|
| git         | 30              | ~200    | C        | VCS |
| Redis       | 30              | ~200    | C        | Database |
| nginx       | 30              | ~198    | C        | Web Server |
| SQLite      | 30              | ~202    | C        | Database |
| curl        | 30              | ~197    | C        | Network |
| OpenSSH     | 30              | ~198    | C        | Security |
| HAProxy     | 30              | ~197    | C        | Networking |
| tmux        | 30              | ~200    | C        | Terminal |
| jq          | 30              | ~200    | C        | Data Processing |
| zstd        | 30              | ~197    | C        | Compression |
| containerd  | 30              | ~197    | Go       | Container Runtime |
| etcd        | 30              | ~194    | Go       | Distributed Systems |
| ripgrep     | 30              | ~197    | Rust     | Text Search |
| **TOTAL**   | **390**         | ~198    | Mixed    | Multiple |

## Next Steps (From todo.md Phase 1)

### Immediate Tasks
1. ✅ Clone repositories as submodules
2. ✅ Analyze commit history
3. 🔲 Filter commits with passing tests before and after
4. 🔲 Manual review to ensure self-contained nature
5. 🔲 Select final 20-30 tasks across different domains:
   - **Task 1:** git - Memory management or data structure refactoring
   - **Task 2:** Redis - Concurrent data structure or command implementation
   - **Task 3:** nginx - Performance optimization or error handling
   - **Task 4:** SQLite - Query optimization or edge case bug fix
   - **Task 5:** curl/libcurl - Protocol implementation or API improvement
   - **Tasks 6-30:** Additional tasks from remaining repositories

### Task Creation Process
For each selected commit:
1. Extract commit specification from commit message
2. Identify codebase state before commit (git checkout parent)
3. Verify test suite passes on original code
4. Document build requirements
5. Document test execution commands
6. Create task YAML file following existing format
7. Validate task can be reproduced

### Priority Commits for Review

Based on commit messages and size, here are some high-priority candidates to review first:

#### Git (Memory/Data Structures)
- `b55e113111` (2025-01-12, 200 LoC): "gitk: adjust indentation to match the style used in this..."
- `7aa619c36f` (2025-08-06, 201 LoC): "builtin/reflog: implement subcommand to write new entries"
- `2b4648b919` (2025-07-15, 202 LoC): "refs: selectively set prefix in the seek functions"

#### Redis (Concurrent Structures)
- `72e90695ec` (2022-11-30, 201 LoC): "Stream consumers: Re-purpose seen-time, add active-time"
- `8234a5123d` (2022-08-22, 205 LoC): "Introduce connection layer framework"
- `95cbe879e5` (2024-05-22, 205 LoC): "sanitize dump payload for HFE"

#### nginx (Performance/Error Handling)
- `f9a7e7cc11` (2024-11-07, 197 LoC): "QUIC: CUBIC congestion control"
- `fac4c7bdf5` (2019-10-17, 205 LoC): "Events: available bytes calculation via ioctl(FIONREAD)"
- `5e31cdbb98` (2022-01-31, 192 LoC): "QUIC: introduced explicit stream states"

#### SQLite (Query Optimization)
- `0247e15f69` (2025-09-13, 191 LoC): "Updates to where.c to handle vtabs in joins more similarly"
- `ad8ec9db63` (2024-08-31, 210 LoC): "Avoid unnecessary sort operations when running one of the..."
- `bcd6d5d393` (2024-09-27, 197 LoC): "Allow UPDATEs of unindexed columns in fts5 contentless_un..."

#### curl (Protocol/API)
- `0d70dfb79b` (2025-06-17, 196 LoC): "xfer: manage pause bits"
- `a638828c88` (2025-04-02, 205 LoC): "TLS: add CURLOPT_SSL_SIGNATURE_ALGORITHMS and --sigalgs"
- `47b2300192` (2025-04-29, 206 LoC): "mqtt: use conn/easy meta hash"

## File Outputs

Individual candidate lists have been generated for each repository:
- `git_candidates.txt`
- `redis_candidates.txt`
- `nginx_candidates.txt`
- `sqlite_candidates.txt`
- `curl_candidates.txt`
- `openssh_candidates.txt`
- `haproxy_candidates.txt`
- `tmux_candidates.txt`
- `jq_candidates.txt`
- `zstd_candidates.txt`
- `containerd_candidates.txt`
- `etcd_candidates.txt`
- `ripgrep_candidates.txt`

Each file contains detailed information including:
- Full SHA
- Author and date
- Commit subject
- Lines added/deleted
- Files changed
- Size category

## Tools Created

- `scripts/analyze_commits.py`: Python script for automated commit analysis
  - Filters commits by size (50-500 LoC)
  - Excludes test/doc-only commits
  - Sorts by proximity to ideal size (200 LoC)
  - Generates detailed candidate reports

## Recommendations

1. **Start with C/C++ tasks:** Focus on git, Redis, nginx, SQLite, and curl first
2. **Diversity:** Select tasks from different domains (VCS, DB, network, security)
3. **Difficulty levels:** Mix of easy (100-150 LoC), medium (150-300 LoC), and hard (300-500 LoC)
4. **Test coverage:** Prioritize commits from projects with robust test suites
5. **Real-world value:** Focus on commits that fix actual bugs or add meaningful features

## Quality Assurance Notes

- All commits have been pre-filtered to exclude merges, docs, and test-only changes
- Actual test verification needs to be done manually (Phase 1 next step)
- Some commits may span multiple related files - review for true self-containment
- Consider git history context (was this part of a larger feature?)
