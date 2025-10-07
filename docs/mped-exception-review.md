# MPED Architecture Review: Exception Hierarchy and Validation

## Overview
Reviewed commits dd3dc08 and 0ebd230 which introduced domain-specific exception hierarchy and command validation.

## 1. Fail-Fast and Verbose Error Handling

### What's Good

**Strong domain-specific exception hierarchy:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/exceptions.py` defines clear exception types with semantic meaning
- Base exception `BrownBenchError` provides single catch point for all library errors
- Domain exceptions: `WorktreeError`, `DUTError`, `ValidationError`, `TaskError`, `CacheError`, `JudgeError`, `TournamentError`
- Follows fail-fast principle - errors are raised immediately when problems occur

**Excellent contextual error messages:**
- WorktreeError: `f"Failed to create worktree at {temp_dir}: {result.stderr}"`
- WorktreeError: `f"Worktree creation timed out after 30s: {e}"`
- ValidationError: `f"Failed to write file {rel_path}: {e}"`
- All include relevant context (paths, timeouts, stderr output)

**Good exception chaining:**
- Uses `from e` consistently to preserve stack traces
- Example: `raise WorktreeError(...) from e`
- Maintains debugging information through exception chain

**Structured logging integrated with exceptions:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/core/task.py` logs validation failures before returning False
- Includes task_id, command, and error details in structured format
- Good separation: logging for observability, exceptions for control flow

### What Could Be Improved

**Silent failure in worktree.py line 187:**
```python
except RuntimeError:
    # If git worktree remove fails, try manual cleanup
    shutil.rmtree(worktree_path, ignore_errors=True)
```
- Catches generic `RuntimeError` instead of `WorktreeError`
- `ignore_errors=True` silently swallows cleanup failures
- Should log cleanup failure at WARNING level minimum
- **Violation**: Silent failures are not acceptable per MPED principles

**Task validation returns boolean instead of raising:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/core/task.py:61` - `validate()` returns True/False
- Logs errors but doesn't raise exceptions
- Callers must check return value and decide what to do
- **Better approach**: Raise `TaskError` with accumulated validation failures
- This would eliminate the need for callers to check and raise separately (see line 46, 81 in loader.py)

**Missing error context in some ValueError exceptions:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/stats/variance.py:88` - `raise ValueError("Data must not be empty")`
- Missing context: what operation failed? what data was expected?
- Should be: `raise ValueError("Variance analysis requires non-empty dataset")`
- These statistical modules might need their own `StatsError` exception type

**ClaudeJudge raises generic ValueError:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/judge/claude_judge.py:61,166,181`
- Should raise `JudgeError` instead
- Example: `raise JudgeError("ANTHROPIC_API_KEY not found in environment")`

## 2. Exception Hierarchy Design

### What's Good

**Clean single-inheritance structure:**
```
Exception
  └─ BrownBenchError (base)
      ├─ WorktreeError
      ├─ DUTError
      ├─ ValidationError
      ├─ TaskError
      ├─ CacheError
      ├─ JudgeError
      └─ TournamentError
```
- Simple, flat hierarchy
- Each exception maps to a clear domain concept
- Easy to catch specific errors or all library errors

**Well-chosen exception names:**
- Descriptive and unambiguous
- Follow Python naming conventions
- Clear semantic meaning from name alone

**Good docstrings:**
- Each exception has clear purpose statement
- Examples: "Raised when git worktree operations fail"

### What Could Be Improved

**No custom attributes on exceptions:**
- Exceptions are just empty classes
- Could carry structured error details
- Example for ValidationError:
  ```python
  class ValidationError(BrownBenchError):
      """Raised when solution validation fails."""
      def __init__(self, message: str, file_path: Path | None = None,
                   operation: str | None = None):
          super().__init__(message)
          self.file_path = file_path
          self.operation = operation
  ```
- Benefits: Programmatic access to error details, better error recovery

**Missing exception for executor/subprocess operations:**
- Executor returns `ValidationResult` with error fields instead of raising
- Pattern mismatch: validation layer uses exceptions, executor uses result objects
- Consider: Should `_run_command` raise `ValidationError` on failure?
- Trade-off: Result objects allow partial success inspection, exceptions force handling

**TaskError and ValidationError overlap:**
- Task validation failures raise `TaskError`
- Solution validation failures raise `ValidationError`
- Naming suggests broader scope for ValidationError
- Consider: Is TaskError a subclass of ValidationError conceptually?

## 3. Remaining Generic Exceptions

**Still using ValueError (should be domain exceptions):**

1. **Validation executor** (`/home/mpedersen/topics/brownbench/src/codegen_bench/validation/executor.py:31`):
   ```python
   raise ValueError(f"Workspace does not exist: {self.workspace}")
   ```
   Should be: `raise ValidationError(...)`

2. **Statistical modules** (variance.py, effect_size.py, correction.py):
   - Multiple `ValueError` for data validation
   - Should introduce `StatsError` exception type
   - Examples: empty data, missing variables, incompatible inputs

3. **ClaudeJudge** as noted above - should use `JudgeError`

4. **MAMS adaptive stats** (`/home/mpedersen/topics/brownbench/src/codegen_bench/stats/adaptive/mams.py:119,130`):
   - Should use `StatsError` or `TournamentError` depending on context

**Test code using RuntimeError (acceptable):**
- `/home/mpedersen/topics/brownbench/tests/unit/test_worktree.py:175,258`
- Test exceptions don't need to be domain-specific
- These are for simulating failures

## 4. Command Validation and Security

### What's Good

**Excellent security documentation:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/core/task.py:31-33` has clear security note
- Explains that `shlex.split()` + `shell=False` prevents shell injection
- Documents that shell features (pipes, redirects, etc.) are NOT supported

