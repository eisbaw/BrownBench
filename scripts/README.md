# BrownBench Task Curation Scripts

This directory contains scripts for analyzing open-source repositories and creating benchmark tasks from real commits.

## Scripts

### 1. `analyze_commits.py`

Analyzes a git repository's commit history to find suitable candidates for benchmark tasks.

**Usage:**
```bash
python3 scripts/analyze_commits.py <repo_path> [--limit N] [--max-candidates M]
```

**Options:**
- `repo_path`: Path to git repository (required)
- `--limit N`: Maximum commits to analyze (default: 1000)
- `--max-candidates M`: Maximum candidates to return (default: 30)

**Criteria:**
- 50-500 lines of code changed (insertions + deletions)
- Modifies production code (not just tests/docs)
- Self-contained commits (not merges)
- Sorted by proximity to ideal size (200 LoC)

**Output:**
- Prints table of candidates to stdout
- Writes detailed report to `{repo_name}_candidates.txt`

**Example:**
```bash
# Analyze the git repository
python3 scripts/analyze_commits.py submodules/git --limit 2000 --max-candidates 30

# Analyze Redis with default limits
python3 scripts/analyze_commits.py submodules/redis
```

### 2. `validate_commit_tests.py`

Validates that a commit has passing tests both before and after the change. This is essential for creating benchmark tasks with known-good baselines.

**Usage:**
```bash
python3 scripts/validate_commit_tests.py <repo_path> <commit_sha> --test-cmd "command" [--build-cmd "command"]
```

**Options:**
- `repo_path`: Path to git repository (required)
- `commit_sha`: Commit SHA to validate (required)
- `--test-cmd`: Command to run tests (required)
- `--build-cmd`: Command to build project (optional)
- `--output`: Output file for JSON results (optional)

**What it does:**
1. Checks out the commit's parent
2. Runs build (if specified) and tests
3. Checks out the target commit
4. Runs build (if specified) and tests
5. Reports whether both pass

**Exit codes:**
- 0: Both parent and commit pass tests (suitable for benchmark)
- 1: One or both fail tests (not suitable)

**Example:**
```bash
# Validate a git commit
python3 scripts/validate_commit_tests.py \
    submodules/git \
    b55e113111 \
    --build-cmd "make" \
    --test-cmd "make test"

# Validate a Python project commit
python3 scripts/validate_commit_tests.py \
    submodules/redis \
    72e90695ec \
    --test-cmd "make test"
```

### 3. `create_task_from_commit.py`

Creates a benchmark task YAML file from a validated commit.

**Usage:**
```bash
python3 scripts/create_task_from_commit.py \
    <repo_path> <commit_sha> \
    --task-id <id> \
    --project-name <name> \
    --test-cmd "command" \
    [--build-cmd "command"] \
    [--difficulty easy|medium|hard] \
    [--domain <domain>] \
    [--output <path>]
```

**Options:**
- `repo_path`: Path to git repository (required)
- `commit_sha`: Commit SHA to create task from (required)
- `--task-id`: Task ID like "task_006" (required)
- `--project-name`: Project name like "git" or "redis" (required)
- `--test-cmd`: Test command (required)
- `--build-cmd`: Build command (optional)
- `--difficulty`: Task difficulty (default: medium)
- `--domain`: Task domain (default: refactoring)
- `--output`: Output path (default: tasks/core/{task_id}.yaml)

**Example:**
```bash
# Create task from git commit
python3 scripts/create_task_from_commit.py \
    submodules/git \
    b55e113111 \
    --task-id task_006 \
    --project-name git \
    --build-cmd "make" \
    --test-cmd "make test" \
    --difficulty medium \
    --domain refactoring

# Create task from Redis commit
python3 scripts/create_task_from_commit.py \
    submodules/redis \
    72e90695ec \
    --task-id task_007 \
    --project-name redis \
    --test-cmd "make test" \
    --difficulty hard \
    --domain "concurrent-data-structures"
```

## Workflow

### Phase 1: Discovery

1. **Clone repositories as submodules** (already done):
   ```bash
   git submodule add https://github.com/git/git.git submodules/git
   git submodule add https://github.com/redis/redis.git submodules/redis
   # ... etc
   ```

2. **Analyze commit history**:
   ```bash
   for repo in git redis nginx sqlite curl openssh haproxy tmux jq zstd containerd etcd ripgrep; do
       python3 scripts/analyze_commits.py submodules/$repo --limit 2000
   done
   ```

3. **Review candidate files**:
   - `git_candidates.txt`
   - `redis_candidates.txt`
   - etc.

### Phase 2: Validation

For each promising candidate:

1. **Check commit details**:
   ```bash
   cd submodules/git
   git show <commit_sha>
   ```

2. **Validate tests pass**:
   ```bash
   python3 scripts/validate_commit_tests.py \
       submodules/git <commit_sha> \
       --build-cmd "make" \
       --test-cmd "make test"
   ```

3. **If validation passes, create task**:
   ```bash
   python3 scripts/create_task_from_commit.py \
       submodules/git <commit_sha> \
       --task-id task_XXX \
       --project-name git \
       --build-cmd "make" \
       --test-cmd "make test"
   ```

### Phase 3: Task Refinement

1. Review generated `tasks/core/task_XXX.yaml`
2. Edit specification to be clearer/more specific
3. Test that the task loads correctly:
   ```bash
   python3 -c "from codegen_bench.core.task import Task; from pathlib import Path; t = Task.from_yaml(Path('tasks/core/task_XXX.yaml')); t.validate()"
   ```

## Repository-Specific Notes

### Git
- **Build:** `make`
- **Test:** `make test`
- **Language:** C
- **Good candidates:** Refactoring, data structures, memory management

### Redis
- **Build:** `make`
- **Test:** `make test` or `./runtest`
- **Language:** C
- **Good candidates:** Concurrent data structures, command implementations

### nginx
- **Build:** `./auto/configure && make`
- **Test:** `make test` (if available)
- **Language:** C
- **Good candidates:** Performance optimizations, protocol implementations

### SQLite
- **Build:** `./configure && make`
- **Test:** `make test`
- **Language:** C
- **Good candidates:** Query optimization, SQL parsing

### curl
- **Build:** `./buildconf && ./configure && make`
- **Test:** `make test`
- **Language:** C
- **Good candidates:** Protocol implementations, API changes

## Tips

1. **Start small**: Begin with 1-2 commits to get the workflow right
2. **Test manually first**: Before automating validation, manually verify a commit
3. **Document assumptions**: Note any special build/test requirements
4. **Check dependencies**: Ensure the commit doesn't require external dependencies
5. **Review context**: Read surrounding commits to understand the change fully

## Output Files

Generated by scripts:
- `*_candidates.txt`: Detailed commit analysis for each repository
- `COMMIT_ANALYSIS_SUMMARY.md`: Summary of all analyses
- `tasks/core/task_*.yaml`: Generated benchmark tasks

## Next Steps

See `COMMIT_ANALYSIS_SUMMARY.md` for recommended high-priority commits to validate and convert into tasks.
