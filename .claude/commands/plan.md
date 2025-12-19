---
type: command
description: Plan a feature with context-rich implementation plan
tags: [planning, research, implementation, context]
allowed-tools: Read, Glob, Grep, Task, WebSearch, WebFetch, AskUserQuestion, Write
---

# /plan

## Input

```
/plan {feature description}
```

ARGUMENTS: $ARGUMENTS

---

## Process

### 1. Clarify

Ask user about implementation approach BEFORE researching:
- Architectural choices
- Library preferences
- Scope boundaries
- Any ambiguities in the request

### 2. Load Historical Context

**Use Sub-Agents for Parallel Discovery:**

Launch Task(explore:*) agents in parallel to discover relevant context across document types:

```
Task 1: Find standards relevant to {feature area}
Task 2: Find ADRs relevant to {feature area}
Task 3: Find learnings relevant to {feature area}
```

**Progressive Disclosure Pattern:**

All documentation has YAML frontmatter. Use it to efficiently find and extract relevant context:

```bash
# Step 1: Find candidates by type and tags
grep -r "tags:.*{feature-tag}" docs/ .claude/

# Step 2: Assess relevance from frontmatter (first 10 lines)
head -10 {candidate-file}

# Step 3: Read full file if relevant
# Step 4: EXTRACT relevant sections to include in plan (don't just reference!)
```

**Target documents:**
- `type: standard` - Technical patterns and conventions (docs/standards/)
- `type: adr` - Architectural decisions and constraints (docs/adr/)
- `type: learning` - Common mistakes and fixes (docs/learnings/)
- `type: spec` - Feature specifications and requirements (docs/specs/)
- `type: task` - Completed implementation plans (.claude/tasks/completed/)

**Workflow:**
1. Use frontmatter tags to discover relevant docs
2. Read identified docs fully to understand context
3. **Extract and include** the specific sections needed for THIS task
4. Add reference links for "complete details" but ensure plan is self-contained

**Note:** Skip `CLAUDE.md` (already loaded in session context)

**CRITICAL - Make Plans Self-Contained:**

Don't just reference documents - **extract the relevant sections and include them directly in the plan**. A build agent should be able to implement the feature by reading ONLY the plan file.

Extraction guidelines:
- Include essential data structures, schemas, requirements directly
- Include code patterns and examples inline
- Add reference links for "full details" but ensure plan is implementable without them
- Be ruthless: only include what's needed for THIS specific task

### 3. Research

**Use Sub-Agents for Parallel Research:**

Launch multiple explore agents in parallel to gather context without blocking:

```
Task 1: Explore app/core/ infrastructure patterns
Task 2: Explore feature directory structure
Task 3: Web search for {library} best practices
```

