# Architecture Validation and Development Workflow

## Goal and scope

Enforce the [documented import boundaries](../../../ARCHITECTURE.md#architectural-boundaries) in CI, verify the [move endpoint](../../domains/game/apis.md) handoff from JSON to a domain move, and exercise the issue-fix workflow on the [two-player game](../../product-specs/local-two-player-game.md).

## Milestones and pull requests

All three branches start from the same main branch and can merge independently. Run each command from the worktree for its branch.

1. `infra/harness-import-boundaries` adds an import check and this plan. Run `bash scripts/compose.sh exec -T app uv run pytest -q tests/architecture_boundaries_test.py`. Legal imports pass. Disallowed imports report the file, line, boundary, and supported entry point. The existing PR pytest job runs this check.
2. `infra/harness-move-dto` adds move adapter tests. Run `bash scripts/compose.sh exec -T app uv run pytest -q tests/game_api_test.py`. Malformed or mistyped requests never construct the application service. Integer coordinates reach it as a domain move. The integration suite verifies rule enforcement and persistence.
3. `fix/game-clipboard-fallback` adds browser guidance when clipboard access is denied, its regression, and a CI step for the Node suite. Run `node --test scripts/tests/game_web_interactions_test.js` before and after the fix.

## Browser verification

Run `APP_PORT=8765 bash scripts/start-local-server.sh`. In Chromium, open `http://localhost:8765/` with clipboard writes denied. Start a game, enter a different ID in the load field, and select **Copy ID**. Verify the message identifies the active ID below the board and preserves the pending input. Play one move and reload by the active ID to verify persistence.

## Delivery and recovery

Run the full Stop hook in each isolated worktree before pushing and the Markdown checker where documentation changes. Check `git status --short` and `bash scripts/compose.sh ps` before resuming. If CI fails, inspect the failed step, reproduce it with the same command, fix it, and repeat validation before pushing. Record results and review feedback in each PR. After pushing, run `bash scripts/stop-local-stack.sh` to preserve the database volume.

## Progress and decisions

- [x] 2026-11-20. Recovered the implementation from [PR #63](https://github.com/Phoxine/gomoku/pull/63), which closed without merging. Split the changes under the [plan guide](../../PLANS.md#pull-request-scope).
- [x] Original validation. The clipboard regression failed before the fix and passed afterward. Chrome confirmed the denied-write fallback, preserved load input, and persisted move. Review prompted the message to reference the active ID below the board.
- [ ] Validate and submit the independent changes against current main.
- [ ] Record the replacement PR and CI results, then archive this plan.

## Outcomes

The [original CI run](https://github.com/Phoxine/gomoku/actions/runs/44665011456) passed. The workflow exercised a failing regression locally. Every GitHub Actions job passed on that run.
