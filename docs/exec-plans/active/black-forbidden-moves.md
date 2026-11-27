# Optional Black Forbidden Moves

## Goal and scope

Before starting a two-player or CPU game, players can enable black forbidden moves and choose the consequence. Save the choice with the game so reloading by ID and retrying use the original setting. The board stays 15×15 with black moving first. Use the forbidden-move and win definitions in [RIF rules §§3 and 9](https://www.renju.net/rifrules/) and retain the current opening sequence.

| New-game choice | Result of submitting a black forbidden move |
| --- | --- |
| Off (default) | Both colors use the current five-or-more win rule. Existing games and create requests that omit the choice use Off. |
| Warn and retry | Reject the move with its reason. The square stays empty, black can choose another move, and the revision and history stay at the last accepted move. |
| Immediate loss | Record the submitted black stone as the final move, increment the revision once, and record a white win with the forbidden-move reason. |

Proposed API field: `forbidden_move_policy`, with values `off`, `warn`, and `loss`. Use an enable checkbox and a consequence selector. When enabled, the selector defaults to Warn and retry. Display the active game's saved policy independently of the settings for the next game.

## Rule and persistence decisions

- In enabled games, check all four axes through the new black stone for an exact five first. An exact five wins even with a forbidden pattern on another axis. Otherwise check overline (six or more), double-four, and double-three in that order for a stable reported reason. A last-cell win or loss takes precedence over a draw. White wins with five or more under every policy.
- Count distinct fours containing the new stone by axis and stone set. A straight four with two winning endpoints counts once. Two distinct fours can share an axis. Straight, single-ended, and gapped formations qualify if a completion makes an exact five. One four and one three can coexist on a legal move.
- Count distinct threes containing the new stone that can become a straight four with two exact-five completions. Exclude extensions that make five or are forbidden. Apply RIF §9.3 recursively to identify false threes. Examine relevant local extensions and use temporary boards. Each recursive step adds a black stone, which bounds the depth.
- Keep rule evaluation framework-independent in [game_service.py](../../../src/app/domain/game/service/game_service.py). Reuse black legality and exact-five evaluation in CPU threat prediction.
- Persist the policy at creation and a nullable forbidden-move result reason on a loss. Commit the final stone, winner, reason, and history entry in the existing locked transaction. A loss uses the normal won state with white as winner and retains black as the last mover in the terminal state. A warning produces no history entry.

## Milestones

### 1. Draft English feature documents and obtain approval

Draft the [API contract](../../domains/game/apis.md), [database schema](../../domains/game/db-schemas.md), [domain design](../../domains/game/context-designs.md), and [CPU product specification](../../product-specs/local-cpu-game.md). Describe both modes, defaults, policy validation, success and error examples, result storage, and the exact-five exception. Resolve how Warn mode ends a game if black has empty intersections but every placement is forbidden, and add an acceptance case for that outcome. Submit the drafts for human review and record explicit approval below before starting implementation. Obtain explicit schema-change approval under [AGENTS.md](../../../AGENTS.md) before changing models or migrations.

### 2. Implement domain rules and adapt CPU prediction

Add policy and reason types to [state.py](../../../src/app/domain/game/state.py). Keep finished-game, coordinate, and occupied-cell checks ahead of forbidden-move evaluation. Add fixtures to the [rules tests](../../../src/tests/game_service_test.py) and [transition tests](../../../src/tests/game_state_transition_test.py) for all axes, edges, mixed and single-ended fours, same-axis double-four, false threes including a nested double-three, four-three legality, exact five with a simultaneous foul, last-cell outcomes, and white and Off-mode overlines.

When a policy is enabled, consider only legal black winning moves and black replies in CPU threat prediction. Re-enumerate black replies after simulated white placements since a white stone can make a previously forbidden black reply legal. A forbidden block cannot stop white's threat. Simulate legal alternatives or apply the approved no-legal-move outcome where applicable. Test newly legal replies, a forbidden block, and a black overline the CPU should skip as a winning threat. Run current CPU fixtures under Off as regression checks.

### 3. Persist and expose policy and result

Follow the [migration skill](../../../.agents/skills/migrate/SKILL.md) in the feature worktree. Give existing games the Off default and a null forbidden-move reason. Constrain policy and reason values and require any forbidden-move result reason to belong to a white win under Loss. Update the [repository](../../../src/app/domain/game/repository/game_repository.py), [application service](../../../src/app/domain/game/service/application_service.py), [DTOs](../../../src/app/api/game_dto.py), and [views](../../../src/app/api/game_views.py).

Validate create values, preserve empty and omitted-field requests, and expose the immutable policy in returned game states. Apply the saved policy under the row lock after turn and applicable revision checks. Propose HTTP 409 with a `forbidden_move` error and reason for Warn. For Loss return HTTP 200 with `status: "won"`, `winner: 2`, and the persisted reason. Include the reason when subsequently returning game state. Test old rows, unknown create values, stale CPU-mode revisions, duplicate submissions after a loss, zero writes on Warn, one final history entry on Loss, and rollback if the history insert fails. Verify replaying recorded moves in a new game under its saved policy produces the saved result.

### 4. Add controls and verify browser flows

Update [game.html](../../../src/app/template/game.html) and [game.js](../../../src/app/static/game/game.js). Submit the selected policy for either game mode. Show the saved policy when restoring a game and announce the specific reason through the existing live region. On Warn, keep the square empty and let black retry by keyboard or pointer. On Loss, show the final stone and why white won, then disable placement. Verify zero CPU move requests after a warning or loss.

## Validation and recovery

From the isolated feature worktree, start `bash scripts/compose.sh up --build -d`. Run `bash scripts/compose.sh exec app uv run pytest tests/game_service_test.py tests/game_state_transition_test.py` for domain checks. Run the related application, API, migration, and history tests through the same wrapper. Stage the intended files, run `bash scripts/check-docs.sh`, and run the [full Stop hook](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing) before pushing. Confirm formatting, lint, and pytest ran and passed.

In both modes, use seeded positions to submit a black forbidden move under each enabled setting. Warn must report the reason, preserve board and history, and allow a legal retry. Loss must persist exactly one final move and a white win, and the board must stay closed after reload. Also verify a black overline wins under Off and games saved before migration load under Off.

If a response is lost, reload by ID and compare status, reason, revision, and history before retrying. Exercise rollback of the stone and result together in the history failure test. Apply the compatible schema before deploying feature code. Finish updating all writers before exposing enabled choices. During recovery, keep writes to enabled games on compatible code and retain the saved records.

## Pull requests

| PR | Deliverables and acceptance |
| --- | --- |
| Plan | This document on `plan/black-forbidden-moves`, with documentation and full delivery validation. |
| Feature | Approved English contracts, domain and CPU rules, migration, API, UI, and tests. Start after documentation approval and obtain explicit schema approval before schema work. Deliver implementation together so every available choice is enforced by move processing and CPU prediction. |

## Progress and review

- [x] 2026-11-27 Confirmed shared move validation, black-first CPU ownership, occupied-cell revision, and transactional history. Drafted settings and acceptance checks.
- [ ] Draft feature documentation and record human approval.
- [ ] Record explicit schema-change approval.
- [ ] Implement and validate milestones 2–4.
- [ ] Record results and retrospective and move this plan to the completed directory.

## Outcomes and retrospective

Feature implementation and acceptance are pending. Record validation results, rule cases that exposed gaps, and follow-up work before completing this plan.
