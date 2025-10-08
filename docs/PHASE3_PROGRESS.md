# Phase 3: Judge Calibration - Progress Report

**Last Updated:** 2025-10-08
**Status:** In Progress (30% complete)

## Overview

Phase 3 focuses on calibrating LLM judges against human ground truth to ensure accurate and unbiased evaluations. This involves statistical metrics for measuring judge performance, bias detection, and prompt iteration based on findings.

## Completed Components ✅

### 1. Calibration Metrics ✅
**Status:** Complete (99% code coverage)

**Implementation:**
- `src/codegen_bench/stats/calibration.py`
- Agreement rate calculation (simple percentage)
- Fleiss' Kappa for inter-rater reliability
- Position bias detection (favoring A or B)
- Confusion matrix for accuracy breakdown
- Comprehensive calibration reports

**Features:**
- **Agreement Rate:** Simple percentage of matching judgments
- **Fleiss' Kappa:** Inter-rater reliability accounting for chance agreement
  - Interpretation scale: poor/slight/fair/moderate/substantial/almost perfect
  - Based on Landis & Koch (1977) guidelines
- **Position Bias:** Statistical test for favoring position A or B
  - Binomial test for significance (p < 0.05)
  - Detects systematic biases independent of quality
- **Confusion Matrix:** TP/FP/TN/FN breakdown
  - Accuracy, precision, recall, F1 score
  - Identifies specific error patterns
- **Calibration Reports:** Formatted analysis with recommendations

**Test Results:** ✅ 29/29 passing

**API Examples:**
```python
from codegen_bench.stats.calibration import (
    calculate_agreement,
    detect_position_bias,
    calculate_confusion_matrix,
    generate_calibration_report,
)

# Calculate agreement metrics
judge_decisions = ["A", "A", "B", "TIE", "A"]
ground_truth = ["A", "B", "B", "TIE", "A"]

agreement = calculate_agreement(judge_decisions, ground_truth)
print(f"Agreement: {agreement.agreement_rate:.1%}")
print(f"Kappa: {agreement.fleiss_kappa:.3f} ({agreement.interpretation})")

# Detect biases
bias = detect_position_bias(judge_decisions, ground_truth)
print(f"Position bias: {bias.position_bias:+.3f} (p={bias.position_bias_pvalue:.3f})")

# Confusion matrix
cm = calculate_confusion_matrix(judge_decisions, ground_truth)
print(f"Accuracy: {cm.accuracy:.1%}, F1: {cm.f1_score:.3f}")

# Generate comprehensive report
report = generate_calibration_report(judge_decisions, ground_truth, "Claude Judge")
print(report)
```

## Remaining Components 📋

### 2. Web Interface & Data Collection (Not Started)

**Web Interface:**
- [ ] Create web interface for comparisons
- [ ] Simple A/B comparison UI
- [ ] Response collection backend
- [ ] Authentication for participants

**Study Design:**
- [ ] Select 50-100 comparison pairs
- [ ] Ensure diverse difficulty levels
- [ ] Ensure multiple arenas covered
- [ ] Include edge cases
- [ ] Document selection criteria

**Participant Management:**
- [ ] Recruit 10 mid-level programmers
- [ ] Set up payment system ($10 per comparison)
- [ ] Limit sessions to 30 minutes
- [ ] Rotate task order to prevent fatigue

**Advanced Bias Detection:**
- [ ] Length bias detection & correction
- [ ] Regression-based adjustment
- [ ] Bias reporting in results

**CLI Integration:**
- [ ] `codegen-bench calibrate` CLI command
- [ ] Load ground truth file
- [ ] Run judges on calibration set
- [ ] Generate calibration report
- [ ] Calibration command integration tests

**Prompt Iteration:**
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

## Architecture

### Calibration Workflow

```
1. Collect Ground Truth
   ↓ Human experts rate 50-100 comparisons

2. Run LLM Judge
   ↓ Same comparisons evaluated by LLM

3. Calculate Metrics
   ├── Agreement Rate (target: ≥85%)
   ├── Fleiss' Kappa (target: ≥0.60)
   ├── Position Bias (p > 0.05)
   └── Confusion Matrix (accuracy, precision, recall)

4. Analyze Results
   ├── Identify disagreement patterns
   ├── Find ambiguous criteria
   └── Document failure modes

5. Iterate on Prompts
   ├── Update arena prompts
   ├── Add clarifying examples
   └── Re-test until targets met

6. Version Control
   ├── Git tag prompt versions
   └── Record version in judgments
```

### Calibration Metrics Overview

