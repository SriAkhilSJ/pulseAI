---
name: commit-message
description: Write a clear, conventional-commits-style commit message for the currently staged/changed files. Use when the user asks for a commit message or wants help committing.
---
Write a commit message following the Conventional Commits format:

    <type>(<optional scope>): <short summary, imperative mood, no period>

    <optional longer body explaining WHY, not just what>

Valid types: feat, fix, docs, style, refactor, test, chore.

Steps:
1. Run `git_diff` (or `git_status` first if you need to see which files changed) to see the REAL staged/unstaged changes -- never invent what changed.
2. Base the summary line on what the diff ACTUALLY shows, not on the user's request text alone.
3. Keep the summary line under 72 characters.
4. If the change is genuinely complex, add a body explaining the reasoning, not a restatement of the diff.
