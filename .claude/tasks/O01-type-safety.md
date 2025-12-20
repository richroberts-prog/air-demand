---
type: task
description: Fix all Pyright errors in production code for strict type safety compliance
tags: [type-safety, pyright, mypy, type-checking, O01]
---

# Feature: O01 Type Safety - Production Code

## Execution Process

Follow these steps in order:

1. Read this entire plan
2. Create TodoWrite list from Task Checklist (all "pending")
3. Execute tasks, updating TodoWrite status in real-time
4. Run validation (L1-L5) after ALL tasks complete
5. Fix any failures, re-validate
6. **Sync progress**: Update Task Checklist in plan file with completion status
7. Output Build Summary (see end of plan)

**Why sync back to the plan?**
- TodoWrite tracks real-time progress during build
- Plan file provides permanent record of completion
- If build is interrupted, we can see partial completion in the plan

**Sub-Agent Strategy:**

Tasks 1-6 are independent and can run in parallel. Task 7 depends on all others completing.

---

## Overview

| | |
|:--|:--|
| **Problem** | Pyright strict mode fails with ~20 errors in production code. Empty collections lack type annotations causing cascade inference failures. |
| **Solution** | Add explicit type annotations to empty lists, dicts, and sets. Fix optional type handling. |
| **Type** | Enhancement |
| **Complexity** | Low |
| **Systems** | core, demand, shared |
| **Dependencies** | None |

---

## Context

### Current Type Checking Status

| Checker | Status | Details |
|---------|--------|---------|
| MyPy | PASSING | 0 errors in strict mode |
| Pyright | FAILING | ~20 errors in production code |

### Root Cause Analysis

All production errors fall into two categories:

1. **Empty collection type inference** (90% of errors)
   - `filtered = []` → Pyright infers `list[Unknown]`
   - `trends = {}` → Pyright infers `dict[Unknown, Unknown]`
   - `categories = set()` → Pyright infers `set[Unknown]`

2. **Optional type handling** (10% of errors)
   - Comparing `None` with operators like `>=`
   - Jinja2 filter type mismatches

### Type Annotation Patterns (from standards)

**Empty Collections - Always annotate:**
```python
# BAD - Pyright infers list[Unknown]
filtered = []

# GOOD - Explicit type
filtered: list[dict[str, Any]] = []
```

**Optional Comparisons - Explicit None check:**
```python
# BAD - Pyright warns about None operand
if value and value >= 0.80:

# GOOD - Explicit is not None
if value is not None and value >= 0.80:
```

### Files to Modify

| File | Errors | Issue |
|------|--------|-------|
| `app/shared/formatting.py` | 13 | Empty set `categories = set()` |
| `app/core/openrouter.py` | 3 | Empty list `filtered = []` |
| `app/demand/briefing_extraction.py` | 4 | Empty lists `formatted_lines = []` |
| `app/demand/services/interview_trends.py` | 1 | Empty dict `trends = {}` |
| `app/demand/services/scraper_service.py` | 1 | Optional comparison `>=` on None |
| `app/demand/temporal.py` | 4 | Type inference in nested dict access |
| `app/demand/email_builder.py` | 1 | Jinja2 filter type |
| `app/core/model_monitoring.py` | 1 | Block list type annotation |

---

## Task Checklist

**For build agent:** Copy these to TodoWrite at start, update in real-time during build, then sync back to this file when complete.

- [ ] **TASK 1:** Fix `formatting.py` - Add type annotation to `categories` set
- [ ] **TASK 2:** Fix `openrouter.py` - Add type annotation to `filtered` list
- [ ] **TASK 3:** Fix `briefing_extraction.py` - Add type annotations to both `formatted_lines` lists
- [ ] **TASK 4:** Fix `interview_trends.py` - Add type annotation to `trends` dict
- [ ] **TASK 5:** Fix `scraper_service.py` - Add explicit None check before comparison
- [ ] **TASK 6:** Fix `temporal.py` - Add type annotations and None checks
- [ ] **TASK 7:** Fix `email_builder.py` and `model_monitoring.py` - Type casts for complex types

**After all tasks:**
- [ ] L1: Format & Lint (ruff)
- [ ] L2: Type Checking (mypy + pyright)
- [ ] L3: Tests (pytest)
- [ ] L4: End-to-End validation
- [ ] L5: Production Readiness

---

## Tasks (Detailed Implementation)

### TASK 1: [PARALLEL] Fix `formatting.py` set type

**File:** `app/shared/formatting.py`
**Line:** 653

**Current code:**
```python
categories = set()
```

**Fix:**
```python
categories: set[str] = set()
```

**Verification:** This fixes 13 cascading errors (add, len, list conversion).

---

### TASK 2: [PARALLEL] Fix `openrouter.py` list type

**File:** `app/core/openrouter.py`
**Line:** 125-143

**Current code:**
```python
def filter_models_by_provider(models: list[dict[str, Any]], providers: list[str]) -> list[dict[str, Any]]:
    filtered = []
```

**Fix:**
```python
def filter_models_by_provider(models: list[dict[str, Any]], providers: list[str]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
```