**Agreement Rate:**
- Simple: % of matching judgments
- Target: ≥85% for production use
- Interpretation: Direct measure of concordance

**Fleiss' Kappa:**
- Accounts for chance agreement
- Range: -1 (complete disagreement) to 1 (perfect agreement)
- Interpretation (Landis & Koch):
  - < 0.00: Poor
  - 0.00-0.20: Slight
  - 0.20-0.40: Fair
  - 0.40-0.60: Moderate
  - 0.60-0.80: Substantial
  - 0.80-1.00: Almost Perfect
- Target: ≥0.60 (substantial agreement)

**Position Bias:**
- Tests for systematic A vs B preference
- Uses binomial test (H0: p = 0.5)
- Significant if p < 0.05
- Target: No significant bias (p > 0.05)

**Confusion Matrix:**
- True Positives: Correct "A" judgments
- False Positives: Incorrect "A" judgments (actually "B")
- True Negatives: Correct "B" judgments
- False Negatives: Incorrect "B" judgments (actually "A")
- Metrics: Accuracy, Precision, Recall, F1

## Test Summary

**Total Tests Passing:** 29/29 (100%)
- Agreement calculation: 5 tests
- Fleiss' Kappa: 3 tests
- Position bias: 5 tests
- Confusion matrix: 6 tests
- Report generation: 4 tests
- Edge cases: 6 tests

**Code Coverage:** 99% (calibration module)
- Only 2 uncovered lines (length bias placeholders)

## Key Metrics

- **Modules Implemented:** 1/1 calibration metrics module
- **Functions Implemented:** 4 core functions + 3 helpers
- **Tests Written:** 29 unit tests
- **Code Coverage:** 99%
- **Lines of Code:** ~400 (module + tests)

## Success Criteria (Phase 3)

| Criterion | Target | Current | Status |
|-----------|--------|---------|--------|
| Calibration metrics | Complete | Complete | ✅ |
| Agreement calculation | Complete | Complete | ✅ |
| Bias detection | Complete | Partial | 🟡 |
| Web interface | Complete | Not started | ❌ |
| Ground truth collection | 50-100 pairs | 0 | ❌ |
| Judge accuracy | ≥85% | N/A | ⏸️ |
| Inter-rater reliability | κ ≥ 0.60 | N/A | ⏸️ |
| Prompt iteration | Complete | Not started | ❌ |

**Overall Progress:** 30% complete (metrics done, data collection pending)

## Technical Highlights

### 1. Agreement Metrics
- **Simple Agreement:** Easy to understand, communicates directly
- **Fleiss' Kappa:** Corrects for chance, more rigorous
- **Interpretation:** Qualitative labels for easy communication
- **Handles Ties:** Properly accounts for TIE judgments

### 2. Bias Detection
- **Statistical Testing:** Binomial test with p-values
- **Position Bias:** Detects systematic A/B preferences
- **Length Bias:** Placeholder for future implementation
- **Significance Flags:** Clear indicators of problems

### 3. Confusion Matrix
- **Complete Breakdown:** TP/FP/TN/FN
- **Standard Metrics:** Accuracy, precision, recall, F1
- **Handles Edge Cases:** Zero predictions, all ties
- **Informative:** Identifies specific error patterns

### 4. Calibration Reports
- **Comprehensive:** All metrics in one view
- **Actionable:** Includes specific recommendations
- **Visual Indicators:** ✓ and ⚠️ for quick scanning
- **Formatted:** Easy to read and share

## Example Usage

### Running Calibration Analysis

```python
# Example: Calibrate a judge against ground truth
from codegen_bench.stats.calibration import (
    calculate_agreement,
    detect_position_bias,
    generate_calibration_report,
)

# Load ground truth (from human experts)
ground_truth = ["A", "B", "B", "A", "TIE", "A", "B", "A"]

# Run judge on same comparisons
judge_decisions = ["A", "B", "A", "A", "TIE", "A", "A", "A"]

# Calculate agreement
agreement = calculate_agreement(judge_decisions, ground_truth)
print(f"Agreement Rate: {agreement.agreement_rate:.1%}")
print(f"Fleiss' Kappa: {agreement.fleiss_kappa:.3f} ({agreement.interpretation})")

# Check for biases
bias = detect_position_bias(judge_decisions, ground_truth)
if bias.has_significant_position_bias:
    print(f"⚠️  Position bias detected: {bias.position_bias:+.3f}")
else:
    print("✓ No significant position bias")

# Generate full report
report = generate_calibration_report(judge_decisions, ground_truth, "Claude-4")
print(report)
```

### Interpreting Results

