# BrownBench Configuration Guide

Complete guide to configuring BrownBench for your benchmarking needs.

## Table of Contents

- [Configuration Methods](#configuration-methods)
- [Configuration File Format](#configuration-file-format)
- [DUT Configuration](#dut-configuration)
- [Tournament Configuration](#tournament-configuration)
- [Judge Configuration](#judge-configuration)
- [Cache Configuration](#cache-configuration)
- [Advanced Configuration](#advanced-configuration)
- [Configuration Examples](#configuration-examples)

## Configuration Methods

Brown Bench can be configured through multiple methods with the following precedence (highest to lowest):

1. **Command-line flags** (highest priority)
2. **Configuration file** (specified with `--config`)
3. **Environment variables**
4. **Defaults** (lowest priority)

### Example Precedence

```bash
# Environment variable
export CODEGEN_BENCH_CACHE_DIR="/env/cache"

# Config file contains: cache_dir: /config/cache

# Command runs with flag
codegen-bench --cache-dir /flag/cache generate ...

# Result: Uses /flag/cache (CLI flag wins)
```

## Configuration File Format

Configuration files can be written in YAML or JSON.

### YAML Format (Recommended)

```yaml
# config.yaml
cache_dir: ~/.cache/codegen-bench
log_level: INFO

# DUT configurations
duts:
  simple-chat:
    model: claude-sonnet-4-20250514
    max_tokens: 8000
    temperature: 0.3
    max_requests_per_minute: 50

  elaborate-prompt:
    model: claude-sonnet-4-20250514
    max_tokens: 8000
    temperature: 0.3
    include_codebase_context: true
    max_context_files: 5

# Judge configurations
judges:
  claude:
    model: claude-sonnet-4-20250514
    temperature: 0.0  # Deterministic for consistency

# Tournament settings
tournament:
  base_seed: 42
  consensus_threshold: 0.7
  parallel_workers: 4
```

### JSON Format

```json
{
  "cache_dir": "~/.cache/codegen-bench",
  "log_level": "INFO",
  "duts": {
    "simple-chat": {
      "model": "claude-sonnet-4-20250514",
      "max_tokens": 8000,
      "temperature": 0.3
    }
  }
}
```

### Using Configuration File

```bash
# Specify config file with --config flag
codegen-bench --config my_config.yaml generate ...

# Or set default config via environment variable
export CODEGEN_BENCH_CONFIG="/path/to/config.yaml"
codegen-bench generate ...  # Uses default config
```

## DUT Configuration

Configure code generation approaches (Devices Under Test).

### SimpleChatDUT

Minimal single-turn prompting approach.

```yaml
duts:
  simple-chat:
    # Model selection
    model: claude-sonnet-4-20250514

    # API authentication
    api_key: ${ANTHROPIC_API_KEY}  # Use env var

    # Generation parameters
    max_tokens: 8000           # Maximum tokens in response
    temperature: 0.3           # Sampling temperature (0.0-1.0)

    # Rate limiting
    max_requests_per_minute: 50  # API rate limit
```

**Parameters**:

- **model** (string): Claude model ID
  - Options: `claude-sonnet-4-20250514`, `claude-opus-4-20250514`
  - Default: `claude-sonnet-4-20250514`

- **api_key** (string): Anthropic API key
  - Default: Read from `ANTHROPIC_API_KEY` environment variable
  - **Required**: Must be set via config or environment

- **max_tokens** (integer): Maximum response tokens
  - Range: `1` to `100000`
  - Default: `8000`
  - Higher values allow longer solutions but cost more

- **temperature** (float): Sampling randomness
  - Range: `0.0` (deterministic) to `1.0` (creative)
  - Default: `0.3`
  - Recommendation: `0.0-0.3` for code generation

- **max_requests_per_minute** (integer): Rate limit for API calls
  - Default: `50`
  - Adjust based on your API tier

### ElaboratePromptDUT

Enhanced prompting with codebase context analysis.

```yaml
duts:
  elaborate-prompt:
    # Inherits all SimpleChatDUT parameters, plus:

    # Codebase analysis
    include_codebase_context: true  # Read existing files
    max_context_files: 5            # Limit files to read
```

**Additional Parameters**:

- **include_codebase_context** (boolean): Read and analyze existing code
  - Default: `true`
  - Enables richer context for brownfield refactoring
  - Increases prompt tokens (higher cost)

- **max_context_files** (integer): Maximum files to include in prompt
  - Default: `5`
  - Higher values provide more context but increase cost
  - Recommendation: `3-10` depending on task complexity

### Custom DUT Configuration

If you've implemented a custom DUT:

```yaml
duts:
  my-custom-dut:
    # Your custom parameters
    custom_param_1: value1
    custom_param_2: value2

    # Can still use common parameters
    api_key: ${ANTHROPIC_API_KEY}
    temperature: 0.2
```

## Tournament Configuration

Configure tournament behavior (currently via Python API).

```python
from codegen_bench.core.config import TournamentConfig, TrueSkillConfig, PricingConfig

# Tournament configuration
config = TournamentConfig(
    # Randomization seed for reproducibility
    base_seed=42,

    # Number of solution samples per (DUT, task) pairing
    samples_per_pairing=3,

    # Save checkpoint every N comparisons
    checkpoint_interval=10
)

# TrueSkill rating configuration (optional, for rating systems)
trueskill_config = TrueSkillConfig(
    # Initial skill parameters
    initial_mu=25.0,       # Mean skill rating for new players
    initial_sigma=8.33,    # Skill uncertainty (standard deviation)

    # Match parameters
    beta=4.17,            # Distance guaranteeing ~76% win probability
    tau=0.0833,           # Skill dynamics factor (drift over time)
    draw_probability=0.1  # Expected probability of draws (10%)
)
```

### Tournament Parameters

**TournamentConfig Parameters**:
- **base_seed** (int): Master seed for reproducibility
  - Default: `42`
  - Derived seeds used for each solution sample

- **samples_per_pairing** (int): Number of solution samples per (DUT, task) pair
  - Default: `3`
  - Higher values increase statistical power but also increase cost

- **checkpoint_interval** (int): Save checkpoint every N comparisons
  - Default: `10`
  - Allows resuming interrupted tournaments

### TrueSkill Rating Configuration

**TrueSkillConfig Parameters**:
- **initial_mu** (float): Initial mean skill rating for new players
  - Default: `25.0` (standard TrueSkill value)
  - Higher values indicate higher initial skill estimate

- **initial_sigma** (float): Initial skill uncertainty (standard deviation)
  - Default: `8.33` (roughly 1/3 of skill range)
  - Higher values indicate more uncertainty about true skill

- **beta** (float, optional): Distance that guarantees ~76% win probability
  - Default: `initial_sigma / 2`
  - Controls how much randomness affects match outcomes

- **tau** (float, optional): Skill dynamics factor
  - Default: `initial_sigma / 100`
  - Models skill drift over time (use 0 for static skills)

- **draw_probability** (float): Expected probability of draws
  - Default: `0.1` (10% draws expected)
  - Affects how conservatively skills are updated

### Pricing Configuration

Configure API pricing for cost tracking.

```python
from codegen_bench.core.config import PricingConfig

# Pricing configuration for API cost calculations
pricing = PricingConfig(
    # Claude Sonnet 4.5 pricing (per 1,000 tokens)
    claude_sonnet_4_5_input_per_1k=0.003,   # $3.00 per million input tokens
    claude_sonnet_4_5_output_per_1k=0.015,  # $15.00 per million output tokens
)

# Example: Calculate cost for a request
input_tokens = 1500
output_tokens = 500
input_cost = (input_tokens / 1000) * pricing.claude_sonnet_4_5_input_per_1k
output_cost = (output_tokens / 1000) * pricing.claude_sonnet_4_5_output_per_1k
total_cost = input_cost + output_cost  # $0.012
```

**PricingConfig Parameters**:
- **claude_sonnet_4_5_input_per_1k** (float): Cost per 1,000 input tokens
  - Default: `0.003` ($3.00 per million tokens)
  - As of January 2025 pricing

- **claude_sonnet_4_5_output_per_1k** (float): Cost per 1,000 output tokens
  - Default: `0.015` ($15.00 per million tokens)
  - As of January 2025 pricing

Note: Pricing is centralized in this configuration to make it easy to update as API pricing changes.

## Judge Configuration

Configure AI judges for solution evaluation.

```yaml
judges:
  claude:
    # Model settings
    model: claude-sonnet-4-20250514
    temperature: 0.0  # Deterministic for consistency
    max_tokens: 4000

    # Judge-specific parameters
    use_cot: true  # Chain-of-thought reasoning
    verbosity: medium  # low, medium, high
```

**Judge Parameters**:

- **model** (string): Judge model
  - Recommendation: Same or stronger than DUT model

- **temperature** (float): Sampling temperature
  - Recommendation: `0.0` for consistency

- **use_cot** (boolean): Enable chain-of-thought reasoning
  - Default: `true`
  - Provides more reliable judgments

- **verbosity** (string): Judgment detail level
  - Options: `low`, `medium`, `high`
  - Higher verbosity helps debugging but costs more tokens

## Cache Configuration

Configure solution caching behavior.

### Via Configuration File

```yaml
cache:
  # Cache location
  cache_dir: ~/.cache/codegen-bench

  # Cache behavior
  enabled: true

  # Note: Advanced cache features (TTL, size limits, eviction policies)
  # are planned but not yet implemented. Currently uses simple file-based caching.
```

### Via Environment Variables

```bash
# Cache directory
export CODEGEN_BENCH_CACHE_DIR="$HOME/.cache/codegen-bench"

# Disable cache
export CODEGEN_BENCH_NO_CACHE=1
```

### Via CLI Flags

```bash
# Custom cache directory
codegen-bench --cache-dir /tmp/cache generate ...

# Force regeneration (ignore cache)
codegen-bench generate --no-cache ...
```

### Cache Structure

```
~/.cache/codegen-bench/
├── solutions/
│   ├── simple-chat_task_001_42.json
│   ├── simple-chat_task_002_42.json
│   └── elaborate-prompt_task_001_42.json
└── metadata/
    └── cache_index.json
```

### Cache Management

```bash
# View cache size
du -sh ~/.cache/codegen-bench/

# Clear cache
rm -rf ~/.cache/codegen-bench/

# Clear cache for specific DUT
rm ~/.cache/codegen-bench/solutions/simple-chat_*.json
```

## Advanced Configuration

### Logging Configuration

```yaml
logging:
  # Log level
  level: INFO  # DEBUG, INFO, WARNING, ERROR

  # Log format
  format: json  # json, text

  # Log output
  file: logs/codegen-bench.log
  console: true

  # Structured logging fields
  include_timestamps: true
  include_context: true
```

### Security Configuration

```yaml
security:
  # Container isolation (if using Docker-based DUTs)
  enable_container_isolation: true

  # Resource limits
  max_memory_mb: 4096
  max_cpu_percent: 50

  # Network restrictions
  allow_network: false  # Disable network for DUTs
  api_proxy_only: true  # Only allow API calls via proxy
```

### Performance Configuration

```yaml
performance:
  # Parallelization
  max_parallel_duts: 4
  max_parallel_tasks: 8

  # Timeouts
  generation_timeout_sec: 300
  validation_timeout_sec: 600

  # Retries
  max_retries: 3
  retry_delay_sec: 5
```

## Configuration Examples

### Example 1: Cost-Conscious Configuration

Minimize API costs while maintaining quality.

```yaml
duts:
  simple-chat:
    model: claude-sonnet-4-20250514  # More economical than Opus
    max_tokens: 4000                 # Limit response length
    temperature: 0.1                 # Lower variance = fewer retries
    max_requests_per_minute: 30      # Conservative rate limit

  elaborate-prompt:
    model: claude-sonnet-4-20250514
    max_tokens: 4000
    temperature: 0.1
    include_codebase_context: true
    max_context_files: 3             # Fewer files = lower cost

tournament:
  parallel_workers: 2                # Slower but more controllable
  max_cost_per_dut: 2.0             # Tight budget
  max_total_cost: 10.0

cache:
  enabled: true                      # Aggressively cache
  ttl_days: 365                      # Long TTL
```

**Estimated savings**: 50-70% compared to default config

### Example 2: High-Performance Configuration

Maximize throughput for large-scale evaluation.

```yaml
duts:
  simple-chat:
    model: claude-sonnet-4-20250514
    max_tokens: 8000
    temperature: 0.3
    max_requests_per_minute: 100     # High rate limit

  elaborate-prompt:
    model: claude-sonnet-4-20250514
    max_tokens: 8000
    temperature: 0.3
    include_codebase_context: true
    max_context_files: 10            # Rich context

tournament:
  parallel_workers: 8                # Maximum parallelism
  max_cost_per_dut: 50.0            # High budget
  max_total_cost: 500.0

cache:
  enabled: true
  max_size_mb: 5000                  # Large cache

performance:
  max_parallel_duts: 8
  max_parallel_tasks: 16
  generation_timeout_sec: 600        # Generous timeout
```

**Estimated speedup**: 4-8x compared to default config

### Example 3: Research Configuration

Maximize reproducibility and statistical rigor.

```yaml
duts:
  simple-chat:
    model: claude-sonnet-4-20250514
    max_tokens: 8000
    temperature: 0.0                 # Fully deterministic
    max_requests_per_minute: 50

judges:
  claude:
    model: claude-opus-4-20250514    # Strongest model for judges
    temperature: 0.0                 # Deterministic judgments
    use_cot: true                    # Detailed reasoning

tournament:
  base_seed: 42                      # Fixed seed
  num_judges: 5                      # High consensus requirement
  consensus_threshold: 0.8           # 80% agreement needed

logging:
  level: DEBUG                       # Maximum detail
  format: json
  file: logs/experiment.jsonl
  include_timestamps: true
  include_context: true
```

### Example 4: Development Configuration

Fast iteration for DUT development.

```yaml
duts:
  my-new-dut:
    model: claude-sonnet-4-20250514
    max_tokens: 4000                 # Faster responses
    temperature: 0.3
    # ... custom parameters

tournament:
  task_ids:                          # Small test set
    - task_001
    - task_002
  parallel_workers: 1                # Sequential for debugging
  max_cost_per_dut: 1.0             # Low budget limit

logging:
  level: DEBUG                       # Verbose logging
  console: true                      # See output immediately

cache:
  enabled: false                     # Disable cache during dev
```

## Environment Variable Reference

Complete list of environment variables:

```bash
# API Keys
export ANTHROPIC_API_KEY="sk-ant-..."

# Cache
export CODEGEN_BENCH_CACHE_DIR="$HOME/.cache/codegen-bench"
export CODEGEN_BENCH_NO_CACHE=1  # Disable cache

# Logging
export CODEGEN_BENCH_LOG_LEVEL="DEBUG"  # DEBUG, INFO, WARNING, ERROR
export CODEGEN_BENCH_LOG_FORMAT="json"  # json, text

# Configuration
export CODEGEN_BENCH_CONFIG="/path/to/config.yaml"

# Performance
export CODEGEN_BENCH_PARALLEL_WORKERS=4
export CODEGEN_BENCH_TIMEOUT_SEC=300

# Security
export CODEGEN_BENCH_ENABLE_CONTAINER_ISOLATION=1
export CODEGEN_BENCH_ALLOW_NETWORK=0
```

## Validation

Validate your configuration file:

```bash
# Test configuration by running init (doesn't make API calls)
codegen-bench --config my_config.yaml init /tmp/test-bench

# Check for config errors
codegen-bench -vv --config my_config.yaml init /tmp/test-bench 2>&1 | grep -i error
```

## Best Practices

### 1. Version Control Your Config

```bash
# Add config to git
git add config.yaml

# Use different configs for different purposes
configs/
├── development.yaml
├── production.yaml
├── research.yaml
└── ci.yaml
```

### 2. Use Environment Variables for Secrets

```yaml
# DON'T: Hard-code API keys
api_key: sk-ant-abc123...

# DO: Reference environment variables
api_key: ${ANTHROPIC_API_KEY}
```

### 3. Start Conservative, Scale Up

```yaml
# Start with low limits
max_cost_per_dut: 1.0
parallel_workers: 2

# Scale up after validation
# max_cost_per_dut: 10.0
# parallel_workers: 8
```

### 4. Document Your Config

```yaml
# config.yaml

# Configuration for: Production tournament evaluation
# Created: 2025-10-09
# Purpose: Compare simple-chat vs elaborate-prompt on core tasks
# Budget: $50 total
# Expected runtime: ~2 hours

duts:
  simple-chat:
    # Using default model for consistency with previous runs
    model: claude-sonnet-4-20250514
    # ... rest of config
```

## Troubleshooting

### Config Not Loading

```bash
# Verify config file exists
ls -la my_config.yaml

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('my_config.yaml'))"

# Test with verbose flag
codegen-bench -vv --config my_config.yaml init /tmp/test
```

### Parameter Not Taking Effect

```bash
# Check precedence: CLI flag > config file > env var > default

# Verify what's being used (check logs)
codegen-bench -vv --config my_config.yaml generate ... 2>&1 | grep -i config
```

### Unknown Parameter Warning

```yaml
# If you see warnings about unknown parameters:
duts:
  simple-chat:
    typo_parameter: value  # Will be ignored with warning

# Check parameter spelling against docs
```

## See Also

- [CLI Reference](CLI_REFERENCE.md) - Command-line options
- [Architecture Overview](ARCHITECTURE.md) - How config is used
- [Adding DUTs](ADDING_DUTS.md) - Custom DUT configuration
- [Troubleshooting](TROUBLESHOOTING.md) - Common config issues
