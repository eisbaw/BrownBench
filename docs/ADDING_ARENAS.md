# Adding New Arenas (Quality Dimensions)

This guide explains how to create new arenas for evaluating code quality in BrownBench. An arena represents a quality dimension (e.g., maintainability, performance) along which solutions are compared.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Arena Anatomy](#arena-anatomy)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Writing Effective Prompts](#writing-effective-prompts)
5. [Testing Your Arena](#testing-your-arena)
6. [Calibration](#calibration)
7. [Examples](#examples)

## Quick Start

To create a new arena:

1. Define an `Arena` instance
2. Create a judge prompt template
3. Add to arena registry
4. Calibrate against ground truth
5. Document evaluation criteria

**Minimal Example**:

```python
from pathlib import Path
from codegen_bench.core.arena import Arena

CODE_SMELL = Arena(
    name="code-smell",
    display_name="Code Smell Detection",
    description="Identifies and avoids common code smells",
    criteria=[
        "Avoids long methods/functions",
        "No duplicate code",
        "Clear separation of concerns",
        "No magic numbers or strings",
    ],
    prompt_template_path=Path("judge/prompts/code_smell.txt"),
)
```

## Arena Anatomy

### Arena Class

```python
@dataclass
class Arena:
    """A quality dimension for evaluation."""

    name: str                      # Unique identifier (lowercase, no spaces)
    display_name: str              # Human-readable name
    description: str               # Brief description (1 sentence)
    criteria: list[str]            # Evaluation criteria (3-6 items)
    prompt_template_path: Path     # Path to prompt template
    prompt_version: str = ""       # Auto-computed SHA-256 hash
```

### Required Components

1. **Arena Definition**: Python dataclass instance
2. **Prompt Template**: Text file with evaluation instructions
3. **Criteria**: List of specific quality attributes
4. **Documentation**: What the arena measures and why

## Step-by-Step Guide

### Step 1: Define Arena Concept

Identify a quality dimension not covered by existing arenas:

**Existing arenas**:
- Maintainability: Code clarity, documentation
- Architectural Integrity: Patterns, abstractions
- Surgical Precision: Minimal changes
- Testability: Test coverage, quality
- Performance: Algorithmic efficiency
- Safety: Error handling, resource management

**New arena ideas**:
- Security: Input validation, secrets handling
- Accessibility: WCAG compliance, a11y
- Observability: Logging, metrics, tracing
- Internationalization: i18n/l10n support
- Code Smell: Anti-patterns, technical debt
- API Design: Interface quality, consistency

### Step 2: Create Prompt Template

Create a file in `src/codegen_bench/judge/prompts/`:

```bash
touch src/codegen_bench/judge/prompts/security.txt
```

**Template structure**:

```text
You are an expert code reviewer evaluating two solutions for {quality_dimension}.

# Task
{task_spec}

# Constraints
{constraints}

# Solution A
{solution_a}

# Solution B
{solution_b}

# Evaluation Criteria: {Quality Dimension}

Evaluate which solution is better based on:

1. **Criterion 1**: Description
2. **Criterion 2**: Description
3. **Criterion 3**: Description
4. **Criterion 4**: Description

# Output Format

You MUST respond in exactly this format:

WINNER: A|B|TIE
REASONING: [2-3 sentences explaining your decision, focusing on the most important differences]
CONFIDENCE: [number between 0.0 and 1.0 indicating how confident you are]

Examples:
- WINNER: A
- WINNER: B
- WINNER: TIE

Guidelines:
- Use TIE only if the solutions are truly equivalent
- Be specific about what makes one solution better
- Focus on the most impactful differences
- Consider real-world implications
```

**Template variables** (provided at runtime):
- `{task_spec}`: Task specification
- `{constraints}`: Task constraints
- `{solution_a}`: First solution code
- `{solution_b}`: Second solution code

### Step 3: Define Arena Instance

Add to `src/codegen_bench/core/arena.py`:

```python
SECURITY = Arena(
    name="security",
    display_name="Security",
    description="Input validation, secure coding practices",
    criteria=[
        "Input validation and sanitization",
        "No hardcoded secrets or credentials",
        "Secure API usage",
        "Protection against common vulnerabilities",
    ],
    prompt_template_path=Path("judge/prompts/security.txt"),
)

# Add to ALL_ARENAS list
ALL_ARENAS = [
    MAINTAINABILITY,
    ARCHITECTURAL_INTEGRITY,
    SURGICAL_PRECISION,
    TESTABILITY,
    PERFORMANCE,
    SAFETY,
    SECURITY,  # New arena
]
```

### Step 4: Test Prompt Loading

Verify the prompt template loads correctly:

```python
from codegen_bench.core.arena import SECURITY

# Load prompt with test data
prompt = SECURITY.load_prompt(
    task_spec="Add user authentication",
    constraints="- Must use bcrypt for passwords\n- No plaintext storage",
    solution_a="# Solution A code here",
    solution_b="# Solution B code here",
)

print(prompt)
```

### Step 5: Add Unit Tests

Create `tests/unit/test_security_arena.py`:

```python
import pytest
from codegen_bench.core.arena import SECURITY

def test_security_arena_attributes():
    """Test arena has required attributes."""
    assert SECURITY.name == "security"
    assert SECURITY.display_name == "Security"
    assert len(SECURITY.criteria) >= 3

def test_security_arena_prompt_loads():
    """Test prompt template loads without error."""
    prompt = SECURITY.load_prompt(
        task_spec="Test task",
        constraints="Test constraints",
        solution_a="def foo(): pass",
        solution_b="def bar(): pass",
    )

    assert "Security" in prompt
    assert "WINNER:" in prompt
    assert "solution_a" not in prompt.lower()  # Verify template vars expanded

def test_security_arena_prompt_version():
    """Test prompt version hash is computed."""
    version = SECURITY.get_prompt_version()

    assert version
    assert len(version) == 16  # SHA-256 truncated to 16 chars
    assert version.isalnum()
```

### Step 6: Document the Arena

Add to arena documentation:

```markdown
## Security Arena

**Purpose**: Evaluate solutions for security best practices and vulnerability prevention.

**When to use**: For tasks involving:
- User input handling
- Authentication/authorization
- Data encryption
- API security
- Secrets management

**Evaluation criteria**:
1. Input validation and sanitization
2. No hardcoded secrets or credentials
3. Secure API usage
4. Protection against common vulnerabilities (SQL injection, XSS, etc.)

**Judge training**: Requires ground truth with security experts' judgments.

**Common pitfalls**:
- Over-engineering for low-risk contexts
- Security theater vs. actual protection
- False positives on safe patterns
```

## Writing Effective Prompts

### Prompt Design Principles

1. **Be specific**: Clearly define what you're evaluating
2. **Be actionable**: Criteria should be objectively assessable
3. **Be fair**: Don't favor particular coding styles
4. **Be complete**: Cover all aspects of the quality dimension
5. **Be consistent**: Use same format as other arena prompts

### Good vs. Bad Criteria

**Good criteria** (specific, actionable):
- ✅ "Functions are < 50 lines and have single responsibility"
- ✅ "Error cases return appropriate HTTP status codes"
- ✅ "Database queries use parameterized statements"

**Bad criteria** (vague, subjective):
- ❌ "Code is good"
- ❌ "Follows best practices"
- ❌ "Professional quality"

### Position Bias Mitigation

Always present solutions neutrally:

```text
# Solution A
{solution_a}

# Solution B
{solution_b}
```

**Don't**:
- Label as "old" vs "new"
- Indicate which is "expected" to be better
- Use suggestive language

### Confidence Calibration

Guide the judge on confidence levels:

```text
CONFIDENCE: [0.0-1.0]

- 0.9-1.0: Clear winner, obvious differences
- 0.7-0.8: Moderate confidence, some trade-offs
- 0.5-0.6: Slight preference, close call
- 0.3-0.4: Very close, minor differences
- 0.0-0.2: Unable to decide (use TIE instead)
```

### Example: Security Arena Prompt

```text
You are an expert security engineer evaluating two solutions for security.

# Task
{task_spec}

# Constraints
{constraints}

# Solution A
{solution_a}

# Solution B
{solution_b}

# Evaluation Criteria: Security

Evaluate which solution is more secure based on:

1. **Input Validation**: Is user input properly validated and sanitized?
2. **Secrets Management**: Are credentials, API keys, and secrets handled securely?
3. **Secure APIs**: Are security-sensitive APIs (crypto, auth) used correctly?
4. **Vulnerability Protection**: Does the code protect against common vulnerabilities (injection, XSS, CSRF)?
5. **Data Protection**: Is sensitive data encrypted at rest and in transit?
6. **Principle of Least Privilege**: Are permissions and access scoped minimally?

# Output Format

You MUST respond in exactly this format:

WINNER: A|B|TIE
REASONING: [2-3 sentences explaining your decision, focusing on the most critical security differences]
CONFIDENCE: [number between 0.0 and 1.0 indicating how confident you are]

Examples:
- WINNER: A
- WINNER: B
- WINNER: TIE

Guidelines:
- Use TIE only if the solutions have equivalent security posture
- Prioritize vulnerabilities by severity (critical > high > medium > low)
- Consider defense in depth - multiple layers of protection
- Real vulnerabilities matter more than theoretical risks
- Be specific about which vulnerabilities are present or prevented
```

## Testing Your Arena

### 1. Unit Tests

Test arena definition and prompt loading:

```python
def test_arena_definition():
    """Test arena is properly defined."""
    from codegen_bench.core.arena import MY_ARENA

    assert MY_ARENA.name == "expected-name"
    assert len(MY_ARENA.criteria) >= 3
    assert MY_ARENA.prompt_template_path.exists()

def test_prompt_formatting():
    """Test prompt template formats correctly."""
    prompt = MY_ARENA.load_prompt(
        task_spec="Test",
        constraints="None",
        solution_a="Code A",
        solution_b="Code B",
    )

    assert "Test" in prompt
    assert "Code A" in prompt
    assert "Code B" in prompt
    assert "{task_spec}" not in prompt  # No unformatted vars
```

### 2. Judge Testing

Test with actual judge:

```python
def test_arena_with_judge():
    """Test arena works with ClaudeJudge."""
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.core.solution import Solution

    judge = ClaudeJudge(config={"api_key": "test"})

    solution_a = Solution(
        approach_id="test-a",
        task_id="test",
        seed=42,
        changed_files={"main.py": "def foo(): pass"},
    )

    solution_b = Solution(
        approach_id="test-b",
        task_id="test",
        seed=42,
        changed_files={"main.py": "def bar(): pass"},
    )

    result = judge.judge(solution_a, solution_b, MY_ARENA)

    assert result.winner in ["A", "B", "TIE"]
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.reasoning) > 0
```

### 3. Validation Testing

Test with known good/bad solutions:

```python
def test_arena_discriminates():
    """Test arena can distinguish good from bad solutions."""

    # Good solution with proper security
    good_solution = Solution(
        approach_id="good",
        task_id="test",
        changed_files={
            "api.py": """
            def authenticate(username, password):
                # Proper password hashing
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                user = db.query(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)  # Parameterized query
                )
                return user
            """
        },
    )

    # Bad solution with vulnerabilities
    bad_solution = Solution(
        approach_id="bad",
        task_id="test",
        changed_files={
            "api.py": """
            def authenticate(username, password):
                # Plaintext password
                user = db.query(
                    f"SELECT * FROM users WHERE username = '{username}'"
                    # SQL injection vulnerability
                )
                return user
            """
        },
    )

    judge = ClaudeJudge(config={...})
    result = judge.judge(good_solution, bad_solution, SECURITY)

    # Good solution should win
    assert result.winner == "A"
    assert result.confidence > 0.7
```

## Calibration

After creating an arena, you must calibrate judges to ensure accuracy.

### 1. Create Ground Truth

Select 50-100 solution pairs and get expert judgments:

```yaml
# calibration/security.yaml
arena: security
pairs:
  - id: sec-001
    task_id: task-1
    solution_a: simple-chat-42
    solution_b: elaborate-prompt-42
    ground_truth:
      winner: B
      confidence: 0.9
      reasoning: "Solution B properly validates input and uses parameterized queries, while A has SQL injection vulnerability"
      expert_id: security-expert-1

  - id: sec-002
    task_id: task-2
    solution_a: simple-chat-43
    solution_b: elaborate-prompt-43
    ground_truth:
      winner: TIE
      confidence: 0.8
      reasoning: "Both solutions handle authentication securely with bcrypt and no hardcoded secrets"
      expert_id: security-expert-2
```

### 2. Run Calibration

```bash
codegen-bench calibrate \
  --arena security \
  --ground-truth calibration/security.yaml \
  --judge claude-judge \
  --output security-calibration-report.json
```

### 3. Analyze Results

The calibration report shows:
- Agreement rate with ground truth
- Fleiss' Kappa (inter-rater reliability)
- Position bias (A vs B preference)
- Confusion matrix

**Target metrics**:
- Agreement rate: ≥ 85%
- Fleiss' Kappa: ≥ 0.7 (substantial agreement)
- Position bias: < 10% difference

### 4. Refine Prompt

If calibration fails:

1. **Identify disagreements**: Where does judge differ from experts?
2. **Analyze patterns**: Are certain criteria being misweighted?
3. **Update prompt**: Add clarifications, examples, edge cases
4. **Re-calibrate**: Test updated prompt

**Iteration example**:

```text
# Version 1 (poor calibration)
Evaluate which solution is more secure.

# Version 2 (better calibration)
Evaluate which solution is more secure based on:
1. Input validation
2. Secrets management
3. Vulnerability protection

# Version 3 (good calibration)
Evaluate which solution is more secure based on:
1. Input validation: All user input must be validated and sanitized
2. Secrets management: No hardcoded credentials, use env vars or secret stores
3. Vulnerability protection: Prevent SQL injection (use parameterized queries), XSS (escape output), CSRF (use tokens)

Prioritize by severity: Critical vulnerabilities (SQL injection) outweigh minor issues (weak validation on low-risk inputs).
```

## Examples

### Example 1: Code Smell Arena

```python
# In src/codegen_bench/core/arena.py
CODE_SMELL = Arena(
    name="code-smell",
    display_name="Code Smell Detection",
    description="Identifies and avoids common anti-patterns",
    criteria=[
        "No long methods (> 50 lines)",
        "No duplicate code",
        "Clear separation of concerns",
        "No magic numbers or strings",
        "No deeply nested conditionals",
        "No god objects or classes",
    ],
    prompt_template_path=Path("judge/prompts/code_smell.txt"),
)
```

```text
# In src/codegen_bench/judge/prompts/code_smell.txt
You are an expert code reviewer evaluating two solutions for code smells.

# Task
{task_spec}

# Constraints
{constraints}

# Solution A
{solution_a}

# Solution B
{solution_b}

# Evaluation Criteria: Code Smells

Evaluate which solution avoids code smells better based on:

1. **Long Methods**: Are functions/methods < 50 lines with single responsibility?
2. **Code Duplication**: Is there duplicate logic that should be extracted?
3. **Separation of Concerns**: Are different responsibilities clearly separated?
4. **Magic Values**: Are magic numbers/strings replaced with named constants?
5. **Nested Complexity**: Is nesting depth reasonable (< 4 levels)?
6. **God Objects**: Are classes focused with limited responsibilities?

# Output Format

You MUST respond in exactly this format:

WINNER: A|B|TIE
REASONING: [2-3 sentences explaining which code smells are present and their severity]
CONFIDENCE: [number between 0.0 and 1.0]

Guidelines:
- Use TIE only if both solutions have equivalent code smell levels
- Prioritize severe smells (god objects, high duplication) over minor ones
- Consider maintainability impact: which smells will cause pain later?
- Be specific about which smells are present in each solution
```

### Example 2: Observability Arena

```python
# In src/codegen_bench/core/arena.py
OBSERVABILITY = Arena(
    name="observability",
    display_name="Observability",
    description="Logging, metrics, and debugging support",
    criteria=[
        "Appropriate logging levels and messages",
        "Structured logging with context",
        "Error logging with stack traces",
        "Performance metrics for critical paths",
    ],
    prompt_template_path=Path("judge/prompts/observability.txt"),
)
```

```text
# In src/codegen_bench/judge/prompts/observability.txt
You are an expert SRE evaluating two solutions for observability.

# Task
{task_spec}

# Constraints
{constraints}

# Solution A
{solution_a}

# Solution B
{solution_b}

# Evaluation Criteria: Observability

Evaluate which solution has better observability based on:

1. **Logging Coverage**: Are important operations logged?
2. **Log Levels**: Are appropriate levels used (DEBUG/INFO/WARN/ERROR)?
3. **Structured Logging**: Are logs structured with context (user_id, request_id)?
4. **Error Logging**: Are errors logged with stack traces and context?
5. **Metrics**: Are performance metrics emitted for critical paths?
6. **Debugging Support**: How easy is it to debug issues in production?

# Output Format

You MUST respond in exactly this format:

WINNER: A|B|TIE
REASONING: [2-3 sentences explaining the observability differences]
CONFIDENCE: [number between 0.0 and 1.0]

Guidelines:
- Use TIE only if both solutions have equivalent observability
- Consider production debugging scenarios
- Structured logs are better than unstructured
- Error context is critical for debugging
- Avoid logging sensitive data (passwords, tokens)
```

## Best Practices

### 1. Arena Scope

- **Do**: Focus on a specific quality dimension
- **Don't**: Create overlapping arenas (e.g., "Code Quality" that overlaps with Maintainability)

### 2. Criteria Specificity

- **Do**: Define concrete, measurable criteria
- **Don't**: Use vague terms like "good" or "professional"

### 3. Prompt Clarity

- **Do**: Provide clear examples and guidelines
- **Don't**: Assume the judge knows your intentions

### 4. Calibration

- **Do**: Calibrate with domain experts
- **Don't**: Skip calibration and assume accuracy

### 5. Version Control

- **Do**: Track prompt versions with SHA-256 hashes
- **Don't**: Modify prompts without documenting changes

### 6. Balance

- **Do**: Consider trade-offs (security vs performance)
- **Don't**: Evaluate dimensions in isolation

## Troubleshooting

### Low Agreement Rate (< 85%)

**Diagnosis**:
- Criteria too vague
- Missing edge cases
- Position bias
- Ambiguous language

**Solution**:
1. Add specific examples to prompt
2. Clarify criteria with measurable attributes
3. Add edge case guidelines
4. Test with position-swapped pairs

### High Position Bias

**Diagnosis**:
- Prompt suggests preference for A or B
- Example bias in prompt
- Judge interprets "first" as "current"

**Solution**:
1. Review prompt for suggestive language
2. Use neutral labels (A/B, not old/new)
3. Randomize solution order in testing

### Judge Always Chooses TIE

**Diagnosis**:
- Criteria too strict (no solution meets bar)
- Criteria too loose (all solutions equivalent)
- Confidence threshold too high

**Solution**:
1. Adjust criteria to reasonable standards
2. Add differentiating factors
3. Provide TIE usage guidelines

### Poor Discrimination

**Diagnosis**:
- Can't distinguish good from bad solutions
- Random judgments

**Solution**:
1. Test with known good/bad pairs
2. Add contrastive examples to prompt
3. Simplify criteria to most important factors

## Next Steps

1. **Design your arena** following this guide
2. **Create prompt template** with clear criteria
3. **Add unit tests** (>90% coverage)
4. **Run calibration** with ground truth
5. **Iterate on prompt** until ≥85% agreement
6. **Document** in arena documentation
7. **Submit PR** if contributing to BrownBench

## References

- Arena definition: `src/codegen_bench/core/arena.py`
- Example prompts: `src/codegen_bench/judge/prompts/`
- Judge interface: `src/codegen_bench/judge/base.py`
- Calibration: `docs/CALIBRATION.md` (to be created)
- Ground truth format: `src/codegen_bench/stats/ground_truth.py`