**Good Calibration:**
```
Agreement Rate: 88.0%
Fleiss' Kappa: 0.724 (substantial)
Position Bias: +0.05 (p=0.812) ✓
Accuracy: 88.0%, Precision: 87.5%, Recall: 87.5%, F1: 0.875
```

**Poor Calibration:**
```
Agreement Rate: 62.0%
Fleiss' Kappa: 0.324 (fair)
Position Bias: +0.35 (p=0.003) ⚠️
Accuracy: 62.0%, Precision: 58.3%, Recall: 70.0%, F1: 0.636

Recommendations:
  ⚠️  Moderate agreement (70-85%). Some prompt refinement may help.
  ⚠️  Significant position bias detected. Review prompt neutrality.
  ⚠️  Low inter-rater reliability (κ<0.40). Poor agreement beyond chance.
```

## Dependencies

All statistical dependencies are already available:
- `numpy`: Numerical operations
- `scipy`: Statistical tests (binomtest)
- `pandas`: Data manipulation (if needed)

No additional dependencies required for calibration metrics.

## Next Steps

### Immediate (Complete Core Phase 3)

1. **Implement Length Bias Detection**
   - Add solution length tracking
   - Calculate correlation between length difference and judgment
   - Statistical significance testing
   - Regression-based adjustment

2. **Create CLI Command**
   - `codegen-bench calibrate` command
   - Load ground truth from YAML/JSON
   - Run judge on calibration set
   - Generate and save calibration report
   - Integration tests

3. **Calibration Dataset Format**
   - Define ground truth file format
   - Include comparison pairs
   - Include human judgments
   - Include metadata (task, arena, difficulty)

### Future (Web Interface & Study)

4. **Design Calibration Study**
   - Select representative comparison pairs
   - Ensure diversity (tasks, arenas, difficulty)
   - Include edge cases and ambiguous comparisons
   - Document selection methodology

5. **Build Web Interface**
   - Simple A/B comparison UI
   - Authentication for participants
   - Progress tracking
   - Response collection backend

6. **Execute Study**
   - Recruit participants (10 mid-level programmers)
   - Collect ground truth (50-100 pairs)
   - Pay participants ($10 per comparison)
   - Manage sessions (30-minute limit, rotation)

7. **Iterate on Prompts**
   - Analyze disagreement patterns
   - Identify ambiguous criteria
   - Update arena prompts
   - Re-test until ≥85% agreement
   - Version control for prompts

## Lessons Learned

### What Went Well
- Clean implementation with comprehensive tests (99% coverage)
- Well-documented with examples in docstrings
- Handles edge cases properly (empty data, ties, zeros)
- Clear API with intuitive function names

### Challenges
- Fleiss' Kappa can behave unexpectedly with 2 raters and extreme agreement
- Need to handle ties appropriately in position bias calculation
- Confusion matrix requires filtering ties for meaningful metrics

### Best Practices
- Use dataclasses for clear return types
- Provide interpretation functions for statistical metrics
- Include qualitative labels (poor/fair/good) for communication
- Generate comprehensive reports with recommendations

## References

### Academic Papers
- Fleiss (1971): "Measuring nominal scale agreement among many raters"
- Landis & Koch (1977): "The measurement of observer agreement for categorical data"
- Cohen (1960): "A coefficient of agreement for nominal scales"

### Implementation References
- scikit-learn: Confusion matrix implementations
- statsmodels: Statistical testing
- R package irr: Inter-rater reliability

## Conclusion

**Phase 3 is 30% complete** with all calibration metrics implemented:

### Achievements ✅
- **Agreement metrics** (rate + Fleiss' Kappa)
- **Bias detection** (position bias with statistical testing)
- **Confusion matrix** (accuracy, precision, recall, F1)
- **Calibration reports** (comprehensive, actionable)
- **29 comprehensive tests** with 99% coverage

### Production-Ready Components
The calibration metrics are ready for immediate use:
- Calculate agreement between any two raters
- Detect systematic biases
- Generate detailed accuracy reports
- All statistical tests included

### Remaining Work
The main remaining work is data collection and iteration:
- Web interface for human comparisons (significant engineering)
- Ground truth collection (requires participant recruitment)
- Prompt iteration based on findings (requires data)

These components depend on having ground truth data, which requires human participants and a web interface for efficient data collection.

### Next Priority
Either:
1. Build web interface for data collection (significant effort)
2. Create CLI tools to work with ground truth files (easier next step)
3. Move to Phase 4 and defer full calibration study

The calibration metrics are ready and can be used whenever ground truth data becomes available.
