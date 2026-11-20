# CI Failure Diagnosis

## Goal and scope

Document how to identify and reproduce failing CI jobs while leaving the existing [issue-fix workflow](../../../.agents/skills/fix-issue/SKILL.md) responsible for code changes and regression tests. The [PR skill](../../../.agents/skills/create-pr/SKILL.md) owns the final push checks. The [third-batch workflow exercise](../completed/architecture-validation-and-development-workflow.md) reproduced the same Node command locally and had no remote failure on the replacement runs. Use the [CI jobs](../../../.github/workflows/ci.yml) and [CodeQL workflow](../../../.github/workflows/codeql.yml) to map the current entry points.

## Milestones

1. Walk through a historical run and capture the PR, head SHA, run attempt, job, first failing step, and diagnostic. Start with `gh pr checks <number>` and `gh run view <run-id> --log-failed`. Use the [historical Trivy failure](https://github.com/Phoxine/gomoku/actions/runs/42974528644) as a starting example. Separate failed Actions jobs from pending checks and review requirements. Record only the relevant sanitized log lines.
2. Add a CI failure reference under `.agents/skills/fix-issue/references/` and link it where diagnostic work starts. Cover Ruff, pytest, the Node interaction suite, the Markdown checker, runner or Docker startup, and scanner or external service failures. Give the branch-specific local command for reproducible checks and record differences between local Compose and GitHub runners. Run the exact first failing command before changing code. For a transient provider issue, document the evidence before considering an authorized rerun against the same SHA. Leave the original failure in the record.
3. Validate a reproducible case and a transient or setup fixture. A normal regression should fail for the same reason before the fix and pass afterward. A setup fixture should identify the failing stage and recover without changing app code or weakening checks. When a local reproduction is unavailable, document the closest evidence and the observed result of the next permitted CI attempt.

## Acceptance and pull requests

- **Issue-fix reference PR.** Link the reference from the existing skill instead of introducing a competing skill trigger. Follow the [skill validation workflow](../../../.agents/skills/validate-skill/SKILL.md). Demonstrate that the reference directs a contributor to the correct command and produces a distinct recommendation for each fixture. Include local steps, examples, and the evidence to record. No dependency on the coverage-publication or browser-test plans.
- If follow-up automation is warranted, open a separate PR with representative passing and rejected cases. Keep diagnosis and retry decisions human-reviewable.

If the environment differs from CI, preserve the original log and tested SHA, then follow the [Compose recovery guide](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) in the affected worktree. Check the relevant Actions run again after pushing a fix.

## Validation and delivery

Work from a dedicated checkout for implementation. Record `git status --short` and `git rev-parse HEAD` before starting. If tests need the app, initialize and start an isolated stack using the [worktree skill](../../../.agents/skills/create-worktree/SKILL.md). Run `bash scripts/check-docs.sh` after staging Markdown changes. Complete [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing) and confirm the Stop hook did not skip formatting, lint, or tests. Follow the [post-push cleanup procedure](../../../.agents/skills/create-pr/SKILL.md#4-push-the-branch).

## Progress and decisions

- [x] 2026-11-20. Reviewed the existing workflow and defined scope at `eff8579`.
- [ ] Classify a historical failure and inventory the reproducible commands.
- [ ] Draft the reference and verify the test and environment cases.

## Outcomes and retrospective

Pending execution. Record the walkthrough results, owner, and remaining follow-up before moving this plan to `docs/exec-plans/completed/`.
