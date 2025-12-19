---
type: guide
description: Architecture Decision Records directory
tags: [adr, architecture, decisions, documentation]
---

# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records (ADRs) - documents that capture important architectural decisions made during the development of Air Demand.

## Purpose

ADRs help us:
- Document the "why" behind architectural choices
- Understand context for future decision-making
- Avoid revisiting already-decided issues
- Onboard new team members with historical context

## Format

Each ADR should follow this structure:

```markdown
---
type: adr
description: {One-line summary of the decision}
tags: [adr, {relevant}, {tags}]
date: YYYY-MM-DD
status: proposed | accepted | deprecated | superseded
---

# ADR-NNN: {Title}

## Status

{proposed | accepted | deprecated | superseded by ADR-XXX}

## Context

{What is the issue we're trying to solve? What forces are at play?}

## Decision

{What did we decide? In active voice: "We will..."}

## Consequences

**Positive:**
- {What improves?}

**Negative:**
- {What are the trade-offs?}

**Neutral:**
- {What else changes?}

## Alternatives Considered

- **Option A**: {Why not chosen}
- **Option B**: {Why not chosen}

## References

- {Links to relevant docs, discussions, or code}
```

## Naming Convention

```
ADR-001-use-vertical-slice-architecture.md
ADR-002-choose-postgresql-over-mongodb.md
ADR-003-structured-logging-with-structlog.md
```

## Examples of ADR-worthy Decisions

- Choosing a database (PostgreSQL vs MongoDB)
- Architectural patterns (Vertical Slice vs Layered)
- Technology selections (Pydantic vs Marshmallow)
- API design patterns (REST vs GraphQL)
- Authentication/authorization approaches
- Deployment strategies
- Monitoring/observability tools

## When to Write an ADR

Write an ADR when:
- The decision has significant long-term impact
- Multiple valid options exist
- Future you will wonder "why did we choose this?"
- The decision constrains future choices
- You're about to have a debate about the best approach

## Related Documentation

- `docs/standards/` - How we implement decisions (technical standards)
- `.claude/tasks/completed/` - Implementation history
- `docs/learnings/` - What we learned from our decisions
