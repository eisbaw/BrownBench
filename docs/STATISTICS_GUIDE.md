# Statistical Methods in BrownBench

This guide explains the statistical methods used in BrownBench for rigorous evaluation of code generation approaches. Understanding these methods will help you interpret results correctly and design statistically valid experiments.

## Table of Contents

1. [Overview](#overview)
2. [Rating Systems](#rating-systems)
3. [Effect Sizes](#effect-sizes)
4. [Multiple Testing Correction](#multiple-testing-correction)
5. [Adaptive Designs](#adaptive-designs)
6. [Variance Components](#variance-components)
7. [Interpretation Guidelines](#interpretation-guidelines)
8. [Common Pitfalls](#common-pitfalls)
9. [References](#references)

## Overview

BrownBench uses statistically rigorous methods to ensure that:

1. **Ratings are reliable**: Rankings reflect true performance, not random variation
2. **Comparisons are valid**: Statistical tests account for multiple comparisons
3. **Results are reproducible**: Effect sizes and confidence intervals quantify uncertainty
4. **Resources are used efficiently**: Adaptive designs minimize API costs while maintaining power

### Why Statistical Rigor Matters

Without proper statistical methods, benchmarks can produce misleading results:

- **Overfitting**: High variance in rankings makes results unreliable
- **False discoveries**: Multiple comparisons without correction inflate Type I error rates
- **Wasted resources**: Fixed sample sizes often oversample or undersample
- **Poor generalization**: Results may not reflect performance on unseen tasks

BrownBench addresses these issues with principled statistical methods.

## Rating Systems

### TrueSkill Rating System

BrownBench uses **TrueSkill**, a Bayesian skill rating system developed by Microsoft Research for ranking players in competitive games. Unlike simple win/loss ratios, TrueSkill maintains uncertainty estimates and updates beliefs based on match outcomes.

#### How TrueSkill Works

Each approach is represented by a Gaussian distribution over skill:
- **μ (mu)**: Mean skill estimate
- **σ (sigma)**: Uncertainty in skill estimate

**Conservative Skill Estimate**: `skill = μ - 2σ`

This conservative estimate accounts for uncertainty. Approaches with few comparisons have high σ and thus lower conservative skill, even if their μ is high.

#### Rating Updates

After each pairwise comparison (match), TrueSkill updates both approaches' ratings:

1. **Predict match outcome** based on current skill distributions
2. **Observe actual outcome** (win/loss/draw)
3. **Update beliefs** using Bayesian inference:
   - Winner's μ increases, σ decreases (more confident)
   - Loser's μ decreases, σ decreases
   - Unexpected outcomes cause larger updates

**Example**:
```python
# Initial ratings (default: μ=25, σ=8.33)
approach_a = TrueSkillRating(mu=25.0, sigma=8.33)
approach_b = TrueSkillRating(mu=25.0, sigma=8.33)

# After A beats B
approach_a_new = TrueSkillRating(mu=28.1, sigma=7.04)  # Higher skill, lower uncertainty
approach_b_new = TrueSkillRating(mu=21.9, sigma=7.04)  # Lower skill, lower uncertainty

# Conservative estimates
skill_a = 28.1 - 2*7.04 = 14.02
skill_b = 21.9 - 2*7.04 = 7.82
```

#### Match Quality

TrueSkill can predict match quality (how informative a comparison will be):
- **High quality**: Approaches with similar skill and high uncertainty
- **Low quality**: Mismatched skill levels or very certain ratings

BrownBench uses match quality to prioritize informative comparisons in adaptive designs.

#### When to Use TrueSkill

**Strengths**:
- Handles transitivity (if A > B and B > C, then A > C)
- Quantifies uncertainty in rankings
- Adapts to surprising outcomes
- Works with partial rankings (not all pairs compared)

**Limitations**:
- Assumes Gaussian skill distributions
- Requires multiple comparisons per approach (σ decreases slowly)
- Doesn't directly measure absolute performance (only relative)

### Leaderboard Interpretation

The leaderboard shows:
- **Rank**: Ordered by conservative skill estimate (μ - 2σ)
- **Rating (μ)**: Mean skill estimate
- **Uncertainty (σ)**: Standard deviation of skill
- **Conservative**: μ - 2σ (used for ranking)

**Interpreting Ratings**:
- **μ ≈ 25**: Average performance (starting value)
- **μ > 30**: Above average
- **μ > 35**: Strong performance
- **μ < 20**: Below average

**Interpreting Uncertainty**:
- **σ ≈ 8**: Very uncertain (few comparisons)
- **σ ≈ 5**: Moderate confidence
- **σ < 3**: High confidence (many comparisons)

**Overlapping Confidence Intervals**: If two approaches have overlapping intervals `[μ₁ - 2σ₁, μ₁ + 2σ₁]` and `[μ₂ - 2σ₂, μ₂ + 2σ₂]`, the difference may not be statistically significant.

## Effect Sizes

Effect sizes quantify the **magnitude** of differences between approaches, beyond just statistical significance.

### Why Effect Sizes Matter

Statistical significance (p-values) only tells you if a difference exists, not if it's meaningful:
- With large samples, tiny differences become "significant"
- With small samples, large differences may be "non-significant"

Effect sizes answer: "How large is the difference, practically speaking?"

### Cohen's d

**Cohen's d** measures standardized difference between two means:

```
d = (μ₁ - μ₂) / σ_pooled
```

Where `σ_pooled` is the pooled standard deviation.

**Interpretation** (Cohen's guidelines):
- **|d| < 0.2**: Negligible effect
- **0.2 ≤ |d| < 0.5**: Small effect
- **0.5 ≤ |d| < 0.8**: Medium effect
- **|d| ≥ 0.8**: Large effect

**Example**:
```
Approach A: μ = 30, σ = 5
Approach B: μ = 25, σ = 5
d = (30 - 25) / 5 = 1.0  →  Large effect
```

A d of 1.0 means Approach A is one standard deviation better than Approach B.

### Confidence Intervals

BrownBench reports **95% confidence intervals** for effect sizes:
- **CI includes 0**: Difference not statistically significant
- **CI excludes 0**: Significant difference
- **Width of CI**: Precision of estimate (narrow = more precise)

**Example**:
```
Cohen's d = 0.6, 95% CI = [0.3, 0.9]
```
- Effect is medium (d = 0.6)
- Significantly different from 0 (CI excludes 0)
- True effect likely between 0.3 (small) and 0.9 (large)

### Practical Significance vs. Statistical Significance

A result can be:
1. **Statistically significant but practically negligible**: p < 0.05, d = 0.1
2. **Practically important but not significant**: p = 0.10, d = 0.7 (underpowered)
3. **Both significant and important**: p < 0.05, d = 0.8

Always report both p-values and effect sizes!

## Multiple Testing Correction

When making many statistical comparisons, the probability of false discoveries increases. BrownBench uses multiple testing correction to control error rates.

### The Multiple Comparisons Problem

**Example**: Testing 10 approaches (45 pairwise comparisons)
- With α = 0.05, expect 2.25 false positives by chance alone!
- **Family-Wise Error Rate (FWER)**: P(≥1 false positive) ≈ 0.90 (very high!)

Without correction, most "significant" findings may be false positives.

### False Discovery Rate (FDR)

BrownBench uses the **Benjamini-Hochberg** procedure to control the False Discovery Rate:

**FDR**: Expected proportion of false discoveries among all discoveries

**Procedure**:
1. Compute p-values for all m comparisons: p₁, p₂, ..., p_m
2. Sort in ascending order: p₍₁₎ ≤ p₍₂₎ ≤ ... ≤ p₍ₘ₎
3. Find largest i where p₍ᵢ₎ ≤ (i/m) × α
4. Reject hypotheses H₍₁₎, ..., H₍ᵢ₎

**Interpretation**:
- If α = 0.05, expect ≤5% of discoveries to be false positives
- More powerful than FWER control (Bonferroni, Holm)
- Appropriate for exploratory benchmarks

**Example**:
```
10 comparisons, α = 0.05
p-values (sorted): 0.001, 0.008, 0.020, 0.045, 0.060, 0.150, 0.300, 0.500, 0.700, 0.900

Benjamini-Hochberg thresholds:
i=1: 0.001 ≤ (1/10)*0.05 = 0.005  ✓ Reject
i=2: 0.008 ≤ (2/10)*0.05 = 0.010  ✓ Reject
i=3: 0.020 ≤ (3/10)*0.05 = 0.015  ✗ Do not reject
i=4: 0.045 ≤ (4/10)*0.05 = 0.020  ✗ Do not reject

Result: Reject first 2 hypotheses, expect ≤10% FDR among these
```

### Holm-Bonferroni Method

For stricter control of FWER (family-wise error rate), BrownBench also supports **Holm-Bonferroni**:

**Procedure**:
1. Sort p-values: p₍₁₎ ≤ p₍₂₎ ≤ ... ≤ p₍ₘ₎
2. For i = 1 to m:
   - If p₍ᵢ₎ > α/(m - i + 1), stop and accept all remaining
   - Otherwise, reject H₍ᵢ₎

**Properties**:
- Controls FWER: P(≥1 false positive) ≤ α
- More powerful than Bonferroni
- More conservative than Benjamini-Hochberg

### Dunnett's Test for MAMS

When comparing multiple approaches to a control (MAMS designs), BrownBench uses **Dunnett's test**:

**Scenario**: Testing k new approaches vs. 1 control approach
- Regular methods: k comparisons, inflated error rate
- Dunnett's test: Accounts for correlation between comparisons (all share control)

**Advantage**: More powerful than Bonferroni for many-to-one comparisons

### When to Use Each Method

| Method | Use Case | Error Control |
|--------|----------|---------------|
| **Benjamini-Hochberg** | Exploratory benchmarks, many comparisons | FDR (expected % false among discoveries) |
| **Holm-Bonferroni** | Confirmatory tests, strict control needed | FWER (probability of ≥1 false positive) |
| **Dunnett's test** | MAMS: multiple approaches vs. control | FWER for many-to-one comparisons |

## Adaptive Designs

Adaptive designs allow early stopping or sample size adjustments based on interim results, saving resources while maintaining statistical validity.

### Group Sequential Designs

**Traditional approach**: Fix sample size n, analyze once at end
**Group sequential**: Analyze at multiple interim points, stop early if clear result

BrownBench implements **O'Brien-Fleming** spending function:

**Idea**: Spend α conservatively at early looks, more liberally at later looks
- Early stopping requires very strong evidence (protects against false positives)
- Later analyses use more lenient thresholds
- Total α spent across all looks = nominal α (e.g., 0.05)

**Benefits**:
- **Cost savings**: Stop early if approach clearly superior or inferior
- **Ethical**: Don't waste resources on futile comparisons
- **Valid inference**: Proper correction maintains Type I error control

**Example**:
```
3 interim analyses (25%, 50%, 75% of planned n) + final analysis

O'Brien-Fleming boundaries:
Look 1 (n=25):  z > 2.96  (p < 0.003)  →  Very strong evidence needed
Look 2 (n=50):  z > 2.36  (p < 0.018)
Look 3 (n=75):  z > 2.07  (p < 0.038)
Final  (n=100): z > 1.98  (p < 0.048)  →  Close to nominal α = 0.05
```

### Multi-Arm Multi-Stage (MAMS)

MAMS designs efficiently screen many approaches in stages:

**Stage 1: Screening with cheap metrics**
- Evaluate all k approaches on inexpensive criteria (e.g., compilation success)
- Eliminate clearly inferior approaches

**Stage 2: Full evaluation of survivors**
- Evaluate surviving approaches on expensive criteria (e.g., full tournament)
- Use Dunnett's test to compare survivors vs. control

**Benefits**:
- **Cost reduction**: 30-50% savings by eliminating poor approaches early
- **Power maintained**: Proper correction preserves statistical power for final comparisons
- **Flexibility**: Can add new approaches mid-study

**Example**:
```
10 approaches, 2 stages

Stage 1 (screening):
- Metric: Compilation success rate (cheap)
- Eliminate 5 worst approaches
- Cost: 10 × $10 = $100

Stage 2 (full evaluation):
- Metric: TrueSkill rating from full tournament
- Evaluate 5 survivors
- Cost: 5 × $100 = $500

Total: $600 (vs. $1000 for full evaluation of all 10)
Savings: 40%
```

### Conditional Power

**Conditional power** estimates the probability of finding a significant result at the final analysis, given current interim data.

**Use cases**:
- **Futility stopping**: If conditional power < 0.20, unlikely to find significance even if continue
- **Sample size re-estimation**: If power lower than planned, increase sample size

**Formula**:
```
CP = P(reject H₀ at final analysis | current data)
```

**Interpretation**:
- **CP > 0.80**: High probability of success, continue as planned
- **0.50 < CP < 0.80**: Moderate, consider extending sample size
- **CP < 0.20**: Futility, consider stopping for lack of efficacy

## Variance Components

Variance component analysis decomposes total variance into sources, helping understand what drives performance differences.

### Mixed Effects Model

BrownBench uses mixed linear models to partition variance:

```
Y_ijkl = μ + α_i + β_j + γ_k + ε_ijkl
```

Where:
- `Y_ijkl`: Judgment for approach i, task j, arena k, repetition l
- `μ`: Grand mean
- `α_i`: Approach effect (fixed)
- `β_j`: Task effect (random)
- `γ_k`: Arena effect (random)
- `ε_ijkl`: Residual error

### Variance Components

```
Var(Y) = Var(approach) + Var(task) + Var(arena) + Var(residual)
```

**Interpreting components**:
- **Var(approach)**: Differences between code generation approaches (what we care about!)
- **Var(task)**: Some tasks are harder than others (expected)
- **Var(arena)**: Some arenas rate more harshly (quality dimension differences)
- **Var(residual)**: Judge inconsistency, random noise

**Example**:
```
Total variance: 1.00

Variance decomposition:
- Approach: 0.35 (35%)  →  Strong signal!
- Task:     0.40 (40%)  →  Task difficulty varies
- Arena:    0.15 (15%)  →  Moderate arena differences
- Residual: 0.10 (10%)  →  Low noise (good!)

Interpretation:
- Approaches differ substantially (35% of variance)
- Benchmark has good signal-to-noise ratio
- Results should generalize across tasks
```

### Intraclass Correlation (ICC)

**ICC** measures the proportion of variance explained by grouping factors:

```
ICC = Var(between groups) / [Var(between groups) + Var(within groups)]
```

**ICC for approaches**:
```
ICC = Var(approach) / [Var(approach) + Var(task) + Var(arena) + Var(residual)]
```

**Interpretation**:
- **ICC > 0.50**: Most variance due to approach differences (strong benchmark)
- **0.25 < ICC < 0.50**: Moderate discrimination between approaches
- **ICC < 0.25**: Weak signal, approach differences hard to detect

**Example**:
```
ICC = 0.35 / (0.35 + 0.40 + 0.15 + 0.10) = 0.35

Interpretation:
- 35% of variance explained by approach
- Moderate-to-strong benchmark
- Approaches are distinguishable but task variation also important
```

### Reliability

**Test-retest reliability**: Correlation between ratings from independent runs

High reliability (r > 0.85) indicates:
- Consistent judge behavior
- Stable approach performance
- Reproducible results

Low reliability suggests:
- Inconsistent judges (needs calibration)
- High randomness in approach performance
- Insufficient comparisons per approach

## Interpretation Guidelines

### Reading Tournament Results

**1. Check sample sizes**
- Each approach needs ≥10 comparisons for stable ratings
- Low σ indicates sufficient data

**2. Examine effect sizes, not just p-values**
- Is d ≥ 0.5 (medium effect)?
- Are confidence intervals narrow?

**3. Look at variance components**
- Is Var(approach) substantial?
- Is Var(residual) low (< 20%)?

**4. Assess reliability**
- Test-retest r > 0.85?
- Agreement rate > 85%?

**5. Consider practical significance**
- Is the performance difference worth the cost?
- Does it generalize to your use case?

### Reporting Guidelines

When reporting benchmark results, include:

1. **Sample sizes**: Comparisons per approach, tasks evaluated
2. **Effect sizes**: Cohen's d with 95% CIs
3. **Multiple testing correction**: Method used (FDR, FWER)
4. **Variance components**: ICC and variance decomposition
5. **Reliability**: Test-retest correlation, agreement rates
6. **Confidence intervals**: For all estimates
7. **Limitations**: Task coverage, judge calibration, generalizability

**Example**:
```
Approach A (μ = 32.5, σ = 4.2) significantly outperformed
Approach B (μ = 27.1, σ = 4.5) with a large effect size
(d = 1.15, 95% CI = [0.82, 1.48], p < 0.001, FDR-corrected).

Performance differences explained 42% of total variance (ICC = 0.42).
Test-retest reliability was high (r = 0.91, 95% CI = [0.87, 0.94]).

Based on 85 comparisons per approach across 21 tasks and 6 arenas.
```

## Common Pitfalls

### 1. P-hacking / Multiple Testing Without Correction

**Problem**: Running many tests, reporting only significant ones
**Solution**: Pre-register hypotheses, use FDR/FWER correction

### 2. Ignoring Effect Sizes

**Problem**: "Significant" doesn't mean "important"
**Solution**: Always report Cohen's d and CIs

### 3. Underpowered Studies

**Problem**: Small sample sizes miss true effects
**Solution**: Power analysis before running, aim for 80% power

### 4. Overfitting to Tasks

**Problem**: Results don't generalize beyond benchmark tasks
**Solution**: Diverse task set, out-of-sample validation

### 5. Cherry-Picking Metrics

**Problem**: Choosing metrics that favor your approach
**Solution**: Pre-register evaluation criteria

### 6. Ignoring Uncertainty

**Problem**: Ranking without considering σ
**Solution**: Use conservative estimates, report CIs

### 7. Misinterpreting p-values

**Problem**: "p = 0.05 means 95% chance hypothesis is true"
**Correct**: "If H₀ is true, 5% chance of data this extreme"

### 8. Assuming Independence

**Problem**: Pairwise comparisons share tasks/judges (correlated)
**Solution**: Mixed effects models, variance component analysis

## References

### TrueSkill

- Herbrich, R., Minka, T., & Graepel, T. (2007). TrueSkill™: A Bayesian Skill Rating System. *Advances in Neural Information Processing Systems* 19.
- Microsoft Research TrueSkill documentation: https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/

### Effect Sizes

- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.). Routledge.
- Lakens, D. (2013). Calculating and reporting effect sizes to facilitate cumulative science. *Frontiers in Psychology*, 4, 863.

### Multiple Testing

- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society: Series B*, 57(1), 289-300.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.

### Adaptive Designs

- O'Brien, P. C., & Fleming, T. R. (1979). A multiple testing procedure for clinical trials. *Biometrics*, 35(3), 549-556.
- Wason, J. M., & Jaki, T. (2012). Optimal design of multi-arm multi-stage trials. *Statistics in Medicine*, 31(30), 4269-4279.

### Variance Components

- Searle, S. R., Casella, G., & McCulloch, C. E. (1992). *Variance Components*. John Wiley & Sons.
- Shrout, P. E., & Fleiss, J. L. (1979). Intraclass correlations: uses in assessing rater reliability. *Psychological Bulletin*, 86(2), 420.

### General Statistical Methods

- Gelman, A., & Hill, J. (2006). *Data Analysis Using Regression and Multilevel/Hierarchical Models*. Cambridge University Press.
- McElreath, R. (2020). *Statistical Rethinking: A Bayesian Course with Examples in R and Stan* (2nd ed.). CRC Press.

---

For questions about statistical methods, see the [troubleshooting guide](TROUBLESHOOTING.md) or open an issue on GitHub.
