# BrownBench Troubleshooting Guide

Solutions to common issues and error messages.

## Table of Contents

- [Installation Issues](#installation-issues)
- [API and Authentication Errors](#api-and-authentication-errors)
- [Task and Codebase Errors](#task-and-codebase-errors)
- [Generation Errors](#generation-errors)
- [Validation Errors](#validation-errors)
- [Cache Issues](#cache-issues)
- [Performance Issues](#performance-issues)
- [Docker and Container Issues](#docker-and-container-issues)
- [Test Failures](#test-failures)
- [Getting More Help](#getting-more-help)

## Installation Issues

### Command Not Found: `codegen-bench`

**Error**:
```
bash: codegen-bench: command not found
```

**Causes & Solutions**:

1. **Virtual environment not activated**:
   ```bash
   # Check if venv is active (should see (.venv) in prompt)
   which python  # Should point to .venv/bin/python

   # Activate venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

2. **Package not installed**:
   ```bash
   # Install in editable mode
   pip install -e ".[dev]"

   # Verify installation
   pip list | grep codegen-bench
   ```

3. **Wrong Python environment**:
   ```bash
   # Check Python version
   python --version  # Should be 3.11+

   # If multiple Python versions, use specific one
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

### Import Errors

**Error**:
```
ModuleNotFoundError: No module named 'codegen_bench'
```

**Solutions**:

1. **Reinstall package**:
   ```bash
   pip uninstall codegen-bench
   pip install -e ".[dev]"
   ```

2. **Check PYTHONPATH**:
   ```bash
   # Should include project src directory
   echo $PYTHONPATH

   # If needed, add to PYTHONPATH
   export PYTHONPATH="/path/to/brownbench/src:$PYTHONPATH"
   ```

3. **Verify package structure**:
   ```bash
   # Should see src/codegen_bench/
   ls -la src/codegen_bench/
   ```

### Dependency Conflicts

**Error**:
```
ERROR: pip's dependency resolver does not currently take into account...
```

**Solutions**:

1. **Create fresh virtual environment**:
   ```bash
   # Remove old venv
   rm -rf .venv

   # Create new one
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

2. **Use uv for faster resolution**:
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Use uv instead
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```

## API and Authentication Errors

### API Key Not Found

**Error**:
```
DUTConfigError: ANTHROPIC_API_KEY not found in config or environment
```

**Solutions**:

1. **Set environment variable**:
   ```bash
   # Set for current session
   export ANTHROPIC_API_KEY="sk-ant-..."

   # Verify
   echo $ANTHROPIC_API_KEY
   ```

2. **Make persistent**:
   ```bash
   # Add to shell profile
   echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
   source ~/.bashrc

   # Or use .zshrc for zsh
   echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **Use config file**:
   ```yaml
   # config.yaml
   duts:
     simple-chat:
       api_key: sk-ant-...  # Not recommended (keep secrets out of git)
   ```

4. **Use .env file** (if supported):
   ```bash
   # Create .env file in project root
   echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

### API Rate Limit Exceeded

**Error**:
```
anthropic.RateLimitError: 429 - Rate limit exceeded
```

**Solutions**:

1. **Reduce request rate**:
   ```yaml
   # config.yaml
   duts:
     simple-chat:
       max_requests_per_minute: 30  # Lower from default 50
   ```

2. **Use parallel workers carefully**:
   ```python
   config = TournamentConfig(
       parallel_workers=2,  # Reduce from 4
       # ...
   )
   ```

3. **Add retry with backoff** (already implemented):
   - SimpleChatDUT automatically retries with exponential backoff
   - Wait 1-2 minutes and try again

4. **Upgrade API tier**:
   - Contact Anthropic for higher rate limits
   - Enterprise tiers have higher limits

### API Authentication Failed

**Error**:
```
anthropic.AuthenticationError: 401 - Invalid API key
```

**Solutions**:

1. **Verify API key format**:
   ```bash
   # Should start with "sk-ant-"
   echo $ANTHROPIC_API_KEY | grep "^sk-ant-"
   ```

2. **Check for extra whitespace**:
   ```bash
   # Trim whitespace
   export ANTHROPIC_API_KEY=$(echo $ANTHROPIC_API_KEY | tr -d '[:space:]')
   ```

3. **Get new API key**:
   - Visit https://console.anthropic.com/
   - Generate new API key
   - Update environment variable

## Task and Codebase Errors

### Task Not Found

**Error**:
```
FileNotFoundError: Task task_001 not found
```

**Solutions**:

1. **Check task file exists**:
   ```bash
   # Look for task file
   ls tasks/core/task_001.yaml

   # If missing, list available tasks
   ls tasks/core/
   ```

2. **Verify task ID format**:
   ```bash
   # Correct format: task_001, task_002, etc.
   codegen-bench generate --task-id task_001  # Correct
   codegen-bench generate --task-id task001   # Wrong (missing underscore)
   ```

3. **Initialize task set**:
   ```bash
   # If tasks directory is empty
   codegen-bench init --tasks core ./
   ```

### Codebase Not Found

**Error**:
```
Error: Codebase not found at /path/to/projects/git
```

**Solutions**:

1. **Initialize git submodules**:
   ```bash
   # Initialize all submodules
   git submodule update --init --recursive

   # Verify submodules
   ls projects/git/  # Should show git source code
   ```

2. **Check submodule status**:
   ```bash
   # Check which submodules are initialized
   git submodule status

   # Should see commits, not dashes
   # Bad:  -abc123... projects/git
   # Good: +abc123... projects/git (master)
   ```

3. **Manually clone missing project**:
   ```bash
   # If submodule is broken, clone manually
   cd projects/
   git clone https://github.com/git/git.git
   cd git
   git checkout <commit_hash>  # Use commit from task YAML
   ```

4. **Update task codebase path**:
   ```yaml
   # In task YAML file
   codebase_path: /absolute/path/to/projects/git
   ```

### Invalid Task YAML

**Error**:
```
yaml.YAMLError: mapping values are not allowed here
```

**Solutions**:

1. **Validate YAML syntax**:
   ```bash
   # Use Python to check
   python -c "import yaml; yaml.safe_load(open('tasks/core/task_001.yaml'))"

   # Or use yamllint
   pip install yamllint
   yamllint tasks/core/task_001.yaml
   ```

2. **Common YAML errors**:
   ```yaml
   # Wrong: Missing space after colon
   name:Add feature

   # Right: Space after colon
   name: Add feature

   # Wrong: Incorrect indentation
   constraints:
   - Must compile
     - Must pass tests

   # Right: Consistent indentation
   constraints:
     - Must compile
     - Must pass tests
   ```

## Generation Errors

### Solution Generation Timeout

**Error**:
```
TimeoutError: Solution generation exceeded 300 seconds
```

**Solutions**:

1. **Increase timeout**:
   ```python
   config = TournamentConfig(
       timeout_seconds=600,  # 10 minutes instead of 5
       # ...
   )
   ```

2. **Reduce max_tokens**:
   ```yaml
   duts:
     simple-chat:
       max_tokens: 4000  # Faster than 8000
   ```

3. **Check network connection**:
   ```bash
   # Test API connectivity
   curl https://api.anthropic.com/v1/messages -I
   ```

### Parsing Error

**Error**:
```
DUTParsingError: Failed to parse API response for task task_001
```

**Solutions**:

1. **Check response format**:
   - This usually means the LLM didn't follow the expected code block format
   - Try regenerating with `--no-cache`

2. **Inspect raw response** (for debugging):
   ```python
   # In SimpleChatDUT, add logging before parsing
   logger.debug("raw_response", response=response.content[0].text)
   ```

3. **Adjust prompt** (if custom DUT):
   - Ensure prompt clearly specifies code block format
   - Add examples in prompt

### Budget Exceeded

**Error**:
```
BudgetExceededError: Cost $12.50 exceeds limit of $10.00 for DUT simple-chat
```

**Solutions**:

1. **Increase budget limits**:
   ```python
   config = TournamentConfig(
       max_cost_per_dut=20.0,  # Increase from 10.0
       max_total_cost=100.0,
       # ...
   )
   ```

2. **Use cheaper model**:
   ```yaml
   duts:
     simple-chat:
       model: claude-sonnet-4-20250514  # Cheaper than opus
   ```

3. **Reduce token usage**:
   ```yaml
   duts:
     simple-chat:
       max_tokens: 4000  # Reduce from 8000
     elaborate-prompt:
       max_context_files: 3  # Reduce from 5
   ```

4. **Check actual costs**:
   ```bash
   # View solution costs
   cat ~/.cache/codegen-bench/solutions/simple-chat_task_001_42.json | \
     jq '.cost_usd'
   ```

## Validation Errors

### Worktree Creation Failed

**Error**:
```
WorktreeError: Failed to create git worktree
```

**Solutions**:

1. **Check git version**:
   ```bash
   # Need git 2.5+ for worktree support
   git --version

   # Upgrade if needed
   sudo apt update && sudo apt install git  # Ubuntu/Debian
   brew upgrade git                         # macOS
   ```

2. **Clean up stale worktrees**:
   ```bash
   # List worktrees
   cd projects/git
   git worktree list

   # Remove stale worktrees
   git worktree prune

   # Force remove if needed
   git worktree remove /tmp/worktree_xyz --force
   ```

3. **Check permissions**:
   ```bash
   # Ensure write permission to temp directory
   ls -la /tmp/

   # Try custom worktree location
   export TMPDIR="$HOME/tmp"
   mkdir -p $TMPDIR
   ```

4. **Repository state**:
   ```bash
   # Check for git issues
   cd projects/git
   git status

   # If corrupted, reinitialize
   cd ../..
   rm -rf projects/git
   git submodule update --init --recursive
   ```

### Compilation Failed

**Error**:
```
Compilation: FAILED
Error: make: *** [all] Error 2
```

**Solutions**:

This is often **expected behavior** - generated solutions may not always compile. However, if systematic:

1. **Check original codebase compiles**:
   ```bash
   cd projects/git
   make clean
   make

   # Should compile successfully
   ```

2. **Install build dependencies**:
   ```bash
   # For git
   sudo apt install build-essential libz-dev libssl-dev  # Ubuntu/Debian

   # For other projects, see docs/BUILD_TEST_COMMANDS.md
   ```

3. **Check solution changes**:
   ```bash
   # View what files were modified
   cat solution.json | jq '.changed_files | keys'

   # Inspect specific file
   cat solution.json | jq '.changed_files["src/main.c"]'
   ```

### Tests Failed

**Error**:
```
Tests: FAILED
Error: FAIL test_feature_x
```

**Solutions**:

This is also **expected** - comparing DUTs based on which pass tests.

1. **Verify baseline tests pass**:
   ```bash
   cd projects/git
   make test

   # Should pass on unmodified code
   ```

2. **View test output**:
   ```bash
   # Run validation with verbose output
   codegen-bench -vv validate solution.json --test
   ```

3. **Check specific test**:
   ```bash
   # Apply solution manually and debug
   cd /tmp/worktree_xyz
   make test TEST=test_feature_x
   ```

## Cache Issues

### Permission Denied

**Error**:
```
PermissionError: [Errno 13] Permission denied: '~/.cache/codegen-bench/...'
```

**Solutions**:

1. **Fix cache directory permissions**:
   ```bash
   # Check permissions
   ls -la ~/.cache/codegen-bench/

   # Fix permissions
   chmod -R 755 ~/.cache/codegen-bench/
   chown -R $USER ~/.cache/codegen-bench/
   ```

2. **Use custom cache directory**:
   ```bash
   # Set via environment
   export CODEGEN_BENCH_CACHE_DIR="$HOME/my-cache"
   mkdir -p $HOME/my-cache

   # Or via CLI flag
   codegen-bench --cache-dir $HOME/my-cache generate ...
   ```

### Cache Corruption

**Error**:
```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solutions**:

1. **Clear corrupted cache**:
   ```bash
   # Backup cache first
   cp -r ~/.cache/codegen-bench ~/.cache/codegen-bench.backup

   # Remove corrupted files
   rm ~/.cache/codegen-bench/solutions/*.json

   # Or clear entire cache
   rm -rf ~/.cache/codegen-bench/
   ```

2. **Regenerate solutions**:
   ```bash
   # Use --no-cache to regenerate
   codegen-bench generate --dut simple-chat --task-id task_001 --no-cache
   ```

### Cache Not Being Used

**Problem**: Solutions regenerate every time despite cache enabled.

**Solutions**:

1. **Verify cache is enabled**:
   ```bash
   # Check environment
   echo $CODEGEN_BENCH_NO_CACHE  # Should be empty

   # Check for --no-cache flag
   # Don't use --no-cache if you want caching
   ```

2. **Check cache key**:
   - Cache key = DUT metadata hash + task ID + seed
   - Changing DUT config invalidates cache
   - Changing prompt invalidates cache

3. **Verify cache directory**:
   ```bash
   # Check cache location
   ls ~/.cache/codegen-bench/solutions/

   # Should see cached solutions
   ```

## Performance Issues

### Slow Generation

**Problem**: Solution generation takes very long (>60 seconds).

**Solutions**:

1. **Check network latency**:
   ```bash
   # Test API latency
   time curl -X POST https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
   ```

2. **Reduce max_tokens**:
   ```yaml
   duts:
     simple-chat:
       max_tokens: 4000  # Faster than 8000
   ```

3. **Reduce context**:
   ```yaml
   duts:
     elaborate-prompt:
       max_context_files: 3  # Fewer files = faster
   ```

4. **Use faster model** (if available):
   ```yaml
   duts:
     simple-chat:
       model: claude-sonnet-4-20250514  # Faster than opus
   ```

### High Memory Usage

**Problem**: Process uses excessive memory (>8GB).

**Solutions**:

1. **Reduce parallel workers**:
   ```python
   config = TournamentConfig(
       parallel_workers=2,  # Reduce from 4
   )
   ```

2. **Clear cache periodically**:
   ```bash
   # During long tournaments
   rm ~/.cache/codegen-bench/solutions/*.json
   ```

3. **Monitor memory**:
   ```bash
   # Watch memory usage
   watch -n 1 'ps aux | grep codegen-bench'
   ```

## Docker and Container Issues

### Docker Not Found

**Error**:
```
docker: command not found
```

**Solutions**:

1. **Install Docker**:
   ```bash
   # Ubuntu/Debian
   sudo apt install docker.io
   sudo systemctl start docker
   sudo usermod -aG docker $USER  # Add user to docker group
   newgrp docker  # Refresh groups

   # macOS
   # Download and install Docker Desktop
   # https://www.docker.com/products/docker-desktop
   ```

2. **Verify Docker is running**:
   ```bash
   docker ps  # Should not error

   # Start Docker daemon if needed
   sudo systemctl start docker  # Linux
   ```

### Container Build Failed

**Error**:
```
ContainerError: Failed to build DUT container image
```

**Solutions**:

1. **Check Dockerfile**:
   ```bash
   # Verify Dockerfile exists
   ls Dockerfile.dut

   # Test build manually
   docker build -t test-dut -f Dockerfile.dut .
   ```

2. **Check Docker permissions**:
   ```bash
   # Run without sudo
   docker ps

   # If permission denied, add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **Clean Docker cache**:
   ```bash
   # Remove old images
   docker image prune -a

   # Rebuild from scratch
   docker build --no-cache -t dut-image -f Dockerfile.dut .
   ```

## Test Failures

### Unit Tests Failing

**Error**:
```
FAILED tests/unit/test_dut.py::test_simple_chat
```

**Solutions**:

1. **Install test dependencies**:
   ```bash
   pip install -e ".[dev]"  # Includes pytest, etc.
   ```

2. **Run specific test with verbose output**:
   ```bash
   pytest tests/unit/test_dut.py::test_simple_chat -vv
   ```

3. **Check for environment issues**:
   ```bash
   # Ensure API key is set for tests
   export ANTHROPIC_API_KEY="sk-ant-..."

   # Run tests
   pytest tests/unit/
   ```

4. **Check test mocks**:
   - Some tests use mocked API responses
   - Check mock data is valid

### Integration Tests Failing

**Error**:
```
FAILED tests/integration/test_tournament.py
```

**Solutions**:

1. **Initialize submodules**:
   ```bash
   git submodule update --init --recursive
   ```

2. **Check required services**:
   - Git must be available
   - Write access to /tmp

3. **Run with verbose logging**:
   ```bash
   pytest tests/integration/ -vv --log-cli-level=DEBUG
   ```

## Getting More Help

### Enable Debug Logging

```bash
# Maximum verbosity
codegen-bench -vv generate --dut simple-chat --task-id task_001

# Save debug log to file
codegen-bench -vv generate ... 2>&1 | tee debug.log
```

### Collect Diagnostic Info

```bash
#!/bin/bash
# diagnostic.sh - Collect debug information

echo "=== System Info ==="
uname -a
python --version
git --version

echo "=== BrownBench Installation ==="
pip show codegen-bench

echo "=== Environment Variables ==="
env | grep CODEGEN_BENCH
echo "API Key set: $([ -n "$ANTHROPIC_API_KEY" ] && echo YES || echo NO)"

echo "=== Cache Status ==="
ls -lah ~/.cache/codegen-bench/ 2>&1 || echo "Cache directory not found"

echo "=== Git Submodules ==="
git submodule status

echo "=== Recent Errors ==="
grep -i error ~/.cache/codegen-bench/logs/*.log 2>&1 || echo "No log files found"
```

Run with:
```bash
chmod +x diagnostic.sh
./diagnostic.sh > diagnostic_output.txt
```

### Report an Issue

When opening a GitHub issue, include:

1. **Error message** (full traceback)
2. **Command that failed** (exact command)
3. **Environment info**:
   - OS and version
   - Python version
   - BrownBench version
4. **Steps to reproduce**
5. **Diagnostic output** (from script above)
6. **Expected vs actual behavior**

**Template**:
```markdown
## Bug Report

### Description
Brief description of the issue

### Environment
- OS: Ubuntu 22.04
- Python: 3.11.5
- BrownBench: 0.1.0

### Steps to Reproduce
1. Run `codegen-bench generate --dut simple-chat --task-id task_001`
2. See error

### Expected Behavior
Solution should generate successfully

### Actual Behavior
Error: DUTConfigError: ANTHROPIC_API_KEY not found

### Full Error Output
```
[paste full error traceback]
```

### Additional Context
- API key is set in environment
- Other commands work fine
```

### Community Support

- **GitHub Issues**: https://github.com/your-org/brownbench/issues
- **GitHub Discussions**: https://github.com/your-org/brownbench/discussions
- **Documentation**: https://brownbench.readthedocs.io/

### Quick Diagnosis Checklist

Before asking for help, check:

- [ ] Virtual environment is activated
- [ ] BrownBench is installed (`pip list | grep codegen-bench`)
- [ ] API key is set (`echo $ANTHROPIC_API_KEY`)
- [ ] Task files exist (`ls tasks/core/`)
- [ ] Git submodules initialized (`git submodule status`)
- [ ] Tests pass (`pytest tests/unit/`)
- [ ] Cache directory is writable (`touch ~/.cache/codegen-bench/test`)
- [ ] Network connectivity (`curl -I https://api.anthropic.com`)

## See Also

- [Installation Guide](INSTALLATION.md) - Setup instructions
- [Quickstart Guide](QUICKSTART.md) - Basic usage
- [CLI Reference](CLI_REFERENCE.md) - All commands
- [Configuration Guide](CONFIGURATION.md) - Config options
