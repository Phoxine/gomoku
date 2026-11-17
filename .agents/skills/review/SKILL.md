---
name: review
description: Review code changes for correctness, security, performance, and compliance with project architecture rules.
---

# Code Review

## Task

Determine the requested review scope and inspect all relevant changes, including task commits, staged and unstaged changes, and relevant untracked files. For task-branch work, compare against the intended base; do not assume the latest commit represents the whole task. Focus on:

1. Whether the business logic matches the task or pull request intent.
2. Potential security vulnerabilities, including SQL injection, cross-site scripting (XSS), and unvalidated input.
3. Performance issues, including N+1 queries and unnecessary re-rendering.
4. Compliance with the architecture rules defined in `AGENTS.md`.

## Output Format

Classify the review using one of the following outcomes:

- **PASS** — No issues found.
- **WARN** — Non-blocking issues were found; recommend improvements.
- **FAIL** — Issues requiring fixes were found; include a suggested fix for each.

## Remediation loop

For implementation work, address actionable review findings and request a fresh
review of the changes. Repeat until no blocking findings remain, with at most
five remediation and re-review cycles. If the fifth re-review still fails,
report each remaining finding and why it could not be resolved. Record any
unresolved non-blocking findings and their rationale in the final report. If a
finding cannot be resolved, report the blocker rather than treating the review
as passed.
