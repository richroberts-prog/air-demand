---
type: standard
description: YAML frontmatter schema and type taxonomy for all documentation
tags: [documentation, standards, metadata, schema]
---

# YAML Frontmatter Schema

## Base (ALL documents)

```yaml
---
type: string              # task | command | adr | guide | spec | standard | learning
description: string       # one-line purpose
tags: [string]            # discovery keywords (supply, demand, q1, q2, infrastructure, etc.)
---
```

## Commands (optional additions)

```yaml
argument-hint: string     # [issue-id], [path-to-plan], etc.
allowed-tools: string     # Bash(git:*), Read, Write, Edit, etc.
model: string            # claude-3-5-haiku-20241022, etc.
```

---

## Type Taxonomy

| Type | Purpose | Location |
|------|---------|----------|
| `task` | Implementation work | `.claude/tasks/` |
| `command` | Slash commands | `.claude/commands/` |
| `adr` | Architecture decisions | `.claude/adrs/` |
| `guide` | How-to documentation | `docs/guides/` |
| `spec` | Requirements definitions | `docs/specs/` |
| `standard` | Reusable patterns | `docs/standards/` |
| `learning` | Lessons learned | `docs/learnings/` |

---

## Examples

### Task

```yaml
---
type: task
description: Extract location features from LinkedIn profiles
tags: [supply, q1, extraction, location]
---
```

### Command

```yaml
---
type: command
description: Build feature by executing implementation plan
tags: [workflow, validation]
argument-hint: [path-to-plan]
allowed-tools: Read, Write, Edit, Bash
model: claude-sonnet-4-5
---
```

### ADR

```yaml
---
type: adr
description: Vertical slice implementation approach with validation checkpoints
tags: [architecture, implementation, vertical-slice, pydantic-ai]
---
```

### Guide

```yaml
---
type: guide
description: Digital Ocean deployment workflow and server management
tags: [deployment, infrastructure, digital-ocean]
---
```

### Spec

```yaml
---
type: spec
description: Q1 qualification requirements and gate definitions
tags: [supply, q1, requirements, qualification]
---
```

### Standard

```yaml
---
type: standard
description: Agent tool docstring format and best practices
tags: [agents, documentation, pydantic-ai]
---
```

### Learning

```yaml
---
type: learning
description: Common mistakes and fixes consolidated across all features
tags: [lessons-learned, best-practices, troubleshooting]
---
```

---

## Migration Notes

**Directory renames required:**
- `.claude/plans/` → `.claude/tasks/`
- `.claude/decisions/` → `.claude/adrs/`

**Field consolidation:**
- `applies_to` → use `tags` instead
- `summary` → use `description`
- `name` → use filename
- `project` → use `tags`
