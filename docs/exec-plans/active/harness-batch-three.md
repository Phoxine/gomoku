# Harness Batch Three

## Goal and scope

Enforce the current import boundaries in CI, verify the move endpoint's JSON-to-domain handoff, and exercise the issue-fix workflow with a reproducible browser defect. See the [architecture](../../../ARCHITECTURE.md#architectural-boundaries), [API contract](../../domains/game/apis.md), and [local two-player specification](../../product-specs/local-two-player-game.md).

## Milestones and acceptance

Run commands from the isolated task worktree.

1. Add a pytest check for static imports throughout the API and in the game rules and state modules. Report the importing file, line, boundary, and supported entry point. Test allowed imports and representative forbidden absolute and relative forms. The existing PR pytest job should run the check and its regression cases.
2. Extend the move API tests to confirm that malformed JSON, incorrect request shape, and incorrect coordinate types never instantiate the application service. Verify that integers pass through the request DTO as a domain move, including an out-of-range value whose rejection belongs to game rules. Keep the PostgreSQL integration test as the check for persistence and actual rule enforcement.
3. With no open GitHub issues at task start, reproduce the Copy ID failure when the browser denies clipboard writes. Capture a failing JavaScript test, restore manual-copy guidance, and verify denied and successful writes. Run `node --test scripts/tests/game_web_interactions_test.js` locally and in PR CI. In Chromium, start a real game, test Copy ID with clipboard writes blocked, inspect the ID field, and submit a move.
4. Review the diff, pass the Stop hook and Markdown checks, submit a PR, and monitor review and CI. Address actionable feedback. On CI failure, inspect the failed step, reproduce it locally, correct it, and validate before pushing again. Record the outcome.

Run the focused Python tests with `bash scripts/compose.sh exec -T app uv run pytest -q tests/architecture_boundaries_test.py tests/game_api_test.py`. For the browser check, open `http://localhost:8765/` in Chromium, block clipboard access for that origin in site settings, and select **New game**. Enter a different ID in the load field, then select **Copy ID**. The message should point to the active ID below the board and preserve the entry in the load field. Play one move, select **Load game** with the active ID, and confirm the stone and the next player's turn are still shown.

## Recovery

Check `git status --short` and `bash scripts/compose.sh ps` before resuming. Start the local server with `APP_PORT=8765 bash scripts/start-local-server.sh`, selecting another unused port if needed. Rerun focused tests before the full Stop hook. After pushing, stop the isolated stack with `bash scripts/stop-local-stack.sh` and retain its database volume. Use a fresh browser profile for clipboard permission checks.

## Progress and decisions

- [x] 2026-11-20. Confirmed the second batch is in the base at `cf261f3`. Created `infra/harness-batch-three` with an isolated Compose project.
- [x] Add architecture checks and cover the move boundary. All 11 focused Python cases passed.
- [x] Reproduce, fix, and verify the clipboard issue. The new JavaScript case failed on the original code. All 9 cases passed after the fix and run in the PR test job. Chrome confirmed the manual-copy message with clipboard writes denied and confirmed the move survived a reload by ID.
- [x] Review found that the editable load field can contain a different game's ID. The fallback now points to the active ID displayed below the board, and the regression case verifies that pending input is preserved.
- [ ] Record review, Stop hook, browser, and PR CI outcomes.

## Outcomes and retrospective

Pending implementation and validation.
