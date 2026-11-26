# CPU Forcing Defense Execution Plan

**Status** — Completed

## Goal and scope

After checking immediate wins for both sides, prioritize white moves that create two or more winning intersections. Otherwise, when several white moves prevent black from forcing a win through a double threat, prefer a defense that also forces black to answer a white winning point and gives white a safe follow-up. When no complete defense is possible, leave black the fewest replies that can still force a win through a double threat. This change applies to the [game rules service](../../../src/app/domain/game/service/game_service.py), its tests, and the [CPU selection design](../../domains/game/context-designs.md#cpu-move-selection). The [CPU turn contract](../../domains/game/apis.md#advance-the-cpu-turn), browser, persistence, and database schema require no changes.

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

The later position before move 26 in that game has no complete defense. A separate reported game below illustrates how white chooses a partial defense in this situation.

## Proposed selection

1. Preserve the immediate white-win and immediate black-block paths, including their row and column order.
2. Select a white move that creates at least two distinct winning intersections for the next white turn, even if black has no double threat. Rank qualifying moves by squared distance to `(7, 7)`, then ascending row and column.
3. Otherwise, identify the white moves that defend against all of black's double threats. Each black reply counts as a forcing threat when it creates two or more winning points and leaves white without an immediate win.
4. Give preference to a defense that leaves exactly one immediate white winning intersection, gives black no immediate win, and passes the follow-up check. Simulate black occupying that intersection. The check passes if the resulting position is a draw or white has a legal next move that wins immediately or leaves black with neither an immediate win nor a forcing double-threat reply. Apply the same requirements when the next white move blocks an immediate black threat.
5. Rank qualifying forcing defenses by the same distance and coordinate ordering. If none qualifies, choose the white move that leaves the fewest distinct black replies that would create two or more winning intersections without leaving an immediate white win. A complete defense leaves zero. Break ties by the same distance and coordinate ordering. If black has no forcing replies, use the closest legal intersection to the center.

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
| Reported position before move 36 | White chooses `(7, 9)` and can win at `(4, 6)` or `(9, 11)` on its next turn after every legal black reply. |
| A candidate creates a winning point but fails the existing defense or the follow-up check | The candidate receives no forcing preference. |
| Several forcing defenses pass | Choose by distance to center, then row and column. |
| Neither side can win immediately and white has no two-point win or qualifying single-point defense | The CPU minimizes remaining forcing black replies and breaks ties by distance, row, and column. With no forcing replies, the CPU selects the closest legal move using the same tie-break order. |
| Reported position before move 26 with no complete defense | White chooses `(7, 4)`, leaving only black reply `(10, 7)` that can create a double threat. |
| CPU command and duplicate request | The command advances revision 21 to 22 and records exactly one white move. The duplicate adds no move. |
| Selector timing | Benchmark results are reproducible and code review accepts the observed latency. |

- **Plan PR.** Deliver this document with the documentation checker and full repository validation. It can merge before #98.
- **Feature PR.** Deliver the approved English design, selector changes, regression tests, and integration coverage together after #98 merges.

## Recovery

If the reproduction differs from the baseline, verify the fixture's 21 recorded moves and the merged #98 behavior before changing selection. For a candidate ranked unexpectedly, inspect both colors' immediate winning points, the black reply, and the available white follow-ups. If runtime increases materially, profile the follow-up search and check the results against direct simulation before acceptance.

If the preference needs to be reverted, restore the #98 ordering among effective defenses. Saved positions and move history continue to use the existing persistence path.

## Progress and decisions

- [x] 2026-11-26. Replayed all 29 moves from the reported game. All 14 white moves matched the #98 selector. Simulated the forcing alternative on move 22 and verified a safe follow-up after black blocks.
- [x] 2026-11-26. Confirmed both prerequisite PRs merged and opened the implementation worktree from `origin/main` at `80ce833`. Drafted the [CPU selection design](../../domains/game/context-designs.md#cpu-move-selection) and [CPU product specification](../../product-specs/local-cpu-game.md#play-a-turn), and verified the existing CPU turn contract covers the proposed behavior.
- [x] 2026-11-26. The requester explicitly approved the English feature documentation and selection design before implementation.
- [x] 2026-11-26. Confirmed the regression fails against the merged selector and passes after implementation. Verified both tie-breakers and rejected candidates that fail the original defense or the follow-up check.
- [x] 2026-11-26. Replayed the real CPU commands at revisions 21 and 23. Verified the responses and matching PostgreSQL history entries, and confirmed the duplicate revision 21 request left the newer pending turn intact.
- [x] 2026-11-26. Accepted the implementation and measured responsiveness in code review. Passed 83 focused tests, documentation checks for 48 Markdown files and 28 checker tests, and the full Stop hook with Ruff formatting, lint, and 259 tests.
- [x] 2026-11-26. The requester explicitly approved adding the two-winning-point priority to PR #100 after reviewing the move 36 replay.
- [x] 2026-11-26. Confirmed the move 36 regression failed at `d2f7321` and passed with the new priority. Code review, Ruff, 86 focused tests, 262 full-suite tests, and the documentation checker passed.
- [x] 2026-11-26. The requester approved minimizing the remaining forcing replies when no complete defense exists after reviewing the move 26 replay.
- [x] 2026-11-26. Confirmed the move 26 regression failed at `f3210ef` and passed with the partial-defense ranking. The focused suite passed 87 tests.

## Outcomes and retrospective

The reported position now produces white `(4, 9)` at revision 22. Black's sole block is `(3, 10)` at revision 23, and the real selector follows with white `(5, 9)` at revision 24. Direct move simulation confirmed no immediate black win or forcing black double-threat reply after the last move. Each accepted request appends one matching history entry. A duplicate CPU request at revision 21 adds none.

The single-point defense preference checks only the forced black block and the next white placement. Game `7b99ad94-0506-4553-abe9-4e0c92fb0c98` exposed a higher-priority opportunity on move 36. The original forcing-defense implementation chose `(8, 9)` and left black a block at `(8, 11)`. The two-winning-point rule chooses `(7, 9)`, creating winning points at `(4, 6)` and `(9, 11)`. Direct simulation of all 189 legal black replies confirmed that white can win on its next turn. The [rules regression](../../../src/tests/game_service_test.py) replays this position.

In game `9f7467c8-b6af-4497-971d-d9c82cb9fb23`, white's move 26 at `(9, 7)` left three forcing black replies. White moves `(7, 4)` and `(11, 4)` both leave only `(10, 7)`, which threatens `(10, 3)` and `(10, 8)`. The updated ranking selects `(7, 4)` because it is closer to the center. The remaining black reply still forces a win.

### Selector timing

The partial-defense change was measured against `f3210ef` using the same alternating method below. The opening uses black at `(7, 7)`. The reported fixture uses the first 25 moves from the move 26 regression. The dense fixture uses the pattern below before adding the three white stones at row 5.

| Position | Baseline median / p95 (ms) | Partial defense median / p95 (ms) |
| --- | ---: | ---: |
| Sparse opening | 1.60 / 2.88 | 1.58 / 2.97 |
| Reported move 26 | 2.38 / 5.15 | 2.54 / 5.67 |
| Dense board with no complete defense | 1.32 / 2.90 | 1.62 / 3.37 |

#### Original forcing-defense benchmark

These measurements cover the original forcing-defense change at `d2f7321`. The baseline was `80ce833`. Both versions ran in the same isolated app container and Python process. Each fixture used 20 warm-up calls and 500 timed calls per selector. Each sample alternated which selector ran first. The timings cover the selector call alone.

| Position | Stones | Baseline median / p95 (ms) | Updated median / p95 (ms) |
| --- | ---: | ---: | ---: |
| Sparse opening | 1 | 1.76 / 5.08 | 1.78 / 5.02 |
| Reported move 22 | 21 | 2.12 / 5.29 | 2.35 / 5.61 |
| Dense board with multiple defenses | 135 | 1.25 / 2.43 | 1.49 / 3.20 |

The reported position had the highest updated p95 at 5.61 ms. The dense position had the largest p95 increase at 0.77 ms. Code review accepted the measured responsiveness within the CPU transaction.

To reproduce the historical comparison, run the following from an isolated checkout at `d2f7321` with its app container active.

```bash
git show 80ce833:src/app/domain/game/service/game_service.py > /tmp/gomoku-forcing-baseline.py
sed -n '/^moves = \[/,/^\]/p' docs/exec-plans/completed/cpu-forcing-defense.md > /tmp/gomoku-forcing-moves.py
cat > /tmp/gomoku-forcing-benchmark.py <<'PY'
from statistics import median, quantiles
from time import perf_counter_ns

from app.domain.game.service.game_service import select_cpu_move as updated

baseline = select_cpu_move
sparse = initialize_board()
sparse[7][7] = 1
reported = initialize_board()
for i, (x, y) in enumerate(moves):
    reported[y][x] = 1 + i % 2
dense = initialize_board()
for y in range(7, 15):
    for x in range(15):
        dense[y][x] = 1 if (x + 2 * y) % 4 < 2 else 2
for y in (0, 3):
    for x in (2, 3, 5, 9, 10, 12):
        dense[y][x] = 1
for x in (0, 2, 4):
    dense[5][x] = 2
for name, board in (("sparse", sparse), ("reported", reported), ("dense", dense)):
    selectors = (baseline, updated)
    timings = ([], [])
    print(name)
    for _ in range(20):
        for select in selectors:
            select(board)
    for sample in range(500):
        for index in (sample % 2, 1 - sample % 2):
            start = perf_counter_ns()
            selectors[index](board)
            timings[index].append((perf_counter_ns() - start) / 1_000_000)
    for select, timings_ms in zip(selectors, timings, strict=True):
        print(select(board), f"{median(timings_ms):.2f}", f"{quantiles(timings_ms, n=100)[94]:.2f}")
PY
cat /tmp/gomoku-forcing-baseline.py /tmp/gomoku-forcing-moves.py /tmp/gomoku-forcing-benchmark.py > /tmp/gomoku-forcing-timing-input.py
bash scripts/compose.sh exec -T app uv run python - < /tmp/gomoku-forcing-timing-input.py
```
