# Game Move History Execution Plan

**Status** — Feature design approved. Schema and isolated database approval pending.

## Goal and scope

Persist every accepted move with its game ID, move number, color, and coordinates. A contributor investigating a game can read the saved moves in order and reconstruct what each player saw before a move. Continue serving the current game from the existing board snapshot for loading and resuming play.

The current [game schema](../../domains/game/db-schemas.md) stores the latest board. It can identify the stones in an old game, but their order cannot be recovered from that snapshot. Record moves accepted after activation, including moves in games already in progress. The first release covers persistence and internal verification. A public history API, a browser replay view, undo, and CPU strategy changes are outside the scope.

The [application service](../../../src/app/domain/game/service/application_service.py) already holds a game row lock while applying and saving a move. The [rules service](../../../src/app/domain/game/service/game_service.py) determines whether the move is legal and what state it produces. Follow the existing [architecture boundaries](../../../ARCHITECTURE.md#architectural-boundaries) when adding persistence.

## Proposed design

- **Keep one row per accepted stone.** Add a `game_moves` table with a foreign key to `games.id`, a one-based `move_number`, a `player` of `1` (black) or `2` (white), and zero-based `x` and `y` from 0 through 14. Require each field. Set `move_number` to the occupied-cell count after the accepted move, from 1 through 225. Enforce unique `(game_id, move_number)` and `(game_id, x, y)` pairs, and check the allowed ranges in PostgreSQL. Use the first unique index for per-game ordered reads and check the generated schema for redundant indexes. Document the foreign key and deletion behavior with the schema.
- **Write the move and board in one transaction.** Under the existing row lock, use the pre-move state's `current_player` to record the mover even when a terminal move retains that value. Apply the rules to obtain the next board, update the game, and insert the move. If either write fails, both roll back. Keep the game rules independent of Django and route all player and CPU move commands through this persistence path. A fixture that initializes a board directly should remain distinguishable from a game built by recorded moves.
- **Persist the history boundary.** Add a required integer `games.history_start_revision` with a PostgreSQL check for 0 through 225. Set it to zero when creating a game. During activation, pause game writers and populate it for existing games from the occupied-cell count before recording begins. The value stays fixed. An older game with 12 stones has a boundary of 12 and starts recording at move 13. The first 12 move positions remain unavailable. Backfill only the boundary.
- **Verify the recorded range.** For a snapshot with `revision` occupied cells, require exactly the move numbers from `history_start_revision + 1` through `revision`. Read the snapshot and history from the same database view. Check each recorded coordinate and color against the board. An empty history is valid only when the current count equals the boundary. A boundary above the current count, a missing row anywhere in the expected range, or a stone mismatch indicates inconsistent data. A valid history with a zero boundary is complete.
- **Keep write behavior compatible.** Legal two-player moves continue to alternate, and existing invalid requests retain their behavior. If CPU mode is present, the two CPU-mode commands record human and CPU moves in their own transactions. A CPU replay that returns the saved state creates no history row. Use the existing revision checks and row lock to prevent duplicate entries from stale CPU-mode commands.

## Milestones

### 1. Draft feature documentation and obtain human approval

Read the existing documents in full and follow the [feature documentation skill](../../../.agents/skills/document-feature/SKILL.md). Draft the new table and the `games` boundary column in the [database schema](../../domains/game/db-schemas.md). Integrate move numbering, write ownership, and history coverage into the [domain design](../../domains/game/context-designs.md). Review the [API contract](../../domains/game/apis.md) for compatibility. This scope preserves public endpoints and payloads.

Run the documentation checker and submit the English drafts for human review. Record explicit approval in this plan before beginning implementation. Obtain separate schema and database approval in milestone 2.

**Milestone check.** The drafts describe the table constraints, the atomic write, and what can be recovered from old games. Human approval is recorded.

### 2. Add move storage and verify the upgrade

1. Verify the current migration graph and write paths on the implementation branch. Obtain explicit approval for the new table, boundary column, backfill, constraints, indexes, and the isolated database target. Follow the [migration skill](../../../.agents/skills/migrate/SKILL.md) before editing models or generating, inspecting, or applying an approved migration.
2. Create and verify a nonempty legacy fixture at the preceding migration. Review the generated SQL, foreign key locking, and how the boundary backfill updates existing rows. Apply the approved migration. Verify that the older game's UUID, board, turn, and result remain intact, its boundary equals its occupied-cell count, and the new move table is empty. Check valid row creation and database rejection of duplicate numbers, duplicate coordinates, out-of-range values, and unknown game IDs.
3. Pause and drain old game writers before setting legacy boundaries. Keep writes paused through the backfill, verification, and cutover so the recorded range starts from the verified snapshot. Resume writes with the history-aware app. After capture starts, an app rollback to a writer without history support must keep move writes paused and preserve the boundary and move rows.

**Milestone check.** The old game loads with the same state, and PostgreSQL enforces the approved history constraints.

### 3. Record accepted moves atomically

1. Add the move persistence operation to the [repository](../../../src/app/domain/game/repository/game_repository.py) and wire it into the atomic [move command](../../../src/app/domain/game/service/application_service.py). Derive the move number from the locked position and record the player from that same state. Expose an internal ordered read for verification.
2. Route CPU advance through the same persistence operation if [the local CPU feature PR](https://github.com/Phoxine/gomoku/pull/93) is present. Keep that integration in the history feature PR if CPU support has landed. Otherwise, record a merge dependency so CPU advance adopts the history write before both features ship together.
3. Test both directions of partial failure. A history insert failure rolls back the board, and a board update failure leaves no committed move record. Under two overlapping PostgreSQL requests, valid moves on distinct cells produce successive numbers for the appropriate colors. Two requests for the same initially empty position commit exactly one move. For CPU mode, verify rollback, retries, and replay of a stale command against a later pending turn.

**Milestone check.** The persistent board and history agree after successful, rejected, delayed, concurrent, and interrupted requests.

### 4. Verify reconstruction and complete delivery

1. Replay a recorded game's ordered moves through the game rules from an empty board. Include a win and a draw. Compare the reconstructed board, player to move or last mover, status, and winner with the saved game. Include both two-player and CPU games when CPU mode is available.
2. Resume a legacy fixture with a boundary of 12 and verify that moves 13 through 15 are recorded and accepted by readback. In disposable fixtures, omit move 13 while retaining moves 14 and 15, then test a nonempty recorded range with all rows missing. Both must report inconsistent history. Also check that readback rejects internal and trailing gaps and recorded stones that disagree with the board. Verify that the current API still loads the game and that an older completed game with an empty recorded range stays read-only.
3. Sync the feature docs with the tested implementation. Record the migration name, validation outcomes, and remaining limitations in this plan. Move the plan to `docs/exec-plans/completed/` once acceptance passes.

## Validation and delivery

Run the checks from the implementation worktree root with its isolated Compose stack. Add any dedicated move-history test files to the focused run.

```bash
bash scripts/compose.sh exec -T app uv run python manage.py makemigrations --check --dry-run
bash scripts/compose.sh exec -T app uv run pytest -q tests/game_model_test.py tests/game_application_service_test.py tests/game_api_test.py tests/game_state_transition_test.py tests/architecture_boundaries_test.py
bash scripts/check-docs.sh
bash .codex/hooks/stop-validation.sh
```

| Scenario | Expected evidence |
| --- | --- |
| Legal move in a new game | The game has a boundary of 0. The first row is move 1, and its player and coordinates match the stone saved to the board. |
| New game reaches a win or draw | Replaying all rows reproduces the saved board and result. The terminal move is recorded once. |
| Illegal or terminal request | The board and history stay unchanged. |
| Failure during either write | Neither the board change nor the history row is committed. A retry can record the move once. |
| Concurrent legal moves or duplicate CPU requests | Successive legal moves get unique numbers. A duplicate or stale CPU command adds no row. |
| Move in a saved legacy game | The stored boundary identifies the unavailable prefix. History begins at the next move number and ends at the current occupied-cell count. |
| Missing recorded moves | A missing first, internal, or last row is detected. An entirely empty history is rejected when the snapshot has advanced beyond the boundary. |

- **Plan PR.** Deliver this plan for design review. Plan validation covers Markdown and links. The plan is based on `main` and can land independently of the local CPU feature PR.
- **Feature PR.** Deliver the migration, transactional writer, regression tests, and aligned feature docs together. Confirm the CPU merge order during milestone 2. Follow the [PR delivery workflow](../../../.agents/skills/create-pr/SKILL.md) after implementation and acceptance.

## Recovery

- **Interrupted move.** Read the saved board and the latest recorded move before retrying. PostgreSQL commits both writes together. A disagreement between the snapshot and a recorded suffix should pause writes while the cause is investigated.
- **Interrupted migration.** Check the isolated database's migration state and inspect the exact migration plan before retrying. Reverse a migration only on an explicitly approved disposable database. Once history rows exist, keep the table and repair forward. Keep game writes paused while only a version without history support is available.
- **Interrupted implementation.** Resume at the first unchecked milestone after reviewing the branch, diff, approval records, and Compose project. Preserve the isolated database volume.

## Progress, discoveries, and decisions

- [x] 2026-11-25. Drafted after a CPU game investigation showed that the exact move order could not be determined from the stored board.
- [x] 2026-11-26. Drafted the schema and domain design for human review. Reviewed the API contract and confirmed all public endpoints and payloads are covered by the existing contract. Local CPU mode landed in `main` in PR #93, so this feature includes both move commands.
- [x] The user approved the feature design in the implementation conversation, including the documented move history scope. This approval completes milestone 1.
- [ ] Record human approval for the schema and isolated database, then verify the upgrade.
- [ ] Implement atomic recording and verify concurrency and rollback.
- [ ] Verify reconstruction and deliver the feature.

## Outcomes and retrospective

Implementation and acceptance are pending. Record the actual migration, test results, legacy-history coverage, and any unresolved rollout dependency here.