**Verification:** This fixes 3 cascading errors (append, len, return).

---

### TASK 3: [PARALLEL] Fix `briefing_extraction.py` list types

**File:** `app/demand/briefing_extraction.py`
**Lines:** 315-337 (two functions)

**Function 1 - `_format_requirements`:**
```python
# Current
formatted_lines = []

# Fix
formatted_lines: list[str] = []
```

**Function 2 - `_format_questions`:**
```python
# Current
formatted_lines = []

# Fix
formatted_lines: list[str] = []
```

**Verification:** This fixes 4 cascading errors (2 append + 2 join).

---

### TASK 4: [PARALLEL] Fix `interview_trends.py` dict type

**File:** `app/demand/services/interview_trends.py`
**Line:** ~72-78

**Current code:**
```python
def get_role_trends(roles: list[Role], changes: dict[int, list[RoleChange]]) -> dict[int, str]:
    trends = {}
```

**Fix:**
```python
def get_role_trends(roles: list[Role], changes: dict[int, list[RoleChange]]) -> dict[int, str]:
    trends: dict[int, str] = {}
```

**Verification:** This fixes 1 error (return type mismatch).

---

### TASK 5: [PARALLEL] Fix `scraper_service.py` optional comparison

**File:** `app/demand/services/scraper_service.py`
**Line:** ~413

**Current code:**
```python
if role.is_qualified and role.combined_score and role.combined_score >= 0.80:
```

**Fix:**
```python
if role.is_qualified and role.combined_score is not None and role.combined_score >= 0.80:
```

**Reasoning:** Pyright's type narrowing doesn't fully eliminate None with truthiness check before `>=`. Explicit `is not None` is clearer and type-safe.

---

### TASK 6: [PARALLEL] Fix `temporal.py` type inference

**File:** `app/demand/temporal.py`
**Lines:** 40-51 (function `_extract_field`)

**Current code:**
```python
def _extract_field(data: dict[str, Any], field: str) -> Any:
    if "." in field:
        parts = field.split(".")
        value: Any = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    return data.get(field)
```

**Fix:** The function is already typed with `Any`, but the intermediate `value.get(part)` returns `Unknown`. Add explicit type annotation:

```python
def _extract_field(data: dict[str, Any], field: str) -> Any:
    if "." in field:
        parts = field.split(".")
        value: Any = data
        for part in parts:
            if isinstance(value, dict):
                result: Any = value.get(part)
                value = result
            else:
                return None
        return value
    return data.get(field)
```

---

### TASK 7: Fix `email_builder.py` and `model_monitoring.py`

**File 1:** `app/demand/email_builder.py`
**Line:** 48

**Issue:** Jinja2 filter assignment type mismatch.

**Fix:** Add type cast or use `Any`:
```python
from typing import Any, cast, Callable

# In the filter assignment section:
self.env.filters["format_salary"] = cast(Callable[..., str], format_salary)
```

**Alternative:** If the cast is too verbose, Pyright allows inline ignore:
```python
self.env.filters["format_salary"] = format_salary  # pyright: ignore[reportArgumentType]
```

**File 2:** `app/core/model_monitoring.py`
**Line:** 233

**Issue:** Block list type mismatch with Slack API types.

**Fix:** Annotate blocks list:
```python
blocks: list[dict[str, Any]] = []
```

---

## Testing

### Unit Tests
- No new tests required - this is type annotation only
- Existing tests must continue to pass

### Integration Tests
- Run full test suite to ensure no behavioral changes

---

## Validation

Run AFTER all tasks complete. Execute in order L1-L5.

### L1: Format & Lint
```bash
uv run ruff format app/
uv run ruff check app/
```

### L2: Type Checking
```bash
uv run mypy app/
uv run pyright app/
```

**Expected outcome:** 0 errors from both checkers.

### L3: Tests
```bash
uv run pytest -v
```

**Expected outcome:** All 186+ tests pass.

### L4: End-to-End

```bash
# Verify API still works
curl http://localhost:8123/health
```

### L5: Production Readiness

```bash
# Quick sanity check - no runtime errors
uv run python -c "from app.main import app; print('Import OK')"
```

---

## Acceptance Criteria

- [ ] All tasks implemented
- [ ] L1-L5 validation passes
- [ ] MyPy: 0 errors
- [ ] Pyright: 0 errors in production code
- [ ] All 186+ tests pass
- [ ] No behavioral changes

---

## Notes

**Why these changes are safe:**
- Adding type annotations doesn't change runtime behavior
- Python ignores type hints at runtime
- All changes are purely for static analysis

**Trade-offs:**
- Using `Any` in some places (Jinja2 filters) trades strictness for pragmatism
- Could use more specific types, but `Any` is acceptable per standards when external library lacks stubs

---

## Build Notes

[Document during implementation]

---

## Validation Results

[Populate after running L1-L5 validation]

---

## Build Summary (output when complete)

After completing all tasks and validation:
1. **Update Task Checklist above** with [x] for completed tasks
2. **Fill in Build Notes** section with key decisions and deviations
3. **Fill in Validation Results** section with L1-L5 status
4. **Output this summary** to the user
