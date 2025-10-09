# Adding New DUTs (Devices Under Test)

This guide explains how to create a new DUT implementation for BrownBench. A DUT represents an AI-assisted code generation approach that can solve programming tasks.

## Table of Contents

1. [Quick Start](#quick-start)
2. [DUT Interface](#dut-interface)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Best Practices](#best-practices)
5. [Testing Your DUT](#testing-your-dut)
6. [Advanced Features](#advanced-features)
7. [Example: ClaudeCodeDUT](#example-claudecodedut)

## Quick Start

To create a new DUT:

1. Subclass `CodeGenerationApproach`
2. Define `APPROACH_ID` class attribute
3. Implement `solve(task, seed)` method
4. Implement `get_metadata()` method
5. Register with `DUTRegistry` (optional)
6. Add unit tests

**Minimal Example**:

```python
from codegen_bench.dut.base import CodeGenerationApproach, ApproachMetadata
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.dut.registry import DUTRegistry

class MyDUT(CodeGenerationApproach):
    """My custom code generation approach."""

    APPROACH_ID = "my-dut"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        # Initialize your approach
        self.model = config.get("model", "default-model")

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution for task."""
        # 1. Build prompt from task
        prompt = self._build_prompt(task)

        # 2. Call your AI/ML system
        response = self._call_model(prompt)

        # 3. Parse code changes
        changed_files = self._parse_response(response)

        # 4. Return Solution
        return Solution(
            approach_id=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
            timestamp=datetime.now(UTC),
            changed_files=changed_files,
            # ... add metrics
        )

    def get_metadata(self) -> ApproachMetadata:
        """Return approach metadata."""
        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="My DUT",
            description="Custom approach description",
            version="1.0.0",
            model=self.model,
            provider="my-provider",
        )

# Register DUT (optional - for CLI usage)
DUTRegistry.register(MyDUT)
```

## DUT Interface

### Required Class Attribute

```python
APPROACH_ID: str  # Unique identifier (e.g., "claude-code", "copilot-agent")
```

### Required Methods

#### `__init__(self, config: dict[str, Any])`

Initialize your DUT with configuration.

**Args**:
- `config`: Configuration dictionary (from YAML/JSON)

**Common config keys**:
- `model`: Model name/ID
- `api_key`: API key (prefer env vars)
- `max_tokens`: Token limit
- `temperature`: Sampling temperature

**Raises**:
- `DUTConfigError`: For invalid configuration

**Example**:

```python
def __init__(self, config: dict[str, Any]):
    super().__init__(config)

    self.model = config.get("model", "default-model")
    self.api_key = config.get("api_key") or os.getenv("MY_API_KEY")

    if not self.api_key:
        raise DUTConfigError("MY_API_KEY not found")

    self.max_tokens = config.get("max_tokens", 8000)
    if self.max_tokens < 1:
        raise DUTConfigError("max_tokens must be positive")
```

#### `solve(self, task: Task, seed: int) -> Solution`

Generate a solution for the given task.

**Args**:
- `task`: Programming task to solve
- `seed`: Random seed for reproducibility

**Returns**:
- `Solution` with generated code and metrics

**Raises**:
- `DUTAPIError`: For API/network failures
- `DUTParsingError`: For response parsing errors
- `DUTError`: For other DUT-specific errors

**Task Properties** (read-only):
- `task.id`: Unique identifier
- `task.name`: Human-readable name
- `task.specification`: What to implement
- `task.constraints`: List of constraints
- `task.key_files`: Files to modify
- `task.domain`: Problem domain
- `task.difficulty`: Easy/medium/hard
- `task.repository_path`: Path to git repo
- `task.target_commit`: Commit SHA to implement

**Solution Properties** (required):
- `approach_id`: Your APPROACH_ID
- `task_id`: task.id
- `seed`: The seed parameter
- `timestamp`: Current UTC timestamp
- `changed_files`: Dict[str, str] mapping file paths to contents

**Solution Properties** (optional metrics):
- `generation_time_seconds`: Time taken
- `total_tokens`: Total API tokens
- `prompt_tokens`: Input tokens
- `completion_tokens`: Output tokens
- `api_calls`: Number of API calls
- `cost_usd`: Total cost in USD

#### `get_metadata(self) -> ApproachMetadata`

Return metadata about your approach.

**Returns**:
- `ApproachMetadata` describing your DUT

**Required fields**:
- `id`: Same as APPROACH_ID
- `name`: Human-readable name
- `description`: Brief description
- `version`: Semantic version

**Optional fields**:
- `model`: Model name/version
- `provider`: Provider name (anthropic, openai, etc.)
- `config`: Configuration dict
- `prompt_hash`: SHA-256 hash of prompt template

**Example**:

```python
def get_metadata(self) -> ApproachMetadata:
    prompt_template = "..."  # Your static prompt template

    return ApproachMetadata(
        id=self.APPROACH_ID,
        name="My Approach",
        description="Does X using Y",
        version="1.0.0",
        model=self.model,
        provider="my-provider",
        config=self.config,
        prompt_hash=self._compute_prompt_hash(prompt_template),
    )
```

## Step-by-Step Guide

### Step 1: Create DUT File

Create a new file in `src/codegen_bench/dut/`:

```bash
touch src/codegen_bench/dut/my_dut.py
```

### Step 2: Define Class

```python
"""My custom DUT implementation."""

from typing import Any
from datetime import UTC, datetime

from codegen_bench.dut.base import CodeGenerationApproach, ApproachMetadata
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.exceptions import DUTConfigError, DUTAPIError

class MyDUT(CodeGenerationApproach):
    """Custom code generation approach."""

    APPROACH_ID = "my-dut"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        # Initialize here
        pass
```

### Step 3: Implement solve()

The solve method should:

1. **Build a prompt** from the task
2. **Call your AI/ML system**
3. **Parse the response** to extract code
4. **Return a Solution** with metrics

```python
def solve(self, task: Task, seed: int) -> Solution:
    """Generate solution for task."""

    # 1. Build prompt
    prompt = f"""
    You are implementing: {task.specification}

    Constraints:
    {chr(10).join(f'- {c}' for c in task.constraints)}

    Key files: {', '.join(task.key_files)}

    Provide modified code for each file.
    """

    # 2. Call your system
    start_time = time.time()
    response = self._call_my_api(prompt)
    elapsed = time.time() - start_time

    # 3. Parse response
    changed_files = self._extract_code(response.text)

    # 4. Return Solution
    return Solution(
        approach_id=self.APPROACH_ID,
        task_id=task.id,
        seed=seed,
        timestamp=datetime.now(UTC),
        changed_files=changed_files,
        generation_time_seconds=elapsed,
        total_tokens=response.total_tokens,
        cost_usd=self._calculate_cost(response),
    )
```

### Step 4: Add Helper Methods

```python
def _call_my_api(self, prompt: str):
    """Call your AI/ML API."""
    try:
        return self.client.generate(prompt)
    except Exception as e:
        raise DUTAPIError(f"API call failed: {e}") from e

def _extract_code(self, text: str) -> dict[str, str]:
    """Extract file changes from response."""
    from codegen_bench.parsing.extractor import CodeExtractor
    return CodeExtractor.extract_all(text)

def _calculate_cost(self, response) -> float:
    """Calculate API cost."""
    input_cost = (response.input_tokens / 1000) * INPUT_PRICE_PER_1K
    output_cost = (response.output_tokens / 1000) * OUTPUT_PRICE_PER_1K
    return input_cost + output_cost
```

### Step 5: Implement get_metadata()

```python
def get_metadata(self) -> ApproachMetadata:
    """Return approach metadata."""
    return ApproachMetadata(
        id=self.APPROACH_ID,
        name="My DUT",
        description="Custom approach using XYZ",
        version="1.0.0",
        model=self.model,
        provider="my-provider",
        config=self.config,
    )
```

### Step 6: Register DUT (Optional)

For CLI integration, register your DUT:

```python
from codegen_bench.dut.registry import DUTRegistry

DUTRegistry.register(MyDUT)
```

Or use the module's `__init__.py`:

```python
# In src/codegen_bench/dut/__init__.py
from codegen_bench.dut.my_dut import MyDUT
from codegen_bench.dut.registry import DUTRegistry

DUTRegistry.register(MyDUT)
```

### Step 7: Add Configuration

Create a config file `configs/duts/my-dut.yaml`:

```yaml
dut_id: my-dut
config:
  model: "my-model-v1"
  api_key: "${MY_API_KEY}"  # From environment
  max_tokens: 8000
  temperature: 0.3
  max_requests_per_minute: 50
```

## Best Practices

### 1. Error Handling

Use specific exceptions:

```python
from codegen_bench.exceptions import DUTConfigError, DUTAPIError, DUTParsingError

# Config errors (fail fast)
if not self.api_key:
    raise DUTConfigError("API key required")

# API errors (retryable)
try:
    response = self.client.call(prompt)
except APIException as e:
    raise DUTAPIError(f"API call failed: {e}") from e

# Parsing errors (response format issues)
try:
    code = extract_code(response)
except KeyError as e:
    raise DUTParsingError(f"Invalid response format: {e}") from e
```

### 2. Logging

Use structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "starting_solution_generation",
    dut=self.APPROACH_ID,
    task_id=task.id,
    seed=seed,
    model=self.model,
)

logger.debug("prompt_built", length=len(prompt))

logger.error(
    "api_error",
    task_id=task.id,
    error=str(e),
    error_type=type(e).__name__,
)
```

### 3. Retry Logic

Implement retries with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _call_api(self, prompt: str):
    """Call API with retry logic."""
    return self.client.generate(prompt)
```

### 4. Rate Limiting

Use the built-in rate limiter:

```python
from codegen_bench.utils.rate_limiter import RateLimiter

class MyDUT(CodeGenerationApproach):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=config.get("max_requests_per_minute", 50)
        )

    def _call_api(self, prompt: str):
        self.rate_limiter.acquire()  # Blocks if rate limit exceeded
        return self.client.generate(prompt)
```

### 5. Cost Tracking

Always track costs accurately:

```python
def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
    """Calculate API cost.

    Pricing as of [date]:
    - Input: $X per 1K tokens
    - Output: $Y per 1K tokens
    """
    INPUT_COST_PER_1K = 0.003
    OUTPUT_COST_PER_1K = 0.015

    input_cost = (input_tokens / 1000) * INPUT_COST_PER_1K
    output_cost = (output_tokens / 1000) * OUTPUT_COST_PER_1K

    return input_cost + output_cost
```

### 6. Reproducibility

Use seeds where possible:

```python
def solve(self, task: Task, seed: int) -> Solution:
    # Set seed if API supports it
    random.seed(seed)
    np.random.seed(seed)

    # Note: Some APIs may not be fully deterministic
    response = self.client.generate(prompt, seed=seed)
```

### 7. Code Extraction

Use the built-in `CodeExtractor`:

```python
from codegen_bench.parsing.extractor import CodeExtractor

changed_files = CodeExtractor.extract_all(response_text)
# Returns: Dict[str, str] mapping file paths to contents
```

Supports multiple formats:
- ` ```language:path/to/file` (recommended)
- `<file path="...">content</file>`
- `// File: path/to/file` followed by code block

## Testing Your DUT

### Unit Tests

Create `tests/unit/test_my_dut.py`:

```python
import pytest
from codegen_bench.dut.my_dut import MyDUT
from codegen_bench.core.task import Task
from codegen_bench.exceptions import DUTConfigError

def test_my_dut_initialization():
    """Test DUT initialization."""
    config = {"model": "test-model", "api_key": "test-key"}
    dut = MyDUT(config)

    assert dut.APPROACH_ID == "my-dut"
    assert dut.model == "test-model"

def test_my_dut_missing_api_key():
    """Test error when API key missing."""
    config = {"model": "test-model"}

    with pytest.raises(DUTConfigError, match="API key"):
        MyDUT(config)

def test_my_dut_solve(mock_task, mock_api_response):
    """Test solution generation."""
    config = {"model": "test", "api_key": "test"}
    dut = MyDUT(config)

    # Mock API call
    dut._call_my_api = lambda p: mock_api_response

    solution = dut.solve(mock_task, seed=42)

    assert solution.approach_id == "my-dut"
    assert solution.task_id == mock_task.id
    assert solution.seed == 42
    assert len(solution.changed_files) > 0

def test_my_dut_metadata():
    """Test metadata generation."""
    config = {"model": "test-model", "api_key": "test"}
    dut = MyDUT(config)

    metadata = dut.get_metadata()

    assert metadata.id == "my-dut"
    assert metadata.name == "My DUT"
    assert metadata.version == "1.0.0"
```

### Integration Tests

Test with real tasks:

```python
def test_my_dut_with_real_task():
    """Test DUT with actual task."""
    from codegen_bench.tasks.registry import TaskRegistry

    config = {
        "model": "test-model",
        "api_key": os.getenv("MY_API_KEY"),
    }
    dut = MyDUT(config)

    task = TaskRegistry.get("task-1")
    solution = dut.solve(task, seed=42)

    assert solution.task_id == "task-1"
    assert solution.generation_time_seconds > 0
    assert solution.cost_usd > 0
```

### Coverage Target

Aim for >90% code coverage:

```bash
pytest tests/unit/test_my_dut.py --cov=src/codegen_bench/dut/my_dut --cov-report=term-missing
```

## Advanced Features

### 1. Multi-Turn Conversations

For approaches that use multiple API calls:

```python
def solve(self, task: Task, seed: int) -> Solution:
    messages = []
    total_tokens = 0
    api_calls = 0

    # Turn 1: Initial prompt
    messages.append({"role": "user", "content": self._build_prompt(task)})
    response1 = self._call_api(messages)
    messages.append({"role": "assistant", "content": response1.text})
    total_tokens += response1.total_tokens
    api_calls += 1

    # Turn 2: Refinement
    messages.append({"role": "user", "content": "Please optimize the code."})
    response2 = self._call_api(messages)
    total_tokens += response2.total_tokens
    api_calls += 1

    changed_files = self._extract_code(response2.text)

    return Solution(
        approach_id=self.APPROACH_ID,
        task_id=task.id,
        seed=seed,
        timestamp=datetime.now(UTC),
        changed_files=changed_files,
        total_tokens=total_tokens,
        api_calls=api_calls,
        # ...
    )
```

### 2. Codebase Context

Read repository context for better solutions:

```python
def solve(self, task: Task, seed: int) -> Solution:
    # Read key files from repository
    context_files = {}
    for file_path in task.key_files:
        full_path = task.repository_path / file_path
        if full_path.exists():
            context_files[file_path] = full_path.read_text()

    # Build prompt with context
    prompt = self._build_prompt_with_context(task, context_files)

    # Generate solution
    response = self._call_api(prompt)
    changed_files = self._extract_code(response.text)

    return Solution(...)
```

### 3. Tool Use

For DUTs that use tools (e.g., file operations, search):

```python
def solve(self, task: Task, seed: int) -> Solution:
    tools = [
        {"name": "read_file", "description": "Read a file from repository"},
        {"name": "search_code", "description": "Search for code patterns"},
    ]

    messages = [{"role": "user", "content": self._build_prompt(task)}]

    while True:
        response = self._call_api(messages, tools=tools)

        if response.stop_reason == "tool_use":
            tool_result = self._execute_tool(response.tool_call, task)
            messages.append({"role": "tool", "content": tool_result})
        else:
            break

    changed_files = self._extract_code(response.text)
    return Solution(...)
```

### 4. Validation and Refinement

Validate and refine solutions:

```python
def solve(self, task: Task, seed: int) -> Solution:
    # Generate initial solution
    response = self._call_api(self._build_prompt(task))
    changed_files = self._extract_code(response.text)

    # Validate syntax
    if not self._validate_syntax(changed_files):
        # Refine with error feedback
        error_msg = "Syntax errors found. Please fix."
        refinement = self._call_api(f"{response.text}\n\n{error_msg}")
        changed_files = self._extract_code(refinement.text)

    return Solution(...)
```

## Example: ClaudeCodeDUT

Here's a complete example of implementing a DUT that uses Claude Code:

```python
"""ClaudeCodeDUT: Use Claude Code as a code generation approach."""

import subprocess
import tempfile
from pathlib import Path
from typing import Any
from datetime import UTC, datetime

from codegen_bench.dut.base import CodeGenerationApproach, ApproachMetadata
from codegen_bench.core.solution import Solution
from codegen_bench.core.task import Task
from codegen_bench.exceptions import DUTConfigError, DUTAPIError
from codegen_bench.dut.registry import DUTRegistry

class ClaudeCodeDUT(CodeGenerationApproach):
    """Use Claude Code to generate solutions."""

    APPROACH_ID = "claude-code"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)

        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise DUTConfigError("ANTHROPIC_API_KEY required")

        # Verify claude-code CLI is available
        try:
            subprocess.run(
                ["claude-code", "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise DUTConfigError("claude-code CLI not found in PATH")

    def solve(self, task: Task, seed: int) -> Solution:
        """Generate solution using Claude Code."""
        start_time = time.time()

        # Create temporary directory for workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Clone repository to workspace
            self._setup_workspace(task, workspace)

            # Build Claude Code prompt
            prompt = self._build_prompt(task)

            # Run Claude Code
            result = self._run_claude_code(prompt, workspace)

            # Extract changed files
            changed_files = self._extract_changes(workspace, task)

        elapsed = time.time() - start_time

        return Solution(
            approach_id=self.APPROACH_ID,
            task_id=task.id,
            seed=seed,
            timestamp=datetime.now(UTC),
            changed_files=changed_files,
            generation_time_seconds=elapsed,
            # Note: Claude Code doesn't expose token counts
            total_tokens=0,
            api_calls=1,
        )

    def _setup_workspace(self, task: Task, workspace: Path):
        """Clone repository and checkout target commit."""
        # Clone repo
        subprocess.run(
            ["git", "clone", str(task.repository_path), str(workspace / "repo")],
            check=True,
            capture_output=True,
        )

        # Checkout parent of target commit
        repo_path = workspace / "repo"
        subprocess.run(
            ["git", "checkout", f"{task.target_commit}^"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

    def _build_prompt(self, task: Task) -> str:
        """Build prompt for Claude Code."""
        constraints = "\n".join(f"- {c}" for c in task.constraints)

        return f"""
Implement the following change:

{task.specification}

Constraints:
{constraints}

Key files to modify: {', '.join(task.key_files)}

Please make the necessary code changes.
"""

    def _run_claude_code(self, prompt: str, workspace: Path) -> subprocess.CompletedProcess:
        """Run Claude Code CLI."""
        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = self.api_key

        try:
            result = subprocess.run(
                [
                    "claude-code",
                    "--model", self.model,
                    "--message", prompt,
                ],
                cwd=workspace / "repo",
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result
        except subprocess.TimeoutExpired:
            raise DUTAPIError("Claude Code execution timed out")
        except subprocess.CalledProcessError as e:
            raise DUTAPIError(f"Claude Code failed: {e.stderr}")

    def _extract_changes(self, workspace: Path, task: Task) -> dict[str, str]:
        """Extract changed files from workspace."""
        repo_path = workspace / "repo"

        # Get list of modified files
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        changed_files = {}
        for file_path in result.stdout.strip().split("\n"):
            if file_path:
                full_path = repo_path / file_path
                if full_path.exists():
                    changed_files[file_path] = full_path.read_text()

        return changed_files

    def get_metadata(self) -> ApproachMetadata:
        """Return approach metadata."""
        return ApproachMetadata(
            id=self.APPROACH_ID,
            name="Claude Code",
            description="Use Claude Code CLI as code generation approach",
            version="1.0.0",
            model=self.model,
            provider="anthropic",
            config=self.config,
        )

# Register DUT
DUTRegistry.register(ClaudeCodeDUT)
```

## Next Steps

1. **Implement your DUT** following this guide
2. **Add comprehensive tests** (>90% coverage)
3. **Run validation**:
   ```bash
   pytest tests/unit/test_my_dut.py
   just lint
   just typecheck
   ```
4. **Test with real tasks**:
   ```bash
   codegen-bench generate --dut=my-dut --task=task-1
   ```
5. **Add documentation** to DUT docstring
6. **Submit PR** if contributing to BrownBench

## Troubleshooting

### Common Issues

1. **API key not found**: Set environment variable before running
   ```bash
   export MY_API_KEY="your-key"
   ```

2. **Code extraction fails**: Use `CodeExtractor.extract_all()` which supports multiple formats

3. **Rate limit errors**: Use `RateLimiter` to throttle requests

4. **Timeout errors**: Add timeout to API calls and handle gracefully

5. **Cost tracking inaccurate**: Double-check pricing constants and token counting

### Getting Help

- See `docs/ARCHITECTURE.md` for system overview
- Check `src/codegen_bench/dut/simple_chat.py` for reference implementation
- Ask in GitHub Discussions or Issues

## References

- Base DUT interface: `src/codegen_bench/dut/base.py`
- SimpleChatDUT example: `src/codegen_bench/dut/simple_chat.py`
- Code extraction: `src/codegen_bench/parsing/extractor.py`
- Exceptions: `src/codegen_bench/exceptions.py`
