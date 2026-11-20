# Quality Tracking and Schema Documentation

## Goal and scope

Decide whether a quality scorecard would add information beyond the existing documentation audit and whether a generated database reference would reduce the cost of verifying the game schema. Evaluate adoption separately. Record the evidence and rationale even when an option is declined. The current delivery adds this plan. The two evaluations start after the plan is reviewed.

Start with the [documentation index](../../index.md), [documentation audit](../../documentation-audit.md), [architecture guide](../../../ARCHITECTURE.md), and [Batch Three outcomes](../completed/architecture-validation-and-development-workflow.md).

## Milestones

### 1. Evaluate quality tracking

1. In a task worktree based on current `origin/main`, record the date and `git rev-parse HEAD`. Use the [product specification](../../product-specs/local-two-player-game.md), [design index](../../design-docs/index.md), and existing audit as the baseline.
2. Draft a sample for local two-player Gomoku. Cover the player flow, rules, API, and persistence. For each row, identify the behavior or constraint, link to evidence, record its status and any gap, and specify a follow-up if needed. Use `Verified` for a claim supported by a current check, `Gap` for a demonstrated shortfall, and `Unverified` when evidence is missing or stale.
3. Ask a reviewer to repeat the status assignments from the linked evidence. Record disagreements and compare the sample with the existing audit. Adopt a scorecard if the statuses are reproducible and the sample exposes a concrete gap or change worth tracking separately. If adopted, add `docs/QUALITY_SCORE.md`, link it from the documentation index, and specify when to update it. Otherwise, record what the existing audit already covers and what evidence would justify revisiting the decision.

### 2. Evaluate schema generation

1. Use a fresh task worktree and its own empty database. From that worktree, run `bash scripts/init-worktree-env.sh` and `bash scripts/compose.sh up --build -d`. Confirm the app is present in `bash scripts/compose.sh ps --status running --services`, then run `bash scripts/compose.sh exec -T app uv run python manage.py migrate game --plan`. Confirm the plan contains only the expected reviewed migrations and required dependencies. Apply that plan with `bash scripts/compose.sh exec -T app uv run python manage.py migrate game`, following the [migration skill](../../../.agents/skills/migrate/SKILL.md). Use the [model](../../../src/app/domain/game/model/game.py), [initial migration](../../../src/app/domain/game/migrations/0001_initial.py), and [schema reference](../../domains/game/db-schemas.md) for comparison.
2. Start with the metadata probe below. The command describes `public.games` without reading game rows. Include columns, types, nullability, database defaults, keys, indexes, and check constraints. Compare the output with the migration and schema reference. Keep Django defaults, timestamp behavior, and gameplay semantics in the maintained schema reference.
3. Generate two scratch outputs from the same migrated schema and compare them with `diff -u`, which should exit 0 with no output. Modify one scratch copy to represent an outdated column or constraint. The same comparison should exit 1 and show the edited line. Record the commands, mismatches, and maintenance cost. Adopt generation if the output is reproducible, covers the relevant database facts, and makes future schema changes easier to review. If adopted, commit the reference under `docs/generated/` and document the exact regeneration command and its expected output. Otherwise, record the tradeoff and the condition for revisiting it.

```bash
bash scripts/compose.sh exec -T db psql -X -P pager=off -U postgres -d gomoku -c '\d+ public.games'
```

## Pull request scope and acceptance

- **Plan PR.** Deliver this active plan. Run `bash scripts/check-docs.sh` after staging it and complete the pre-push validation.
- **Quality evaluation PR.** Record the evidence, decision, and reviewer reproduction. If adopted, include the scorecard and its maintenance instructions. Run the Markdown checker.
- **Schema evaluation PR.** Record the decision, metadata comparison, repeatability result, and scratch mismatch result. If adopted, include the generated reference, regeneration instructions, and coverage for any executable tooling. If adding CI tooling, run its version-controlled passing and rejected cases in the relevant CI job.

The evaluation PRs can be prepared and merged independently after the plan PR. After both decisions are recorded, archive this plan with links to their evidence and record any follow-up in the owning document.

## Recovery and validation

Run commands from the relevant worktree. If setup stops partway, inspect `bash scripts/compose.sh ps -a` and follow the [Compose troubleshooting guide](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) before retrying in that worktree. Scratch files can be regenerated independently of the named database volume. Stop the isolated stack with `bash scripts/stop-local-stack.sh`; the volume is retained.

Before every push, follow the [PR validation procedure](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Confirm the Stop hook reports Ruff formatting, Ruff lint, and pytest completion. If it reports `Skipping final validation`, restore the running app and rerun the hook.

## Progress and decisions

- [x] 2026-11-20. Defined independent adoption criteria and delivery scope from the post-Batch Three baseline `c6b9df0`.
- [ ] Reproduce the quality assessment and record the adoption decision.
- [ ] Verify schema coverage and reproducibility and record the adoption decision.
- [ ] Link evaluation results and archive the plan.

## Outcomes and retrospective

Pending evaluation. Record the observed results, the cost of maintaining each option, and any follow-up after both decisions are available.
