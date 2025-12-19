---
type: command
description: Audit all type suppressions and linting ignores, provide resolution recommendations
tags: [code-quality, type-safety, technical-debt]
---

# Check Ignore Comments Command

Find all noqa/type:ignore comments in the codebase, investigate why they exist, and provide recommendations for resolution or justification.

Create a markdown report file (create the reports directory if not created yet): `.agents/reports/ignore-comments-report-{YYYY-MM-DD}.md`

## Report Format

For each suppression found, create a section in the report:

**Why it exists:**
{explanation of why the suppression was added}

**Options to resolve:**

1. {Option 1: description}
   - Effort: {Low/Medium/High}
   - Breaking: {Yes/No}
   - Impact: {description}

2. {Option 2: description}
   - Effort: {Low/Medium/High}
   - Breaking: {Yes/No}
   - Impact: {description}

**Tradeoffs:**

- {Tradeoff 1}
- {Tradeoff 2}

**Recommendation:** {Remove | Keep | Refactor}
{Justification for recommendation}

---

{Repeat for each comment}
