# Browser Smoke Test

## Goal and scope

Make the core player flow reproducible in a real browser. A smoke test is a short check that the application can start, accept a move, and load the saved game. Start from the [local two-player specification](../../product-specs/local-two-player-game.md), [Node interaction tests](../../../scripts/tests/game_web_interactions_test.js), and [Batch Three browser verification](../completed/architecture-validation-and-development-workflow.md). The existing Node tests cover interaction logic with a simulated DOM.

## Milestones

1. Reproduce the baseline with `node --test scripts/tests/game_web_interactions_test.js`. In an isolated worktree, choose an unused host port for a fresh local web stack and run `APP_PORT=8765 bash scripts/start-local-server.sh`, replacing 8765 if needed. Confirm the server responds on that port. Manually create a game, place a legal move, and capture the active game ID. In a clean browser context, load that ID and verify the stone and next-player indicator.
2. Evaluate a headless Chromium runner that fits local and CI execution. Record how its version and browser binaries will be obtained. Check dependency approvals before changing project manifests. Automate the manual scenario using a fresh game and a clean browser context per run. Wait for the server and observable UI state with bounded timeouts. Save a screenshot and useful failure output on an assertion failure.
3. Verify the same runner locally and in the PR workflow. Keep the existing Node suite. Reserve the browser test for behavior that needs the real server and browser together.

## Acceptance and pull requests

- **Browser smoke test PR.** Include the runner, one documented local command, the CI step, and failure artifact instructions. Run the test twice on the same isolated stack with different game IDs. Both runs must show a black stone after loading and the white player to move.
- Verify the failure path by temporarily expecting the wrong next player in a scratch copy. The run must fail with the relevant assertion and save the screenshot. Include version-controlled passing and rejected behavior for any CI tooling added. No other follow-up plan is a merge prerequisite.

If the server cannot start, inspect `bash scripts/compose.sh ps -a` and the port owner before choosing a new port. If the test flakes, inspect its screenshot and wait conditions before retrying. Revert the browser step if needed to restore CI while retaining the Node suite.

## Worktree and recovery

Run commands from this plan's dedicated worktree. Record `git status --short` and `git rev-parse HEAD` before starting. When the work needs Django and PostgreSQL, run `bash scripts/init-worktree-env.sh` and `bash scripts/compose.sh up --build -d`. Confirm `app` is listed by `bash scripts/compose.sh ps --status running --services`. If startup is interrupted, inspect `bash scripts/compose.sh ps -a` and follow the [Compose troubleshooting guide](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) before retrying in the same worktree.

Run `bash scripts/check-docs.sh` after staging documentation changes. Use the full [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Confirm Ruff formatting, Ruff lint, and pytest completed. If the hook reports `Skipping final validation`, restore the running app and retry. After pushing, use `bash scripts/stop-local-stack.sh` to stop the containers and keep the worktree's database volume.

## Progress and decisions

- [x] 2026-11-20. Defined scope and acceptance from baseline `eff8579`.
- [ ] Record the manual browser and Node baselines.
- [ ] Implement and verify the real-browser scenario and failure output.
- [ ] Record local and CI results.

## Outcomes and retrospective

Pending implementation or adoption review. Record the evidence, decisions, open gaps, and follow-up before moving this plan to `docs/exec-plans/completed/`.
