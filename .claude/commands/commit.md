---
type: command
description: Create atomic commit with conventional commit message, optionally push to remote
tags: [git, workflow, automation]
argument-hint: [--push]
---

# Commit Command

Create a new commit for all uncommitted changes with a conventional commit message.

## Steps

1. **Analyze changes:**
   - Run `git status && git diff HEAD && git status --porcelain` to see what files are uncommitted
   - Review the changes to understand the scope

2. **Stage changes:**
   - Add untracked and changed files with `git add -A`

3. **Create commit:**
   - Write an atomic commit message with appropriate conventional commit type (feat, fix, docs, refactor, etc.)
   - Include descriptive summary and context
   - Add Claude Code attribution footer

4. **Push (if --push flag provided):**
   - If user invoked `/commit --push`, push to remote after successful commit
   - Run `git push` only after commit succeeds
   - Report push status to user
