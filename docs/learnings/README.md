---
type: guide
description: Learnings and retrospectives directory
tags: [learnings, retrospectives, mistakes, best-practices, documentation]
---

# Learnings & Retrospectives

This directory captures lessons learned during development - the mistakes we made, the patterns that worked well, and the insights we gained.

## Purpose

Learnings help us:
- Avoid repeating mistakes
- Share knowledge across the team
- Improve AI-assisted development prompts
- Build institutional knowledge

## Format

Each learning document should follow this structure:

```markdown
---
type: learning
description: {One-line summary of the lesson}
tags: [learning, {area}, {technology}]
date: YYYY-MM-DD
severity: critical | important | minor
---

# Learning: {Title}

## What Happened

{Describe the situation or problem}

## What We Did Wrong

{The mistake, anti-pattern, or incorrect approach}

## Why It Happened

{Root cause analysis - why did we make this mistake?}

## What We Learned

{The key insight or lesson}

## Correct Approach

{How to do it right}

**Example:**
```python
# WRONG: {bad code}

# RIGHT: {good code}
```

## How to Prevent

{Changes to process, documentation, or tooling to prevent recurrence}

## Related

- ADR: {Link if relevant}
- Task: {Implementation where this occurred}
- Standard: {If we updated a standard because of this}
```

## Categories

### Bug Learnings
Bugs that taught us something valuable about the system.

### Performance Learnings
Optimizations discovered through profiling or production issues.

### Pattern Learnings
Design patterns that worked well or poorly.

### Tool Learnings
Discoveries about frameworks, libraries, or development tools.

### Process Learnings
Insights about our development workflow.

## Naming Convention

```
YYYYMMDD-async-context-managers-require-explicit-cleanup.md
YYYYMMDD-playwright-tests-need-deterministic-waits.md
YYYYMMDD-pydantic-validators-run-before-model-init.md
```

## When to Write a Learning

Write a learning when:
- You spent >2 hours debugging something non-obvious
- You found a gotcha that could bite someone else
- A pattern worked surprisingly well
- Something in production behaved unexpectedly
- You wish you'd known this before starting

## Related Documentation

- `docs/adr/` - Decisions we made
- `docs/standards/` - How we do things
- `.claude/tasks/completed/` - Implementation history
