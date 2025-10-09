# SimpleChatDUT Documentation

## Overview

SimpleChatDUT is a minimal baseline DUT (Device Under Test) that uses a single-turn chat interaction with an AI model to generate code solutions. It serves as a simple, transparent baseline for comparison with more sophisticated approaches.

## Design Philosophy

- **Minimal prompting**: Uses a straightforward task description without complex instructions
- **Single API call**: One request per task, no iteration or refinement
- **Transparent**: Simple enough to understand and reproduce
- **Fast**: Quick generation with minimal overhead
- **Cost-effective**: Single API call keeps costs low

## Architecture

### Prompt Structure

SimpleChatDUT builds a minimal prompt containing:
1. Task name and specification
2. Constraints
3. Key files to modify
4. Basic formatting instructions for code blocks

### Code Extraction

Uses `CodeExtractor` to parse code from various formats:
- Triple-backtick code blocks with language/file hints
- File path annotations
- Multiple code blocks in single response

### Rate Limiting

Built-in rate limiter prevents API quota exhaustion:
- Default: 50 requests per minute
- Configurable via `max_requests_per_minute` parameter
- Automatic backoff with exponential retry (up to 3 attempts)

## Configuration

### Basic Configuration

```python
from codegen_bench.dut.simple_chat import SimpleChatDUT

config = {
    "model": "claude-sonnet-4-20250514",
    "api_key": None,  # Falls back to ANTHROPIC_API_KEY env var
    "max_tokens": 8000,
    "temperature": 0.3,
    "max_requests_per_minute": 50,
}

dut = SimpleChatDUT(config)
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | str | `claude-sonnet-4-20250514` | Claude model identifier |
| `api_key` | str\|None | None | API key (or use `ANTHROPIC_API_KEY` env var) |
| `max_tokens` | int | 8000 | Maximum tokens in response |
| `temperature` | float | 0.3 | Sampling temperature (0.0-1.0) |
| `max_requests_per_minute` | int | 50 | Rate limit for API calls |

### Environment Variables

Required:
- `ANTHROPIC_API_KEY`: Anthropic API key if not provided in config

## Usage Examples

### Basic Usage

```python
from codegen_bench.core.task import Task
from codegen_bench.dut.simple_chat import SimpleChatDUT

# Load task
task = Task.from_yaml_file("tasks/core/task_006.yaml")

# Create DUT
dut = SimpleChatDUT(config={})  # Uses defaults

# Generate solution
solution = dut.solve(task, seed=42)

print(f"Generated {len(solution.changed_files)} files")
print(f"Cost: ${solution.cost_usd:.4f}")
print(f"Time: {solution.generation_time_seconds:.1f}s")
```

### In Tournament

```python
from codegen_bench.core.tournament import TournamentRunner
from codegen_bench.dut.simple_chat import SimpleChatDUT

# Create multiple SimpleChatDUT variants
duts = [
    SimpleChatDUT({"model": "claude-sonnet-4-20250514", "temperature": 0.3}),
    SimpleChatDUT({"model": "claude-sonnet-4-20250514", "temperature": 0.7}),
]

# Use in tournament...
```

### Comparing Different Models

```python
# Claude variant
claude_dut = SimpleChatDUT({
    "model": "claude-sonnet-4-20250514",
    "api_key_env": "ANTHROPIC_API_KEY",
})

# For OpenAI models, you would need to extend SimpleChatDUT
# or use a different DUT implementation
```

## Cost Analysis

### Pricing (as of January 2025)

Claude Sonnet 4.5:
- Input: $3.00 per million tokens ($0.003 per 1K)
- Output: $15.00 per million tokens ($0.015 per 1K)

### Typical Costs

For a medium-complexity task (200 LoC):
- Input tokens: ~2,000 (task spec + prompt)
- Output tokens: ~1,500 (code changes)
- **Total cost: ~$0.03 per solution**

For a full tournament (26 tasks, 3 samples):
- Solutions: 26 tasks × 3 samples = 78 solutions
- **Estimated cost: $2-4 per DUT**

## Performance Characteristics

### Strengths

1. **Fast generation**: Single API call, minimal overhead
2. **Low cost**: One API call per task
3. **Predictable**: Same prompt structure for all tasks
4. **Easy to understand**: Transparent baseline for comparison
5. **Reproducible**: Deterministic seed (though Claude may have variance)

### Limitations

1. **No iteration**: Cannot refine or improve initial solution
2. **No context reading**: Doesn't explore codebase before generating
3. **No error recovery**: If generation fails, must retry entire task
4. **Limited reasoning**: Single-shot approach misses opportunity for planning
5. **No tool use**: Cannot query codebase, run tests, or use external tools

### When to Use

SimpleChatDUT is ideal for:
- Establishing baseline performance
- Quick evaluations
- Cost-conscious comparisons
- Understanding minimum viable approach
- Sanity checking more complex DUTs

SimpleChatDUT is **not** ideal for:
- Complex refactoring tasks requiring deep codebase understanding
- Tasks needing iterative refinement
- Situations where cost is not a primary concern
- When maximum accuracy is required

## Technical Details

### Error Handling

SimpleChatDUT includes robust error handling:

1. **API Errors**: Automatic retry with exponential backoff (3 attempts)
2. **Parsing Errors**: Graceful failure with actionable error messages
3. **Config Errors**: Validation on initialization
4. **Rate Limiting**: Automatic request throttling

### Logging

Structured logging provides visibility:
- Task start/completion
- API call details (tokens, cost)
- Parsing results (files found)
- Errors with context

### Caching

SimpleChatDUT integrates with `SolutionCache`:
- Identical (DUT, task, seed) tuples are cached
- Avoids redundant API calls during development
- Cache invalidated when DUT configuration changes

## Extending SimpleChatDUT

### Custom Prompts

To customize the prompt:

```python
class CustomSimpleChatDUT(SimpleChatDUT):
    def _build_prompt(self, task: Task) -> str:
        # Custom prompt logic
        return f"Custom instruction: {task.specification}"
```

### Different Models

To support different providers:

```python
# Current SimpleChatDUT is Anthropic-specific
# For OpenAI, create a parallel implementation or
# generalize the base class
```

## Troubleshooting

### Common Issues

**Issue**: `DUTConfigError: ANTHROPIC_API_KEY not found`
- **Solution**: Set environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`

**Issue**: Rate limit errors
- **Solution**: Reduce `max_requests_per_minute` or add delay between runs

**Issue**: Parsing errors
- **Solution**: Check that model is generating code blocks with proper format

**Issue**: High costs
- **Solution**: Reduce `max_tokens` or use smaller model variant

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Version History

- **v1.0.0** (2025-01): Initial implementation
  - Single-turn chat with Claude
  - Basic error handling and retry logic
  - Code extraction from markdown blocks
  - Cost tracking and rate limiting

## See Also

- [ElaboratePromptDUT](ELABORATE_PROMPT_DUT.md) - Enhanced prompting approach
- [Adding New DUTs](../../docs/ADDING_DUTS.md) - Guide to creating custom DUTs
- [Tournament Configuration](../../docs/CONFIGURATION.md) - Running tournaments
