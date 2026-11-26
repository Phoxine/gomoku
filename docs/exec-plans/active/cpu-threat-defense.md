# CPU Threat Defense Execution Plan

**Status** — Draft for review

## Goal and scope

Teach the white CPU to defend before black can create two distinct immediate winning moves. Keep the existing priority for a white win and an immediate black threat. Use the [CPU product specification](../../product-specs/local-cpu-game.md), the [CPU selection design](../../domains/game/context-designs.md#cpu-move-selection), and the [game rules service](../../../src/app/domain/game/service/game_service.py) as the baseline. The work covers the CPU selector, regression tests, and documentation. It requires no public API, browser, database, or move history changes.

### Reproduction

Replay these first five moves on a 15×15 board using zero-based `(x, y)` coordinates. This sequence is sufficient to reproduce the position without the original saved game.

| Move | Player | Position |
| --- | --- | --- |
| 1 | Black | `(7, 6)` |
| 2 | White | `(7, 7)` |
| 3 | Black | `(6, 7)` |
| 4 | White | `(8, 7)` |
| 5 | Black | `(5, 8)` |

The current selector plays `(7, 8)` on move 6. Black then plays `(4, 9)` and can win next at either `(8, 5)` or `(3, 10)`. White blocks `(8, 5)` on move 8 and black wins at `(3, 10)`. A white move such as `(4, 9)` or `(8, 5)` at move 6 prevents that double threat.

## Proposed selection

- Take an immediate white win first. Otherwise block black's immediate winning move using the existing order. If black already has more than one winning move, white can block only one.
- When neither color can win immediately, look for a legal black reply that would leave at least two **distinct empty positions** at which black could win on its next turn. Include threats along different lines and patterns with gaps. Count a single position once even if it completes multiple lines. A black reply does not force a loss if white can win immediately in the resulting position.
- If these threats exist, look for white moves that eliminate every such forced threat. Test each candidate against the resulting black replies. Rank effective defenses by squared distance to the center, then ascending row and column. If every legal white move still leaves a forced threat, use the existing center fallback. Keep the center fallback for positions without a forced threat.
- Keep the selector deterministic and side-effect-free. Reuse the existing five-or-more rule. Keep all lookahead in the framework-independent rules service.

## Milestones

### 1. Draft feature documentation and obtain human approval

Read the affected documents in full and apply the [feature documentation skill](../../../.agents/skills/document-feature/SKILL.md). Integrate the threat definition, selection order, tie-breaking, and fallback into the existing CPU selection section. Update the CPU product specification if needed to describe the observable behavior. Review the [game API](../../domains/game/apis.md) for compatibility.

Run the documentation checker and record explicit human approval of the English drafts in this plan before implementing the selector.

### 2. Reproduce the weakness and implement threat defense

1. Add a regression in the [rules tests](../../../src/tests/game_service_test.py) using the five-move sequence above. Confirm that the old selector fails the requirement to prevent the double threat, then retain the assertion during implementation.
2. Preserve the immediate-win and immediate-block paths. Build the lookahead from the game rules. First identify potential black replies and their winning positions on the unchanged board. Adding a white stone can remove black winning positions or occupy a reply, so only the potential replies need reevaluation for each candidate defense. Check that proposed shortcuts agree with a straightforward simulated reference on representative fixtures.
3. Keep the search bounded by the board and avoid scanning all candidate defenses when the initial position has no potential double threat. Profile the old and new selector under the same container conditions on sparse, typical midgame, and dense threat-heavy positions. Record the fixtures, invocation, sample count, median, and p95. Review the worst measured positions for responsiveness before acceptance.

### 3. Verify integration and complete delivery

Run the focused rules, state transition, application service, API, and move history tests. Verify one CPU command on the reproduced position with the real selector and confirm the saved board and the single recorded white move agree. Keep the public response fields and revision behavior compatible.

Sync the approved design with the implementation. Record the observed behavior and timing results in this plan, run the full repository checks, and move the plan to `docs/exec-plans/completed/` after acceptance.

## Validation and acceptance

Run from the implementation worktree root with its isolated Compose stack.

```bash
bash scripts/compose.sh exec -T app uv run pytest -q tests/game_service_test.py tests/game_state_transition_test.py tests/game_application_service_test.py tests/game_application_service_unit_test.py tests/game_api_test.py tests/game_move_history_test.py
bash scripts/check-docs.sh
bash .codex/hooks/stop-validation.sh
```

| Scenario | Expected evidence |
| --- | --- |
| Reproduced position after move 5 | White prevents black from producing the two winning points on the diagonal. The regression verifies the defense by simulating black replies. |
| White win and black threat both available | White takes the immediate win. |
| One immediate black win with no white win | White blocks the winning coordinate. |
| Gapped or crossing double threat | Two different winning coordinates count as a double threat. A single coordinate completing multiple lines counts once. |
| White can win immediately after the projected black reply | The reply does not count as a forced loss for white. |
| Multiple effective defenses | The closest to the center wins the tie, followed by ascending row and column. |
| No effective defense or no threat | The documented fallback selects a legal cell. The existing full-board behavior and input-board immutability still pass. |
| Real CPU command on the regression position | Exactly one legal white stone commits and has one matching history record. The revision advances by one. |
| Selector timing | Baseline and new measurements are reproducible from the recorded fixtures and command. The review explicitly accepts the worst observed latency before delivery. |

- **Plan PR.** Deliver the plan for design review. Run the documentation checker and the required pre-push validation.
- **Feature PR.** Deliver the selector, tests, and approved English feature documentation together. The CPU and move history features are already on the base branch.

## Recovery

If the selector picks an unexpected move, replay the five-move example and inspect the immediate winning positions for both colors before evaluating potential black replies. Run the focused rules tests before returning to application-level tests. If latency is unacceptable, profile the candidate checks and compare optimized decisions with the simulated reference before retrying acceptance.

If a deployed strategy change needs to be reverted, restore the previously verified selector. The resulting revision, turn, and move history remain governed by the existing persistence path. Previously accepted stones remain part of their saved games.

## Progress and decisions

- [x] 2026-11-26. Replayed the reported CPU game and confirmed all four white moves matched the current selector. Identified move 6 as a defensive opportunity.
- [ ] Approve the feature documentation and selection design.
- [ ] Reproduce the failure, implement threat defense, and record baseline and new timing.
- [ ] Verify the real CPU command and complete feature delivery.

## Outcomes and retrospective

Implementation and acceptance are pending. Record the selected defense in the regression position, measured latency, reviewed limitations, and final validation results here.
