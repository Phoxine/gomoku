# Scheduled Documentation Audits

## Goal and scope

Make the existing manual audit repeatable on a schedule. A run should identify claims that need verification, show the underlying evidence, and leave a report a maintainer can act on. Start with the [audit checklist and records](../../documentation-audit.md), [documentation index](../../index.md), and [current PR CI](../../../.github/workflows/ci.yml). The [Harness Engineering article](https://openai.com/index/harness-engineering/#we-made-repository-knowledge-the-system-of-record) describes recurring documentation maintenance.

## Milestones

1. Repeat the full audit against a recorded commit. Run `bash scripts/check-docs.sh` and cross-check at least one product claim and one design claim against the linked implementation or tests. Compare findings with the previous complete audit. Record the pages read, evidence, time required, and cases that still need judgment.
2. If the audit proves repeatable, define a read-only scheduled workflow and an on-demand trigger. Reuse the current Markdown check. Where a claim requires interpretation, record the source checked and whether a reviewer can confirm it. A report should contain the commit, affected page, expected behavior, observed evidence, and suggested follow-up. Test publication with a local scratch report or a nonpublishing dry run before enabling any scheduled output.
3. After the reporting workflow lands on the default branch, observe its first scheduled run and compare its findings with a manual audit of the same commit. Test the on-demand trigger at that point. Consider a separate correction workflow after the reports demonstrate reliable findings. Scope any authorized correction PR to one finding and have the normal documentation checks review it. [GitHub Actions trigger behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## Acceptance and pull requests

- **Audit baseline and reporting PR.** Before merge, demonstrate a clean dry run and a fixture with a valid link but a deliberately stale behavior claim. The structural checker should still pass the latter and the report should identify the claim and its conflicting evidence. If adding executable CI tooling, include version-controlled passing and rejected cases in the relevant job. Record the workflow name, trigger, and report location. After merge, record the first scheduled run and its comparison with the manual audit.
- **Optional correction PR workflow.** Proceed only after the report workflow lands and reliable findings have been observed. Keep normal review on proposed corrections and obtain authorization before enabling automatic external writes. Demonstrate that a dry run creates no external artifact and a permitted run proposes exactly the documented change.

Rerun the original workflow run to reproduce a failed report at the same commit. If no scheduled run started, run an on-demand audit and record its commit before comparing reports. If scheduling or reporting is unreliable, disable the trigger and continue the existing manual audit. Preserve findings that already have a maintainer follow-up.

## Worktree and recovery

Run commands from this plan's dedicated worktree. Record `git status --short` and `git rev-parse HEAD` before starting. When the work needs Django and PostgreSQL, run `bash scripts/init-worktree-env.sh` and `bash scripts/compose.sh up --build -d`. Confirm `app` is listed by `bash scripts/compose.sh ps --status running --services`. If startup is interrupted, inspect `bash scripts/compose.sh ps -a` and follow the [Compose troubleshooting guide](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) before retrying in the same worktree.

Run `bash scripts/check-docs.sh` after staging documentation changes. Use the full [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Confirm Ruff formatting, Ruff lint, and pytest completed.

If the hook reports `Skipping final validation`, address the stated cause. If the tracked `compose.yaml` is accidentally missing, confirm the deletion with `git status --short` and restore the file from the intended commit. If the root `.env` is missing or has no project name, run `bash scripts/init-worktree-env.sh` for a fresh worktree. For a previously initialized worktree, recover its original project name and local credentials before retrying so its database volume remains attached. Stop if the original settings cannot be recovered. Once the configuration is valid, start the intended stack as described above, confirm `app` is running, and rerun the hook.

After pushing, use `bash scripts/stop-local-stack.sh` for a path-bound Compose project. For a legacy or directory-default project rejected by the helper, verify that the project belongs to this worktree before running `bash scripts/compose.sh down` from the same checkout. Both paths retain the database volume. See the [post-push cleanup procedure](../../../.agents/skills/create-pr/SKILL.md#4-push-the-branch).

## Progress and decisions

- [x] 2026-11-20. Defined scope and acceptance from baseline `eff8579`.
- [ ] Repeat the manual audit and agree on report evidence.
- [ ] Validate the read-only report and record the scheduling decision.
- [ ] Observe a scheduled run and record whether correction automation is justified.

## Outcomes and retrospective

Pending implementation or adoption review. Record the evidence, decisions, open gaps, and follow-up before moving this plan to `docs/exec-plans/completed/`.
