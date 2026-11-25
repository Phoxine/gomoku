# Local CPU Game Execution Plan

**Status** — Draft for review

## Goal and scope

Deliver the proposed [Local Game Against the CPU](../../product-specs/local-cpu-game.md). From the game page, a player can choose CPU mode, play black against a white CPU at one difficulty, and resume a saved game by its ID or from the same browser. Games use the existing 15×15 board, win and draw rules, and ID access model. Existing and newly created two-player matches must keep their current turn behavior. Follow the specification's first-release scope.

The [rules service](../../../src/app/domain/game/service/game_service.py) validates moves and computes results. The [application service](../../../src/app/domain/game/service/application_service.py) already serializes move writes by locking the game row in a transaction. The [browser client](../../../src/app/static/game/game.js) already supports create, load, refresh, keyboard play, and Copy ID. Extend these entry points.

## Proposed design decisions

- **Persist the mode.** Add one immutable game mode in `games.mode` with values `two_player` and `cpu`. Use a non-null field with a two-player default and a database check constraint. Populate existing rows as two-player through the additive migration. Keep the board, status, and result fields and add no index or background job. Assess migration locking and the database default needed for overlapping old writers before finalizing the migration.
- **Commit each move independently.** Save the human move before requesting a CPU move. A pending CPU turn is a saved CPU game with `status == in_progress` and white to move. The browser can recover it from a read-only GET after refresh or loss of the POST response. Apply both colors through the existing rules service.
- **Bind requests to a specific board position.** Use the occupied-cell count as the game's revision. It starts at zero and increases once per accepted stone. The board is append-only within a game, and starting over creates a new ID. A CPU command carries the revision returned for the pending turn. Under the game row lock, compare the current revision, mode, turn, and status before choosing or placing a CPU stone. A stale or duplicate CPU request returns the current state without modifying it, including when a later white turn is pending. Require the same revision on human moves in CPU games so a retry or stale tab cannot place a move on a later turn. Preserve the coordinate-only request contract for two-player games.
- **Use a bounded CPU policy.** Propose a deterministic, framework-independent selector. Choose an immediate winning move if available, otherwise block an immediate opponent win if available, otherwise prefer an empty intersection nearest the center with a stable row and column tie-break. Use the existing rules for evaluating legal moves and wins. Bound work to the 225 board intersections and measure response time on representative positions before shipping.

## Milestones

### 1. Draft feature documentation and obtain human approval

1. Use the [product specification](../../product-specs/local-cpu-game.md) and current implementation to draft the proposed changes to the [API contract](../../domains/game/apis.md), [database schema](../../domains/game/db-schemas.md), and [domain design](../../domains/game/context-designs.md). Identify any changes needed to the product pages and [architecture overview](../../../ARCHITECTURE.md). Keep CPU mode marked as proposed while implementation and acceptance are pending.
2. Run the documentation checker and present the drafts to the human reviewer. Incorporate their feedback and resubmit if needed.

**Milestone check and approval gate.** A human reviewer must explicitly approve the documentation drafts before milestone 2 begins. Until then, keep work within this milestone. Schema changes and migration execution still require the separate approvals in milestone 2.

### 2. Establish mode, migration, and compatibility

1. Baseline the game API, storage model, and browser tests. Use the [API rules](../../../.codex/rules/api.md), [API contract](../../domains/game/apis.md), [schema](../../domains/game/db-schemas.md), and [domain design](../../domains/game/context-designs.md).
2. Obtain explicit approval for the proposed schema change and the target isolated database before modifying models, generating a migration, or applying it to that database. Follow the [migration skill](../../../.agents/skills/migrate/SKILL.md). Use a test fixture created at the preceding migration to verify that an existing game retains its ID, board, turn, status, and winner after upgrading. Check fresh creation for both modes and database rejection of invalid mode values.
3. Carry the mode through [state types](../../../src/app/domain/game/state.py), [the model](../../../src/app/domain/game/model/game.py), and [repository mappings](../../../src/app/domain/game/repository/game_repository.py). Preserve the immutable mode when the rules service returns a new state, including on terminal moves. Through [DTOs](../../../src/app/api/game_dto.py) and [views](../../../src/app/api/game_views.py), accept optional JSON mode on creation, keep bodyless creation as two-player, and expose mode and revision in game responses. Preserve existing form/CSRF behavior and validate malformed input and unsupported modes at the API boundary.

**Milestone check.** Old rows and bodyless requests load as two-player and still alternate both human colors. A CPU game starts empty with black to move. Run migration checks and the model and API suites.

### 3. Implement and verify CPU turns

1. Add the CPU selector alongside the [rules service](../../../src/app/domain/game/service/game_service.py). Cover immediate wins, immediate blocks, the fallback, and a board with just one legal move. Keep the selector independent of Django and persistence.
2. Extend the [application service](../../../src/app/domain/game/service/application_service.py) with a CPU advance command. In a separate transaction from the human move, lock and re-read the game, check the supplied revision and eligibility, then select, apply, and save the white move. Keep a request that targets an old revision, a finished game, or a CPU game on black's turn free of writes. Reject the CPU command for a two-player game. Guard human submissions to CPU games by mode, black's turn, and revision under the same row lock.
3. Add a CSRF-protected `POST /api/v1/games/{id}/cpu-move/` in [URL configuration](../../../src/config/urls.py) and expose the command through the DTO and handler layers. The JSON body contains `expected_revision`. Human moves in CPU games send `x`, `y`, and `expected_revision` to the existing moves route. Validate the revision as an integer from 0 through 225, excluding booleans. Propose `200` with the current state for a repeated or stale CPU request on a CPU game, `409` for a CPU request on a two-player game or an out-of-turn or stale human move, and the existing error conventions for malformed requests and missing games. Document the final contract and its errors with the implementation.
4. Verify rollback of the CPU transaction after a controlled selector or save failure. Use a PostgreSQL-backed test with independent connections to overlap two CPU requests for the same revision. Verify both the stored board and the command results. Replay the old CPU request after another black move has advanced the game to a new pending white turn. Also submit a human move directly during white's turn and replay an old black request after the turn returns to black. Verify that neither human request changes the stored game.