**Validation at load time:**
- Commands validated in `Task.validate()` before execution
- Fail-fast: invalid commands caught early, not during tournament
- Structured logging of validation failures

**Defense in depth:**
- Validation at task load time (task.py line 79-102)
- Parsing during execution (executor.py line 70)
- shell=False in subprocess.run (executor.py line 74)

**Good error handling in executor:**
- Catches ValueError from malformed shlex commands (executor.py line 98)
- Returns ValidationResult with error details instead of crashing

### What Could Be Improved

**Command validation doesn't check for dangerous patterns:**
- Only validates that `shlex.split()` succeeds
- Doesn't check for suspicious commands or patterns
- Consider: Whitelist of allowed commands? (make, cmake, pytest, etc.)
- Consider: Blacklist of dangerous patterns? (rm -rf, curl, wget, eval)
- Trade-off: Too restrictive vs security risk

**No validation of command semantics:**
- Could validate that compile_command and test_command are non-empty if specified
- Could check that commands start with expected tools
- Example: test_command should probably start with pytest/unittest/make test

**Timeout values are hardcoded:**
- Executor uses 300s for compile, 600s for test
- Worktree operations use 30s, 10s timeouts
- Should these be configurable per-task?
- Some embedded tests might need longer timeouts

**No validation that commands will work in target environment:**
- Commands validated for syntax but not availability
- Could fail at runtime if tool not installed
- Consider: Check during validation that required tools exist?
- Trade-off: Validation environment might differ from execution environment

## 5. Other Architecture Concerns

### Good Patterns Observed

**Consistent error handling across modules:**
- Worktree, applicator, loader all follow same pattern
- Catch specific exceptions, add context, reraise as domain exception
- Example pattern: `except (OSError, PermissionError) as e: raise DomainError(...) from e`

**Proper cleanup with context managers:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/validation/worktree.py:164-189`
- Context manager ensures cleanup even on exception
- Good use of try/finally

**Cache failures don't break system:**
- `/home/mpedersen/topics/brownbench/src/codegen_bench/cache/store.py:83`
- Corrupted cache returns None, logs warning
- System continues with cache miss
- Good graceful degradation

### Concerns

**Inconsistent use of Path vs string for paths:**
- Most modules use `Path` objects
- But changed_files dict uses string keys
- Solution.changed_files: `dict[str, str]`
- Consider: Should file paths in solutions be Path objects?

**No validation of Solution objects:**
- Solution dataclass has no `validate()` method
- Changed files could have invalid paths, empty content
- Validation happens at application time (too late?)

**DUTError usage is minimal:**
- Only used in 3 places: registry and simple_chat API key check
- DUT.solve() failures raise generic Exception
- SimpleChatDUT line 130 does `raise` without specifying exception type
- Should wrap all DUT failures in DUTError

**Error recovery not documented:**
- Unclear what callers should do when they catch these exceptions
- Should tournaments retry? Abort? Skip task?
- Consider: Add recovery guidance in exception docstrings

## Summary and Recommendations

### Excellent Work
1. Domain-specific exception hierarchy with clear semantics
2. Contextual error messages with relevant details
3. Proper exception chaining preserving stack traces
4. Command validation prevents shell injection
5. Structured logging integrated with error handling

### Critical Fixes Needed
1. **Fix silent failure in worktree cleanup** (line 187) - log failures, don't swallow
2. **Replace ValueError in ClaudeJudge** with JudgeError (3 locations)
3. **Replace ValueError in executor.py** with ValidationError

### Recommended Improvements
1. **Add StatsError exception** for statistical modules
2. **Make Task.validate() raise instead of return boolean** - eliminates duplicate error handling
3. **Add structured attributes to exceptions** for programmatic error handling
4. **Document error recovery strategies** in exception docstrings
5. **Add semantic validation for commands** beyond syntax checking
6. **Wrap all DUT failures** in DUTError consistently

### Architectural Questions to Consider
1. Should ValidationResult pattern be replaced with exceptions for consistency?
2. Should TaskError be a subclass of ValidationError?
3. Should timeouts be configurable per-task rather than hardcoded?
4. Should Solution objects have validation methods?

## MPED Principle Adherence

**Strengths:**
- ✅ Fail fast and verbosely: Excellent error messages with context
- ✅ Composable: Exception hierarchy doesn't create dependencies
- ✅ Single source of truth: One exception module, clear hierarchy
- ✅ Fundamentals first: Uses standard library patterns correctly

**Needs Work:**
- ❌ Silent failures: worktree cleanup swallows errors
- ⚠️  Optimization for readability: Some exception messages could be clearer
- ⚠️  Bottom-up development: Some exceptions defined but not used (TournamentError, CacheError barely used)

**Overall Assessment:** 7/10 - Good foundation with domain exceptions and fail-fast approach. Main issues are silent failures and incomplete migration from generic to domain exceptions. Command validation is solid but could be more semantic.
