---
type: command
description: Execute implementation plan tasks, run L1-L5 validation, append build notes and results to plan
tags: [build, implementation, validation, execution]
allowed-tools: Read, Glob, Grep, Task, Bash, Edit, Write, TodoWrite, AskUserQuestion
---

# /build

## Input

```
/build .claude/tasks/{plan}.md
```

ARGUMENTS: $ARGUMENTS

---

## Requirements (NON-NEGOTIABLE)

- **All tasks MUST be completed** - Do not stop partway
- **All validations MUST pass** - Fix failures before proceeding, do not skip
- **Run validations automatically** - Do not prompt user to run them
- **E2E testing MUST pass** - L4 is not optional
- **No partial completion** - Either fully done or report blockers

---

## Process

### 1. Initialize

- Read the ENTIRE plan
- Create TodoWrite list from tasks (all "pending")
- Note validation commands

### 2. Execute Tasks

For each task:

| Step | Action |
|------|--------|
| Prepare | Mark "in_progress" via TodoWrite, read relevant files |
| Implement | Follow plan exactly, maintain patterns, include types |
| Verify | Check syntax/imports, mark "completed" via TodoWrite |
| Document | Note any significant decisions or deviations for Build Notes |

Update TodoWrite immediately after each task (don't batch).

### 2.5 Append Build Notes to Plan File

After completing all tasks (before validation), append Build Notes to the plan file:

**Append to plan file under "## Build Notes" section:**

```markdown
## Build Notes

### Implementation Date
{date}

### Key Decisions Made
- {Decision 1: What was decided and why}
- {Decision 2: What was decided and why}

### Deviations from Plan
- {Deviation 1: What changed and rationale}
- {Deviation 2: What changed and rationale}

### Issues Encountered & Solutions
- **Issue**: {Problem description}
  - **Solution**: {How it was resolved}
  - **Location**: {file:line}

### Additional Patterns/Helpers
- {Any helpers or patterns added beyond plan}
```

**Only document significant items** - not every minor detail. Focus on decisions that future you (or another developer) would want to know.

### 3. Validation

Run ALL validation commands from plan in order (L1→L5):

```bash
# L1: Syntax & Style
uv run ruff format . && uv run ruff check .

# L2: Type Checking
uv run mypy app/ && uv run pyright app/

# L3: Tests
uv run pytest -v

# L4: E2E - As specified in plan

# L5: Production readiness - As specified in plan
```

**Dashboard Validation (if feature touches dashboard):**

If the feature modifies dashboard code, also run:

```bash
# Navigate to dashboard
cd dashboard

# TypeScript type checking
npx tsc --noEmit

# Dashboard tests
npm test

# Dashboard smoke tests
npm run test:smoke

# Production build validation
npm run build
```

If any fail: fix → re-run → continue only when passing.

### 3.5 Append Validation Results & Move to Completed

After ALL validation passes, append results to plan file and move to completed/:

**1. Append to plan file under "## Validation Results" section:**

```markdown
## Validation Results

### Validation Date
{date}

### L1: Format & Lint
✅ PASS
- ruff format: no changes needed
- ruff check: no errors

### L2: Type Checking
✅ PASS
- mypy: 0 errors
- pyright: 0 errors

### L3: Tests
✅ PASS
- {n} tests passed
- 0 failed

### L4: End-to-End
✅ PASS
{specific E2E validation results}

### L5: Production Readiness
✅ PASS
{specific production checks results}

### L6: Dashboard (if applicable)
✅ PASS / ⏭️ SKIPPED (no dashboard changes)
- TypeScript: no errors
- npm test: {n} tests passed
- smoke tests: {n}/{n} passed
- build: successful

### Fixes Applied (if any)
- {Any issues fixed during validation}
```

**2. Move plan file to completed/:**

```bash
mv {plan-file-path} .claude/tasks/completed/{plan-filename}
```

**3. Update output to reflect completion** (see Output section below)

---

## Output

### When Validation Passes (Success)

```
✅ Build Complete - All Validation Passed

Plan: {path}
Tasks: {total}/{total} ✓

Files Changed:
  Created: {list}
  Modified: {list}

Validation: ALL PASS ✓
  L1 Syntax:    ✅ PASS
  L2 Types:     ✅ PASS
  L3 Tests:     ✅ PASS ({n} passed)
  L4 E2E:       ✅ PASS
  L5 Prod:      ✅ PASS
  L6 Dashboard: ✅ PASS / ⏭️ SKIPPED

Plan Status:
  ✓ Build Notes appended ({n} decisions documented)
  ✓ Validation Results appended
  ✓ Plan moved: tasks/{filename} → tasks/completed/{filename}

Ready for commit: YES

Next steps:
  /commit                    # Commit the feature
  /system:retro (optional)   # Reflect and capture learnings
```

### When Validation Fails (Blocked)

```
❌ Build Incomplete - Validation Failed

Plan: {path}
Tasks: {completed}/{total}

Files Changed:
  Created: {list}
  Modified: {list}

Validation: FAILED
  L1 Syntax:    PASS/FAIL
  L2 Types:     PASS/FAIL
  L3 Tests:     PASS/FAIL ({n} passed, {n} failed)
  L4 E2E:       PASS/FAIL
  L5 Prod:      PASS/FAIL
  L6 Dashboard: PASS/FAIL/SKIPPED

Blockers:
- {what failed and why}
- {what needs to happen to fix}

Plan Status:
  ✓ Build Notes appended (partial completion documented)
  ✓ Validation Results appended (with failures)
  ⚠ Plan remains in tasks/ (not moved to completed/)

Ready for commit: NO

Next steps:
  # Fix the issues above, then:
  /build {plan-path}  # Re-run to complete validation
```