**Milestone check.** A committed human move survives a failed CPU transaction. Retrying the same turn produces one white stone. Concurrent or delayed requests for that turn cannot produce any additional stone, even after the next black move. Human move, CPU move, and subsequent GET responses all preserve the original game ID and CPU mode.

### 4. Connect the browser and verify the player flow

1. Extend [the game page](../../../src/app/template/game.html) and [browser client](../../../src/app/static/game/game.js) to select a mode at creation and identify mode, color, current turn, and result. Render the saved black stone and the CPU turn before posting the CPU command. Disable player placement while a CPU turn is pending, including after an error. Reuse the existing keyboard board controls and live status, with a reachable retry action and focus restoration after the turn.
2. On load by ID, refresh, or automatic restore, use the saved response to determine whether to request the CPU move. On failure, keep the last confirmed board visible and offer retry. Re-read by ID before retrying a request with an uncertain outcome. If the same revision is still pending, retry it. If the position advanced, render it and handle any newly pending turn using its own revision. When the human POST response is lost, refresh the saved state before accepting further input. Use the existing ID storage, Copy ID, and manual-copy fallback.
3. Add cases to the [browser interaction tests](../../../scripts/tests/game_web_interactions_test.js) for pending-state rendering, keyboard and pointer placement guards, failure and retry, and reopening a saved game. Exercise the page with two tabs on the same CPU game, then start a two-player match and reopen an older one.
4. Verify the approved documentation against the implemented API, schema, domain design, and browser behavior. Record any differences for review. Mark CPU mode available in the product spec and index after the feature passes acceptance.

**Milestone check.** The browser meets every row in the product specification's acceptance table, including the final-intersection cases and ID recovery when clipboard access is blocked.

## Validation and delivery

Run commands from the future implementation worktree root. Initialize that worktree with `bash scripts/init-worktree-env.sh`, start its services with `bash scripts/compose.sh up --build -d`, and confirm `app` is running before container checks.

```bash
bash scripts/compose.sh exec -T app uv run python manage.py makemigrations --check --dry-run
bash scripts/compose.sh exec -T app uv run pytest -q tests/game_model_test.py tests/game_service_test.py tests/game_state_transition_test.py tests/game_application_service_unit_test.py tests/game_application_service_test.py tests/game_api_test.py tests/game_web_test.py tests/architecture_boundaries_test.py
node --test scripts/tests/game_web_interactions_test.js
bash scripts/check-docs.sh
bash .codex/hooks/stop-validation.sh
```

Include any new CPU-specific suite in focused runs. For milestone evidence, record human approval of the documentation drafts, the migrated legacy row, unchanged two-player behavior, one stored white stone after concurrent requests, unchanged revision after stale replay, and successful browser recovery after an interrupted turn. Verify that a terminal human move sends no CPU request and that a terminal CPU move disables further placement. Stage new Markdown before the documentation check and verify that the Stop hook completes Ruff formatting, lint, and the full pytest suite.

- **Plan PR.** Review the milestones, proposed design, and acceptance checks before implementation. The feature documentation still requires the explicit human approval in milestone 1.
- **Feature PR.** Keep the migration, server turn contract, browser flow, regression tests, and updated feature docs in one PR. The browser needs the mode and revision contract, and CPU creation needs a complete turn flow so saved games can progress. Use the existing [delivery workflow](../../../.agents/skills/create-pr/SKILL.md) after the plan is reviewed and implementation is authorized.
- **Activation order.** For any rollout with overlapping app versions, apply the additive migration first, then keep CPU creation unavailable at the API until every game writer enforces mode. Verify that the previous app version can create and update a two-player game against the expanded schema and that the new app reads the same game as two-player. Enable CPU creation only after the older writers are out of service.

## Recovery

- **Interrupted move.** Fetch the saved game by ID. A pending white turn is resumable from its current revision. A completed game stays terminal. A failed attempt to advance the CPU leaves the last committed position available for retry.
- **Migration interrupted.** From the isolated worktree, inspect `showmigrations`, the migration plan, and a pre-existing fixture before retrying. Follow the migration skill for any rollback. Once CPU games exist, reverting to an app that does not recognize CPU mode could let human submissions take white turns. Keep the column and CPU data and fix forward. If service must be paused, stop game writes until a version that understands CPU mode is restored. Test any reverse migration only on an approved disposable database.
- **Work interrupted.** Resume at the first unchecked milestone after reviewing the diff, branch, and isolated Compose state. If the documentation is still awaiting human approval, resume at milestone 1. Preserve the worktree's database volume.

## Progress, discoveries, and decisions

- [x] 2026-11-25. Drafted from the product spec merged at `81bcd01`. Existing row locking can serialize requests, and the board revision identifies the exact pending turn across retries.
- [ ] Draft feature documentation and record explicit human approval in milestone 1.
- [ ] Obtain schema approval and complete milestone 2.
- [ ] Complete CPU logic, failure recovery, and concurrency verification in milestone 3.
- [ ] Complete browser integration, acceptance checks, and documentation verification in milestone 4.

## Outcomes and retrospective

Implementation and its acceptance checks are pending. Record the actual API and migration decisions, validation commands and results, and any remaining work before moving this plan to `docs/exec-plans/completed/`.
