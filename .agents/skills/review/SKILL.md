---
name: review
description: Review code changes for correctness, security, performance, and compliance with project architecture rules.
---

# Code Review

## Task

Review the most recent code changes, focusing on:

1. Whether the business logic matches the intent described in the pull request (PR).
2. Potential security vulnerabilities, including SQL injection, cross-site scripting (XSS), and unvalidated input.
3. Performance issues, including N+1 queries and unnecessary re-rendering.
4. Compliance with the architecture rules defined in `AGENTS.md`.

## Output Format

Classify the review using one of the following outcomes:

- **PASS** — No issues found.
- **WARN** — Non-blocking issues were found; recommend improvements.
- **FAIL** — Issues requiring fixes were found; include a suggested fix for each.
