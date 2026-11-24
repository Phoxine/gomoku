# Dependency and Security Update Triage

## Goal and scope

Provide one procedure for evaluating an existing dependency update or security alert. [Dependabot](../../../.github/dependabot.yml) already proposes GitHub Actions, uv, and Docker updates. [CI](../../../.github/workflows/ci.yml) runs secret, application, and image checks. The [Python image policy](../../development.md#python-container-image-updates) owns the matched digest pins. The gap is explaining how to decide on a proposed change and record the evidence across these checks.

## Milestones

1. Review examples of a routine dependency update and an image or security alert. The merged [psycopg update](https://github.com/Phoxine/gomoku/pull/41) and [proposed Python runtime update](https://github.com/Phoxine/gomoku/pull/38) are starting examples. For each, record the package or image, direct or transitive relationship, installed and proposed versions or digests, and affected paths. For an alert, read the advisory and official release notes, verify applicability to the version in the lockfile or rebuilt image, and record the fixed version or actionable reason for deferral. Keep report details limited to defensive impact and remediation.
2. Draft a short maintenance playbook near the existing project development guidance. Cover GitHub Actions pin verification, uv lockfile and manifest scope, Docker base-image and secondary pin checks, and review of unrelated changes. Treat a Python major/minor upgrade as a distinct compatibility decision. Keep new dependency approval in [AGENTS.md](../../../AGENTS.md). Link existing image-version and publishing procedures rather than duplicating them.
3. Verify one routine update and one advisory or scanner fixture without modifying protected credentials or production services. For an actual later update, rebuild the affected containers, run the full Stop hook, and inspect relevant CI checks on the new head. For a Python image change, also run `bash scripts/check-docs.sh`, compare both image pins, and check the CI scan for the original finding. Preserve before and after evidence or record that the advisory remains open.

## Acceptance and pull requests

- **Triage playbook PR.** Record the two walkthroughs and verify another maintainer can determine applicable versions, required approvals, validation commands, and the next action from the same evidence. Keep the playbook in project documentation initially. Add a standalone skill only if repeated use shows a distinct trigger and repeatable procedure.
- Deliver actual dependency or image updates in separate focused PRs. Keep routine updates independent of major runtime upgrades. An alert without a supported fix should record its owner or follow-up and the condition for reopening the decision.

If an upgrade fails, identify whether the package change, dependency resolution, or image scan introduced the problem. Retain the prior tested version or digest and revert the focused update through the usual PR workflow before retrying with new evidence.

## Validation and delivery

Work from a dedicated checkout for implementation. Record `git status --short` and `git rev-parse HEAD` before starting. If tests need the app, initialize and start an isolated stack using the [worktree skill](../../../.agents/skills/create-worktree/SKILL.md). Run `bash scripts/check-docs.sh` after staging Markdown changes. Complete [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing) and confirm the Stop hook did not skip formatting, lint, or tests. Follow the [post-push cleanup procedure](../../../.agents/skills/create-pr/SKILL.md#4-push-the-branch).

## Progress and decisions

- [x] 2026-11-20. Reviewed the existing workflow and defined scope at `eff8579`.
- [ ] Walk through a routine dependency update and an image or security example.
- [ ] Draft the playbook and independently verify the decision paths.

## Outcomes and retrospective

Pending execution. Record the walkthrough results, owner, and remaining follow-up before moving this plan to `docs/exec-plans/completed/`.
