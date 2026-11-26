# CPU Forcing Defense Execution Plan

**Status** — Draft for review

## Goal and scope

When several white moves prevent black from forcing a win through a double threat, prefer a defense that also forces black to answer a white winning point and gives white a safe follow-up. Preserve the priorities for an immediate white win and an immediate black block. This change applies to the [game rules service](../../../src/app/domain/game/service/game_service.py), its tests, and the [CPU selection design](../../domains/game/context-designs.md#cpu-move-selection). The [CPU turn contract](../../domains/game/apis.md#advance-the-cpu-turn), browser, persistence, and database schema require no changes.

The plan PR can land independently on `main`. Implementation depends on [PR #98](https://github.com/Phoxine/gomoku/pull/98), which supplies the double-threat defense. Start the feature branch from `origin/main` after #98 merges and confirm the reproduction against the merged selector.

### Reproduce the decision

The local CPU game `5ec21865-da7b-4ae0-8c4a-c938a2125c22` reached the following position before move 22, with white to move. Replay these moves from an empty board in order, alternating black and white starting with black. Coordinates are zero-based `(x, y)`.

```python
moves = [
    (7, 7), (7, 6), (6, 8), (6, 7), (8, 8), (8, 7), (7, 8),
    (5, 8), (8, 5), (6, 6), (8, 6), (9, 5), (9, 8), (10, 8),
    (7, 9), (7, 5), (7, 10), (7, 11), (8, 9), (10, 7), (6, 9),
]
```

On move 22, the selector in #98 chooses `(5, 9)` by proximity to the center. White can instead play `(4, 9)`, creating a single winning intersection at `(3, 10)`. Black has no immediate win and must occupy `(3, 10)` to prevent white from winning. White can then play `(5, 9)` to stop the projected double threats. Test this continuation independently of the original saved game and its ID.

The later position before move 26 has no complete defense. It illustrates a separate fallback policy decision. This plan keeps the existing center fallback in that case and in positions without a forcing black reply.

## Proposed selection

1. Preserve the immediate white-win and immediate black-block paths, including their row and column order.
2. If the base selector finds black double threats, consider only the white moves that defend against all of them under the existing rule. A black reply that leaves an immediate white win is already covered by that rule.
3. Give preference to a defense that leaves exactly one immediate white winning intersection, gives black no immediate win, and passes the follow-up check. Simulate black occupying that intersection. The check passes if the resulting position is a draw or white has a legal next move that wins immediately or leaves black with neither an immediate win nor a forcing double-threat reply. Apply the same requirements when the next white move blocks an immediate black threat.
4. Rank qualifying forcing defenses by squared distance to `(7, 7)`, then ascending row and column. If no defense qualifies, preserve the existing defense ordering and center fallback. Creating two immediate white winning intersections and general offensive scoring are outside this preference.

## Milestones

### 1. Draft English feature documentation and obtain approval

Read the domain design and CPU product specification in full. Follow the [feature documentation skill](../../../.agents/skills/document-feature/SKILL.md) to integrate the forcing-defense preference, forced reply, follow-up requirement, and tie-breaking into the existing CPU selection section. Update the [CPU product specification](../../product-specs/local-cpu-game.md) to explain the observable behavior. Review the CPU turn contract for compatibility, run the documentation checker, and record explicit human approval of the drafts here before implementation.

### 2. Add the regression and implement the preference

1. Add the 21-move fixture to the [rules tests](../../../src/tests/game_service_test.py). Confirm the expected move 22 fails on the merged baseline, then retain the assertion. Independently verify the unique white winning point, the forced black reply, and a legal defensive follow-up using the existing board rules.
2. Reuse the base selector's window and candidate evidence to filter white moves before simulating forced replies. Limit the additional evaluation to one forced black reply and one subsequent white candidate search. Use the existing tactical checks for that search without recursively applying the new forcing-defense ranking. Keep the selector deterministic and preserve the input board.
3. Cover the cases in the acceptance table. Compare baseline and new execution time in the same container for the reproduction, a sparse opening, and a dense position with multiple candidate defenses. Record the baseline commit, fixtures, command, sample count, median, and p95. Review the largest observed increase, since selection runs inside the CPU transaction.

### 3. Verify integration and complete delivery

Send an actual CPU command on a pending position at revision 21. Verify that it commits one white stone at `(4, 9)`, returns revision 22, and appends one matching history entry. Retry the same revision and check the board and history again. Use the [move history integration tests](../../../src/tests/game_move_history_test.py) as the entry point.

Run repository checks, sync the approved design with the implementation, and record the results here. Move the plan to `docs/exec-plans/completed/` after acceptance.

## Validation and acceptance

Run from the checkout root with its isolated Compose stack.

```bash
bash scripts/check-docs.sh
bash scripts/compose.sh exec -T app uv run pytest -q tests/game_service_test.py tests/game_state_transition_test.py tests/game_application_service_test.py tests/game_application_service_unit_test.py tests/game_api_test.py tests/game_move_history_test.py
bash .codex/hooks/stop-validation.sh
```

| Scenario | Expected result |
| --- | --- |
| Reported position before move 22 | White chooses `(4, 9)`; black has no immediate win and must block `(3, 10)`; white can then defend with `(5, 9)`. |
| White can win immediately or black has an immediate win | Existing priority and tie order apply. |
| A candidate creates a winning point but fails the existing defense or the follow-up check | The candidate receives no forcing preference. |
| Several forcing defenses pass | Choose by distance to center, then row and column. |
| No forcing defense passes, no forcing reply exists, or no complete defense exists | Existing choice is preserved. |
| CPU command and duplicate request | The command advances revision 21 to 22 and records exactly one white move. The duplicate adds no move. |
| Selector timing | Benchmark results are reproducible and code review accepts the observed latency. |

- **Plan PR.** Deliver this document with the documentation checker and full repository validation. It can merge before #98.
- **Feature PR.** Deliver the approved English design, selector changes, regression tests, and integration coverage together after #98 merges.

## Recovery

If the reproduction differs from the baseline, verify the fixture's 21 recorded moves and the merged #98 behavior before changing selection. For a candidate ranked unexpectedly, inspect both colors' immediate winning points, the black reply, and the available white follow-ups. If runtime increases materially, profile the follow-up search and check the results against direct simulation before acceptance.

If the preference needs to be reverted, restore the #98 ordering among effective defenses. Saved positions and move history continue to use the existing persistence path.

## Progress and decisions

- [x] 2026-11-26. Replayed all 29 moves from the reported game. All 14 white moves matched the #98 selector. Simulated the forcing alternative on move 22 and verified a safe follow-up after black blocks.
- [ ] Approve the English feature design.
- [ ] Confirm the baseline regression, implement the preference, and record timing.
- [ ] Verify the real CPU command, complete repository validation, and deliver the feature PR.

## Outcomes and retrospective

Implementation and acceptance are pending. Record the verified move sequence, benchmark results, reviewed limitations, and validation outcomes here.
