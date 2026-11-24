# CI Failure Diagnosis

## Goal and scope

Document how to identify and reproduce failing CI jobs while leaving the existing [issue-fix workflow](../../../.agents/skills/fix-issue/SKILL.md) responsible for code changes and regression tests. The [PR skill](../../../.agents/skills/create-pr/SKILL.md) owns the final push checks. The [third-batch workflow exercise](architecture-validation-and-development-workflow.md) reproduced the same Node command locally and had no remote failure on the replacement runs. Use the [CI jobs](../../../.github/workflows/ci.yml) and [CodeQL workflow](../../../.github/workflows/codeql.yml) to map the current entry points.

## Milestones

1. Walk through a historical run and capture the PR, head SHA, run attempt, job, first failing step, and diagnostic. Follow the [failed-attempt procedure](../../../.agents/skills/fix-issue/references/ci-failure-diagnosis.md#find-the-failed-attempt) to locate attempt-specific job metadata and inspect safe job output. Use the [historical Trivy failure](https://github.com/Phoxine/gomoku/actions/runs/42974528644) as a starting example. Separate failed Actions jobs from pending checks and review requirements. Record only the relevant sanitized log lines.
2. Add a CI failure reference under `.agents/skills/fix-issue/references/` and link it where diagnostic work starts. Cover Ruff, pytest, the Node interaction suite, the Markdown checker, runner or Docker startup, and scanner or external service failures. Give the branch-specific local command for reproducible checks and record differences between local Compose and GitHub runners. Run the exact first failing command before changing code. For a transient provider issue, document the evidence before considering an authorized rerun against the same SHA. Leave the original failure in the record.
3. Validate a reproducible case and a transient or setup fixture. A normal regression should fail for the same reason before the fix and pass afterward. A setup fixture should identify the failing stage and recover without changing app code or weakening checks. When a local reproduction is unavailable, document the closest evidence and the observed result of the next permitted CI attempt.

## Acceptance and pull requests

- **Issue-fix reference PR.** Link the reference from the existing skill instead of introducing a competing skill trigger. Follow the [skill validation workflow](../../../.agents/skills/validate-skill/SKILL.md). Demonstrate that the reference directs a contributor to the correct command and produces a distinct recommendation for each fixture. Include a run or fixture with an earlier failed attempt and a later passing attempt. Verify that the documented steps select the earlier failure and its first failing step. Include local steps, examples, and the evidence to record. No dependency on the coverage-publication or browser-test plans.
- If follow-up automation is warranted, open a separate PR with representative passing and rejected cases. Keep diagnosis and retry decisions human-reviewable.

If the environment differs from CI, record the original log link, sanitized diagnostic, and tested SHA. Follow the [Compose recovery guide](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) in the affected worktree. Check the relevant Actions run again after pushing a fix.

## Validation and delivery

Work from a dedicated checkout for implementation. Record `git status --short` and `git rev-parse HEAD` before starting. If tests need the app, initialize and start an isolated stack using the [worktree skill](../../../.agents/skills/create-worktree/SKILL.md). Run `bash scripts/check-docs.sh` after staging Markdown changes. Complete [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing) and confirm the Stop hook did not skip formatting, lint, or tests. Follow the [post-push cleanup procedure](../../../.agents/skills/create-pr/SKILL.md#4-push-the-branch).

## Progress and decisions

- [x] 2026-11-20. Reviewed the existing workflow and defined scope at `eff8579`.
- [x] 2026-11-24. Classified the historical Trivy failure and checked the local command map against the CI and CodeQL workflows.
- [x] 2026-11-24. Added the [CI diagnosis reference](../../../.agents/skills/fix-issue/references/ci-failure-diagnosis.md) to the issue-fix skill and validated the regression, setup, and earlier-attempt paths.

## Outcomes and retrospective

- [PR #1, Actions run 42974528644](https://github.com/Phoxine/gomoku/actions/runs/42974528644/attempts/1), head `84db9bd59661b00ad96c4e14b6e5967380dbce74`. Attempt 1 first failed in the Docker Vulnerability Scan job at step 4, **Run Trivy vulnerability scanner**. The log showed high-severity findings and exit status 1, which called for scanner finding triage.
- Replayed the [PR #67 clipboard regression](https://github.com/Phoxine/gomoku/pull/67) in temporary files with the same Node test command before and after the fix. The denied-write test first failed with the connection-error message, then all nine tests passed.
- In the isolated implementation worktree, the Ruff command first exited with `service "app" is not running`. After starting that worktree's stack, the same command passed without a code change. The workflow's pytest coverage command passed all 235 tests.
- An independent offline fixture returned a passing attempt 2 and a failed attempt 1 on the same SHA. The documented commands selected attempt 1 and the earliest failed step, **Start Environment**, and routed it to setup recovery. Pending and external checks and a plain issue followed their own paths. The fixture did not rerun GitHub Actions.

The maintainer diagnosing a failure records the evidence and chooses the next action within the available authorization. The reference lives in `fix-issue`. Consider a separate automation PR if repeated use reveals a specific need.
