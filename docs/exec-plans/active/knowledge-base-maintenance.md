# Make the Gomoku knowledge base maintainable

This plan pilots the [execution plan guide](../../PLANS.md) on the remaining documentation maintenance work. Contributors should be able to detect broken documentation links in a pull request, repeat a documentation audit, and recover durable project decisions from a fresh checkout. The [documentation index](../../index.md), [design index](../../design-docs/index.md), and [core beliefs](../../design-docs/core-beliefs.md) are the starting points.

## Progress

- [x] 2026-11-19. Define the execution plan format and record the remaining documentation work in this plan.
- [x] 2026-11-19. Add the documentation job and PR reminder and validate the checker locally.
- [x] 2026-11-20. Record and run the first repeatable documentation audit.
- [ ] Record a durable decision and validate the handoff in a fresh worktree.

## Milestones and acceptance

### 1. Add documentation checks to PR CI

From the repository root, inspect the [CI workflow](../../../.github/workflows/ci.yml), [PR template](../../../.github/pull_request_template.md), and [feature documentation guide](../../../.agents/skills/document-feature/SKILL.md). Add a lightweight checker under `scripts/` and wire it into pull requests targeting `main`. Check repository Markdown relative links, index coverage, and a verification status on each design document entry. The design index should cover the domain design, API contract, and schema under `docs/domains/game/`. The product index should cover the product specification pages under `docs/product-specs/`. Add a reminder to the PR template to compare documentation with implementation when changing game rules, API behavior, or database schema. Record the checker invocation and its inputs in this plan.

Acceptance requires a passing run on the corrected checkout. Exercise a broken relative link, an omitted index entry, and a missing design verification status in temporary fixtures. Each should fail with the affected file and the reason. Confirm that the PR's CI runs the check successfully and that the PR description displays the documentation reminder.

Run `bash scripts/check-docs.sh` from the repository root to run the Markdown checks and regression tests in Docker. The [checker](../../../scripts/check_docs.py) uses the Git index to find tracked files, including newly staged paths, and reads Markdown from the working tree. It checks relative inline and reference link destinations and section anchors on Markdown pages. Use inline links in the design table. The product index also supports reference links. The design table accepts `Verified`, `Partially verified`, and `Pending` in its status column. The checker reports offending files and exits with status 1 if any check fails. The PR workflow invokes the checker and regression tests directly in its Documentation Checks job.

### 2. Make the documentation audit repeatable

Create `docs/documentation-audit.md` with a checklist for document owners, stale or unused pages, and differences between documentation and implementation. Start with the [architecture guide](../../../ARCHITECTURE.md), [design evidence](../../design-docs/index.md), and [product specifications](../../product-specs/index.md). For each audited area, record the owning page, the evidence used, the finding or pass result, and any follow-up. Use the checker from milestone 1 for mechanical checks and read the referenced behavior for claims the checker cannot assess.

Acceptance requires a dated audit covering the design and product indexes, with every finding either resolved or assigned a versioned follow-up. Consider scheduled automation after the checklist has been repeated successfully.

### 3. Preserve decisions and test a fresh handoff

Select a durable product or architecture decision from a PR review or task discussion. Record the decision, its reason, and supporting evidence in the document that owns it, such as the product specification, domain design, or API contract. Link to that record from this plan. Check the [architecture guide](../../../ARCHITECTURE.md) and [API rules](../../../.codex/rules/api.md) when choosing where it belongs. Update navigation if the decision would otherwise be difficult to find.

Use the [worktree setup guide](../../../.agents/skills/create-worktree/SKILL.md) to create a separate checkout of the committed documentation changes, using its own Compose project if container checks are needed. Starting at [AGENTS.md](../../../AGENTS.md), a reviewer should be able to find this plan, follow its link to the decision in the owning document, locate the supporting code or tests, and run the documented checker and audit steps using only repository files. Record the commit and the commands and results in this plan.

Use the [Python container image update decision](../../../README.md#python-container-image-updates) for this handoff. From the fresh worktree root, compare the two pins with `git grep -n -F 'python:3.14-slim@' -- docker/Dockerfile scripts/check-docs.sh`. Expect two references with the same digest. Run `bash scripts/check-docs.sh` and expect both the Markdown checks and checker tests to pass. Use the [documentation audit checklist](../../documentation-audit.md) to compare the decision with its implementation and test entry points.

## Recovery

Run negative checker cases in temporary fixtures. If a PR check fails, keep the plan active, record the failing file and output, correct the smallest affected change, and rerun the same check before pushing again. When resuming work, inspect `git status --short`, compare the branch with `origin/main`, and pick up at the first unchecked milestone. Follow the [delivery workflow](../../../AGENTS.md#git-and-pull-request-workflow) for push validation and volume-preserving cleanup.

If milestone 1 needs to be rolled back, use `git status --short`, `git diff`, and `git diff --cached` to identify its changes to the checker under `scripts/`, the CI workflow, and the PR template. For uncommitted work, undo only the milestone's edits and remove a new checker file only if it contains no unrelated work. For committed work, inspect the commit with `git show` and use `git revert` if it contains only milestone 1 changes. If edits are mixed, make a corrective commit that reverses only the milestone's changes. Review the resulting diff to confirm that unrelated work is intact and rerun the remaining checks. In Progress, record the rollback, mark milestone 1 pending again, and reopen any dependent acceptance checks that the rollback invalidated.

## Discoveries

- The design index already links to implementation and test evidence. The current PR workflow has no dedicated documentation check, so the next milestone can validate the existing index and report actionable failures.

## Decisions

- 2026-11-19. Keep the first checker lightweight and start with the current index structure. The documentation audit handles ownership, usage, and accuracy claims that require human judgment.
- 2026-11-19. Use Python's standard library and the Git index so the PR job needs no project dependencies and checks the same tracked paths as a local run.
- 2026-11-19. Keep game architecture checks and game UI workflow experiments outside this documentation plan so the acceptance criteria stay focused on maintaining the knowledge base.
- 2026-11-20. Record the [Python image update decision](../../../README.md#python-container-image-updates) from the discussion following [PR #61](https://github.com/Phoxine/gomoku/pull/61). It affects future changes to both container entry points and can be verified from a clean checkout.

## Outcomes and retrospective

On 2026-11-19, a read-only handoff walkthrough used the guide, this plan, and the repository to locate the first pending milestone, its CI inputs, and the expected pass and failure cases. The walkthrough identified an ambiguity in index coverage, so milestone 1 now names the pages each index is expected to cover.

The first checker passed on all 27 tracked Markdown files. In temporary Git fixtures, a broken relative link, an omitted product index entry, a missing design verification status, and a missing heading anchor each returned status 1 with the affected file and reason.

The [first documentation audit](../../documentation-audit.md#2026-11-20) recorded ownership, navigation, and source evidence for the design and product indexes. It corrected the API's description of CSRF token submission and rechecked the API and schema edits made since the design index's verification baseline. The documentation checker passed.

Record actual outputs and lessons here as milestones finish. Move this file to `docs/exec-plans/completed/` after all three milestones meet their acceptance criteria.
