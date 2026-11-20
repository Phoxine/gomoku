# Architecture Validation and Development Workflow

## Goal and scope

Enforce the [documented import boundaries](../../../ARCHITECTURE.md#architectural-boundaries) in CI, verify the [move endpoint](../../domains/game/apis.md) handoff from JSON to a domain move, and exercise the issue-fix workflow on the [two-player game](../../product-specs/local-two-player-game.md).

## Milestones and pull requests

All three branches start from the same main branch and can merge independently. Run each command from the worktree for its branch.

In a fresh worktree, run `bash scripts/init-worktree-env.sh` to create the local Compose settings, then `bash scripts/compose.sh up --build -d` to start the app and database.

1. `infra/harness-import-boundaries` adds an import check and this plan. Run `bash scripts/compose.sh exec -T app uv run pytest -q tests/architecture_boundaries_test.py`. Legal imports pass. Disallowed imports report the file, line, boundary, and supported entry point. The existing PR pytest job runs this check.
2. `infra/harness-move-dto` adds move adapter tests. Run `bash scripts/compose.sh exec -T app uv run pytest -q tests/game_api_test.py`. Malformed or mistyped requests never construct the application service. Integer coordinates reach it as a domain move. The integration suite verifies rule enforcement and persistence.
3. `fix/game-clipboard-fallback` adds browser guidance when clipboard access is denied, its regression, and a CI step for the Node suite. Run `node --test scripts/tests/game_web_interactions_test.js` before and after the fix.

## Browser verification

Run `APP_PORT=8765 bash scripts/start-local-server.sh`. In Chromium, open `http://localhost:8765/` with clipboard writes denied. Start a game, enter a different ID in the load field, and select **Copy ID**. Verify the message identifies the active ID below the board and preserves the pending input. Play one move and reload by the active ID to verify persistence.

## Delivery and recovery

If setup stops after the database starts, check `git status --short`, then run `bash scripts/compose.sh ps -a` to see which services were created and their health. Use `bash scripts/compose.sh logs --tail 50 app db` to diagnose the failing service. If initialization was interrupted, rerun `bash scripts/init-worktree-env.sh` in the same worktree to reuse its existing settings. Then retry `bash scripts/compose.sh up --build -d` in that worktree. Confirm that `app` appears in `bash scripts/compose.sh ps --status running --services` before testing.

To undo partial startup or clean up after a push, run `bash scripts/stop-local-stack.sh` from that worktree. It removes containers and the project network for the worktree's path-bound project and preserves its database volume and local settings. For a legacy project rejected by the helper, verify its ownership before running `bash scripts/compose.sh down` from that worktree.

Run the full Stop hook in each isolated worktree before pushing and the Markdown checker where documentation changes. If CI fails, inspect the failed step, reproduce it with the same command, fix it, and repeat validation before pushing. Record results and review feedback in each PR.

## Progress and decisions

- [x] 2026-11-20. Recovered the implementation from [PR #63](https://github.com/Phoxine/gomoku/pull/63), which closed without merging. Split the changes under the [plan guide](../../PLANS.md#pull-request-scope).
- [x] Original validation. The clipboard regression failed before the fix and passed afterward. Chrome confirmed the denied-write fallback, preserved load input, and persisted move. Review prompted the message to reference the active ID below the board.
- [x] 2026-11-20. Revalidated and submitted the three independent changes against `f74bc75`. Read-only review caught persisted checkout authentication in the job running the Node tests. Disabled credential persistence for that job and passed re-review.

## Outcomes

| Change | Isolated Stop hook | GitHub Actions |
| --- | --- | --- |
| [Import boundaries, PR #65](https://github.com/Phoxine/gomoku/pull/65) | Ruff format and lint, 228 Python tests | [Passed](https://github.com/Phoxine/gomoku/actions/runs/44667438171) |
| [Move DTO, PR #66](https://github.com/Phoxine/gomoku/pull/66) | Ruff format and lint, 220 Python tests | [Passed](https://github.com/Phoxine/gomoku/actions/runs/44667437513) |
| [Clipboard fallback, PR #67](https://github.com/Phoxine/gomoku/pull/67) | Ruff format and lint, 219 Python tests | [Passed](https://github.com/Phoxine/gomoku/actions/runs/44667437832) |

The same Node command used in CI failed once on the original game script, which reported a connection error when clipboard access was denied. All nine cases passed with the fixed script. Headless Chrome confirmed the new message, preserved the pending load input, and showed the persisted move after reloading. The replacement GitHub Actions runs passed on their first attempt, so the failure-and-retest exercise took place locally.
