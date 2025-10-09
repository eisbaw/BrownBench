# Tournament Cost Estimation Guide

This guide helps you estimate API costs for running BrownBench tournaments at different scales, enabling informed budget planning before starting your benchmarking experiments.

## Table of Contents
- [Quick Reference](#quick-reference)
- [Cost Formula](#cost-formula)
- [Tier Presets](#tier-presets)
- [Detailed Breakdowns](#detailed-breakdowns)
- [Optimization Strategies](#optimization-strategies)
- [Real-World Examples](#real-world-examples)
- [Cost Calculator](#cost-calculator)

## Quick Reference

### Estimated Costs by Scale

| Scale | DUTs | Tasks | Samples | Judge Calls | Estimated Cost |
|-------|------|-------|---------|-------------|----------------|
| Quick Test | 2 | 5 | 1 | 10 | $0.50 - $1.00 |
| Small | 3 | 10 | 3 | 90 | $5 - $10 |
| Standard | 5 | 20 | 5 | 500 | $25 - $50 |
| Large | 10 | 50 | 5 | 2,500 | $125 - $250 |
| Research | 20 | 100 | 10 | 20,000 | $1,000 - $2,000 |

*Costs based on Claude 3 Sonnet pricing as of January 2025*

## Cost Formula

### Basic Formula

```
Total Cost = Generation Cost + Judgment Cost

Where:
- Generation Cost = (DUTs × Tasks × Samples) × (Input + Output Token Costs)
- Judgment Cost = (Comparisons × Judge Calls) × Judge Token Costs
```

### Detailed Breakdown

#### 1. Generation Costs

```python
generation_cost = (
    num_duts ×
    num_tasks ×
    samples_per_pairing ×
    (avg_prompt_tokens × input_price + avg_output_tokens × output_price)
)
```

**Typical Token Usage:**
- Simple prompt: 500-1,000 input tokens
- Elaborate prompt: 2,000-4,000 input tokens
- Optimized prompt: 300-600 input tokens
- Generated code: 500-2,000 output tokens

#### 2. Judgment Costs

```python
num_comparisons = (num_duts × (num_duts - 1)) / 2  # All pairs
judgment_cost = (
    num_comparisons ×
    num_arenas ×
    samples_per_comparison ×
    (judge_prompt_tokens × input_price + judge_response_tokens × output_price)
)
```

**Typical Judge Token Usage:**
- Standard judge prompt: 1,500-3,000 tokens
- Optimized judge prompt: 800-1,500 tokens
- Judge response: 50-200 tokens

## Tier Presets

### Tier 1: Quick Evaluation ($5-15)
- **Purpose**: Rapid testing, development validation
- **Configuration**:
  - 2-3 DUTs
  - 5-10 tasks
  - 1-2 samples per pairing
  - 1-2 arenas
- **Use Cases**:
  - Testing new DUT implementations
  - Validating tournament setup
  - Quick A/B comparisons

### Tier 2: Standard Benchmark ($50-150)
- **Purpose**: Meaningful comparisons, reliable results
- **Configuration**:
  - 5-7 DUTs
  - 20-30 tasks
  - 3-5 samples per pairing
  - 3-4 arenas
- **Use Cases**:
  - Research experiments
  - Model selection
  - Performance validation

### Tier 3: Comprehensive Study ($500-2000)
- **Purpose**: Publication-quality results
- **Configuration**:
  - 10-20 DUTs
  - 50-100 tasks
  - 5-10 samples per pairing
  - 5-6 arenas
- **Use Cases**:
  - Academic research
  - Production deployment decisions
  - Comprehensive benchmarking

## Detailed Breakdowns

### Cost Components by Model

| Model | Input (per 1K tokens) | Output (per 1K tokens) |
|-------|----------------------|------------------------|
| Claude 3 Opus | $0.015 | $0.075 |
| Claude 3 Sonnet | $0.003 | $0.015 |
| Claude 3 Haiku | $0.00025 | $0.00125 |
| GPT-4 | $0.03 | $0.06 |
| GPT-3.5 Turbo | $0.001 | $0.002 |

*Prices as of January 2025, check provider documentation for current rates*

### Token Usage Patterns

#### DUT Token Usage
```
SimpleChatDUT:       800-1,200 input,  800-1,500 output
ElaboratePromptDUT:  2,500-4,000 input, 1,000-2,000 output
OptimizedPromptDUT:  400-700 input,    800-1,500 output
```

#### Judge Token Usage
```
Standard Judge:      2,000-3,000 input, 100-200 output
Optimized Judge:     1,000-1,500 input, 100-200 output
Per Arena:          +200-500 tokens for specific criteria
```

## Optimization Strategies

### 1. Use Optimized Prompts
- Switch to `OptimizedPromptDUT` for 40-50% token reduction
- Use `OptimizedClaudeJudge` for 30-40% token reduction
- Potential savings: 35-45% overall

### 2. Reduce Sampling
- Start with fewer samples (1-2) for initial experiments
- Increase samples only for final validation
- Potential savings: 50-80% during development

### 3. Selective Arena Testing
- Begin with 1-2 most critical arenas
- Add more arenas only for comprehensive analysis
- Potential savings: 50-75% on judgment costs

### 4. Incremental Evaluation
- Run small tournaments first to identify promising DUTs
- Use adaptive designs to eliminate poor performers early
- Potential savings: 30-50% through early stopping

### 5. Cache Effectively
- Reuse cached results when re-running with same configurations
- Share cache across team members
- Potential savings: 100% on repeated runs

## Real-World Examples

### Example 1: Comparing 3 Models
```yaml
Scenario: Quick comparison of 3 DUT variations
Configuration:
  duts: 3
  tasks: 10
  samples_per_pairing: 2
  arenas: 2 (maintainability, correctness)

Calculations:
  Generations: 3 × 10 × 2 = 60
  Generation tokens: 60 × (1000 + 1000) = 120,000
  Generation cost: 120 × $0.003 + 120 × $0.015 = $2.16

  Comparisons: 3 × 2 / 2 = 3 pairs
  Judgments: 3 × 2 × 10 × 2 = 120
  Judge tokens: 120 × (2000 + 150) = 258,000
  Judge cost: 258 × $0.003 + 18 × $0.015 = $1.04

Total: ~$3.20
```

### Example 2: Research Benchmark
```yaml
Scenario: Academic research comparing 10 approaches
Configuration:
  duts: 10
  tasks: 50
  samples_per_pairing: 5
  arenas: 5

Calculations:
  Generations: 10 × 50 × 5 = 2,500
  Generation tokens: 2,500 × (1500 + 1200) = 6,750,000
  Generation cost: 6,750 × $0.003 + 3,000 × $0.015 = $65.25

  Comparisons: 45 pairs
  Judgments: 45 × 5 × 50 × 5 = 56,250
  Judge tokens: 56,250 × (2500 + 150) = 148,125,000
  Judge cost: 148,125 × $0.003 + 8,438 × $0.015 = $570.94

Total: ~$636
```

### Example 3: Production Validation
```yaml
Scenario: Validating new model for production
Configuration:
  duts: 2 (current vs new)
  tasks: 100 (comprehensive test suite)
  samples_per_pairing: 10 (high confidence)
  arenas: 6 (all quality dimensions)

Calculations:
  Generations: 2 × 100 × 10 = 2,000
  Generation tokens: 2,000 × (1000 + 1500) = 5,000,000
  Generation cost: 5,000 × $0.003 + 3,000 × $0.015 = $60

  Comparisons: 1 pair
  Judgments: 1 × 6 × 100 × 10 = 6,000
  Judge tokens: 6,000 × (2000 + 150) = 12,900,000
  Judge cost: 12,900 × $0.003 + 900 × $0.015 = $52.20

Total: ~$112
```

## Cost Calculator

### Python Script

```python
from codegen_bench.core.config import PricingConfig

def estimate_tournament_cost(
    num_duts: int,
    num_tasks: int,
    samples_per_pairing: int,
    num_arenas: int = 1,
    avg_prompt_tokens: int = 1000,
    avg_output_tokens: int = 1000,
    judge_prompt_tokens: int = 2000,
    judge_response_tokens: int = 150,
    pricing: PricingConfig = None
) -> dict:
    """Estimate tournament costs."""

    if pricing is None:
        pricing = PricingConfig()

    # Generation costs
    total_generations = num_duts * num_tasks * samples_per_pairing
    gen_input_cost = (total_generations * avg_prompt_tokens / 1000) * \
                     pricing.claude_sonnet_4_5_input_per_1k
    gen_output_cost = (total_generations * avg_output_tokens / 1000) * \
                      pricing.claude_sonnet_4_5_output_per_1k
    generation_cost = gen_input_cost + gen_output_cost

    # Judgment costs
    num_comparisons = (num_duts * (num_duts - 1)) // 2
    total_judgments = num_comparisons * num_arenas * num_tasks * samples_per_pairing
    judge_input_cost = (total_judgments * judge_prompt_tokens / 1000) * \
                       pricing.claude_sonnet_4_5_input_per_1k
    judge_output_cost = (total_judgments * judge_response_tokens / 1000) * \
                        pricing.claude_sonnet_4_5_output_per_1k
    judgment_cost = judge_input_cost + judge_output_cost

    return {
        'total_generations': total_generations,
        'total_judgments': total_judgments,
        'generation_cost': generation_cost,
        'judgment_cost': judgment_cost,
        'total_cost': generation_cost + judgment_cost,
        'cost_per_dut': (generation_cost + judgment_cost) / num_duts,
        'cost_per_task': (generation_cost + judgment_cost) / num_tasks
    }

# Example usage
result = estimate_tournament_cost(
    num_duts=5,
    num_tasks=20,
    samples_per_pairing=3,
    num_arenas=3
)
print(f"Estimated total cost: ${result['total_cost']:.2f}")
print(f"Cost per DUT: ${result['cost_per_dut']:.2f}")
print(f"Cost per task: ${result['cost_per_task']:.2f}")
```

## Best Practices

### Budget Planning

1. **Start Small**: Run minimal viable tournament first
2. **Use Progressive Evaluation**:
   - Phase 1: 2-3 DUTs, 5 tasks, 1 sample
   - Phase 2: Winners + new DUTs, 20 tasks, 3 samples
   - Phase 3: Final validation, all tasks, 5+ samples

3. **Set Budget Limits**: Use `BudgetEnforcer` to prevent overruns
```python
config = {
    'max_cost_per_dut': 50.0,
    'total_budget_limit': 500.0,
    'warning_threshold': 0.8
}
```

4. **Monitor Spending**: Check costs after each phase
```bash
codegen-bench tournament --tier 1 --budget-limit 50
```

### Cost-Saving Tips

1. **Development Phase**:
   - Use mock DUTs for testing infrastructure
   - Test with subset of tasks
   - Single sample per pairing
   - Estimated savings: 80-90%

2. **Optimization Phase**:
   - Use optimized prompts
   - Cache all results
   - Run during off-peak hours (if applicable)
   - Estimated savings: 40-50%

3. **Production Phase**:
   - Batch multiple evaluations
   - Share costs across teams
   - Use incremental evaluation
   - Estimated savings: 20-30%

## Conclusion

Tournament costs scale with:
- **Linear factors**: DUTs × Tasks × Samples
- **Quadratic factors**: DUT comparisons (n²/2)

Key recommendations:
- Start with Tier 1 ($5-15) for development
- Use Tier 2 ($50-150) for meaningful comparisons
- Reserve Tier 3 ($500+) for final validation
- Always use optimized prompts when possible
- Implement caching to avoid repeated API calls
- Monitor costs continuously with `BudgetEnforcer`

For specific cost estimates for your use case, use the cost calculator script above or run:
```bash
codegen-bench estimate --duts 5 --tasks 20 --samples 3
```