**Codebase (read, don't execute):**
- `docs/standards/` - Use frontmatter tags to find relevant standards
- `docs/adr/` - Architectural decisions and constraints
- `.claude/tasks/completed/` - Past implementation patterns and decisions
- `app/core/` - Infrastructure patterns (config, database, logging, health, middleware)
- `app/demand/` - Demand-side feature patterns (roles, scraping, scoring, qualification)
- `app/shared/` - Cross-feature utilities (pagination, timestamps, error schemas)
- `dashboard/` - Next.js dashboard patterns (if feature touches UI)
- Skip other feature directories (vertical slice architecture)

**Online:**
- Official documentation (capture URLs with section anchors)
- Best practices and gotchas

### 4. Identify Pre-flight Checks (if needed)

For plans with external dependencies or production environment assumptions, identify 3-5 quick checks that validate assumptions before implementation:
- Dependency installed? Command to verify
- External service reachable? Command to test
- Disk space available? Command to check
- Historical data to calibrate thresholds? Command to analyze

Only include if checks are actionable and take <5 minutes total.

### 5. Write Plan

Save to: `.claude/tasks/{feature-name}.md`

Use template below. **MAXIMUM 10 TASKS** - if more needed, stop and ask user to split scope.

**CRITICAL - YAML Frontmatter:**
- `type: task` (always)
- `description:` One-line summary of what this delivers (not what it does)
- `tags:` Relevant discovery keywords (feature area, systems, tech stack)

**CRITICAL - Content:**
Incorporate historical context from step 2:
- Reference relevant architectural decisions
- List common mistakes to avoid
- Include validation requirements from learnings

### 6. Summary

Output to user after writing plan.

---

## Output (to user)

```
Plan: .claude/tasks/{filename}

Delivers:
{1-2 sentence summary synthesized from Overview Problem/Solution - what value does this plan provide?}

Tasks: {n}
Complexity: Low / Medium / High
Confidence: {1-10}/10 for one-pass success

{If pre-flight checks identified, include this section:}
Pre-flight checks (5 min, boosts confidence to 10/10):
  [ ] {Check 1}: {command}
  [ ] {Check 2}: {command}
  [ ] {Check 3}: {command}

Assumptions:
- {assumption 1} {← Validated by check #1, if applicable}
- {assumption 2}

Key risks:
- {risk 1}
- {risk 2}

Next: {If checks present: "Run checks above, then"} implement the plan
```

---

## Plan Template (written to file)

**CRITICAL**: The plan must be self-contained. An AI agent with NO conversation history must be able to read the plan file alone and fully implement + validate the feature without additional research.

```markdown
---
type: task
description: {one-line summary of what this feature delivers}
tags: [{relevant}, {feature}, {keywords}]
---

# Feature: {name}

## Execution Process

Follow these steps in order:

1. Read this entire plan
2. Create TodoWrite list from Task Checklist (all "pending")
3. Execute tasks, updating TodoWrite status in real-time
4. Run validation (L1→L5) after ALL tasks complete
5. Fix any failures, re-validate
6. **Sync progress**: Update Task Checklist in plan file with completion status
7. Output Build Summary (see end of plan)

**Why sync back to the plan?**
- TodoWrite tracks real-time progress during build
- Plan file provides permanent record of completion
- If build is interrupted, we can see partial completion in the plan

**Sub-Agent Strategy:**

Use sub-agents to maximize parallelization and minimize context pollution:

- **Independent tasks**: Launch parallel agents for tasks with no dependencies
- **Context isolation**: Use separate agents for research vs implementation
- **Parallel validation**: Run L1-L3 checks in parallel after implementation
- **Example**: If tasks 2, 3, 4 are independent, launch 3 agents in parallel

**Context Management:**

- Main session: TodoWrite tracking, coordination, final validation
- Sub-agents: Isolated research, independent implementations, parallel checks
- Return to main session: Integrate results, update todos, final synthesis

---

## Overview

| | |
|:--|:--|
| **Problem** | {what problem this solves} |
| **Solution** | {how this approach solves it} |
| **Type** | New Capability / Enhancement / Refactor / Bug Fix |
| **Complexity** | Low / Medium / High |
| **Systems** | {demand \| enrichment \| qualification \| scoring \| digest \| shared \| core \| dashboard} |
| **Dependencies** | {external libraries/services} |

---

## Context

**CRITICAL**: This section must be fully self-contained. Extract and include the essential information from specs, docs, and code patterns directly in the plan. The build agent should not need to read other files to understand what to build.

### Key Requirements & Specifications

**{Extract and include critical information here}**

Guidelines:
- If task requires understanding specific data structures → include them
- If task requires following specific patterns → include code examples
- If task requires domain knowledge → include relevant excerpts
- Always include reference links for "full details if needed"

### Files to Reference (optional supplementary reading)

| File | Lines | Why |
|------|-------|-----|
| `path/file.py` | X-Y or "ALL" | {reason - and note if key parts already extracted above} |

### Patterns to Follow

| Pattern | Example | File:Line |
|---------|---------|-----------|
| Error handling | `raise HTTPException(...)` | `app/features/routes.py:45` |
| Logging | `logger.info("event", **ctx)` | `app/core/logging.py:20` |

### External Documentation

| Resource | Section | Why |
|----------|---------|-----|
| [Title](url#anchor) | {section name} | {reason} |

### Standards to Respect

**From `docs/standards/` - constraints from architectural choices:**

- {Standard title}: {Key constraint or pattern}
- {Example: "Logging Standard: Use domain.component.action_state format"}

### Common Mistakes to Avoid

**Patterns that led to bugs or issues:**

- ❌ {Mistake}: {Brief description}
- ✅ {Correct approach}: {Why}

### Files to Create

| File | Purpose |
|------|---------|
| `path/file.py` | {purpose} |

---

## Task Checklist

**For build agent:** Copy these to TodoWrite at start, update in real-time during build, then sync back to this file when complete.

- [ ] **TASK 1:** {Brief one-line description}
- [ ] **TASK 2:** {Brief one-line description}
- [ ] **TASK 3:** {Brief one-line description}
- [ ] ...
- [ ] **TASK N:** {Brief one-line description}

**After all tasks:**
- [ ] L1: Format & Lint (ruff)
- [ ] L2: Type Checking (mypy + pyright)
- [ ] L3: Tests (pytest)
- [ ] L4: End-to-End validation
- [ ] L5: Production Readiness

---

## Tasks (Detailed Implementation)

MAXIMUM 10 TASKS. Ordered by dependency (top-to-bottom execution).

**Mark parallelizable tasks** with `[PARALLEL]` to enable sub-agent execution.

### TASK 1: {ACTION} {target}

- **Implement**: {specific detail}
- **Pattern**: `{file:line}` - {description}
- **Imports**: {required imports}
- **Gotcha**: {constraints to avoid}

### TASK 2: [PARALLEL] {ACTION} {target}

- **Implement**: {specific detail}
- **Dependencies**: None (can run parallel with Task 3, 4)
- **Pattern**: `{file:line}` - {description}

### TASK 3: [PARALLEL] {ACTION} {target}

- **Implement**: {specific detail}
- **Dependencies**: None (can run parallel with Task 2, 4)

...

---

## Testing

### Unit Tests
- {scope based on project standards}

### Integration Tests
- {scope based on project standards}

### Edge Cases
- {specific cases to test}

---

## Validation

Run AFTER all tasks complete. Execute in order L1→L5.

### L1: Format & Lint
```bash
uv run ruff format {directories}
uv run ruff check {directories}
```

### L2: Type Checking
```bash
uv run mypy {directories}
uv run pyright {directories}
```

### L3: Tests
```bash
uv run pytest {test_directories} -v
```

### L4: End-to-End

{Feature-specific E2E validation commands}

**Example validation requirements:**
- Test with real data samples
- Verify database round-trips
- Test null state handling
- Validate schema compatibility
- Measure performance

### L5: Production Readiness

{Accuracy validation, performance benchmarks, manual smoke test}

**Requirements:**
- Accuracy meets baseline (if applicable)
- Performance acceptable
- No regressions

---

## Acceptance Criteria

- [ ] All tasks implemented
- [ ] L1-L5 validation passes
- [ ] Test coverage meets requirements
- [ ] Follows project conventions
- [ ] No regressions
- [ ] Documentation updated (if applicable)

---

## Notes

{Additional context, design decisions, trade-offs, risks}

---

## Build Notes

[Document during implementation]

**Document during build:**
- Key decisions made during implementation
- Deviations from plan (with rationale)
- Issues encountered and solutions applied
- Helper functions or patterns added

---

## Validation Results

[Populate after running L1-L5 validation]

**Will contain:**
- L1-L5 validation status (PASS/FAIL)
- Any fixes applied to resolve failures
- Final metrics and performance data

---

## Build Summary (output when complete)

After completing all tasks and validation:
1. **Update Task Checklist above** with [x] for completed tasks
2. **Fill in Build Notes** section with key decisions and deviations
3. **Fill in Validation Results** section with L1-L5 status
4. **Output this summary** to the user:

```
## Build Complete: {feature name}

Plan: {plan file path}

### Completion

| Task | Status |
|------|--------|
| TASK 1: {description} | DONE / FAILED |
| TASK 2: {description} | DONE / FAILED |
| ... | ... |

### Validation

| Level | Status | Notes |
|-------|--------|-------|
| L1: Format & Lint | PASS/FAIL | {details if failed} |
| L2: Type Checking | PASS/FAIL | {details if failed} |
| L3: Tests | PASS/FAIL | {n} passed, {n} failed |
| L4: End-to-End | PASS/FAIL | {details} |
| L5: Production | PASS/FAIL | {details} |

### Files Changed

Created: {list}
Modified: {list}

### Assumptions Made

- {assumption 1}
- {assumption 2}

### Observations

- {learning or observation 1}
- {learning or observation 2}

### Ready for Commit

YES / NO (if NO, explain blockers)
```
```

---

## Task Limit

| Condition | Action |
|-----------|--------|
| ≤10 tasks | Proceed |
| >10 tasks | STOP and output error |

**Error format:**
```
SCOPE TOO BROAD - {N} tasks exceeds 10-task limit

Recommendation: Split into smaller plans

Option A: By layer
- Plan A: {description} ({X} tasks)
- Plan B: {description} ({Y} tasks)

Option B: By feature boundary
- Plan A: {description} ({X} tasks)
- Plan B: {description} ({Y} tasks)

Please choose a split or narrow scope.
```
