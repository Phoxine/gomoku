# Close the Game Coverage Test Gaps

## Goal and scope

Add focused tests for four defensive paths in [`apply_move`](../../../src/app/domain/game/service/game_service.py) and the [`Game` string representation](../../../src/app/domain/game/model/game.py). Use the existing [state transition suite](../../../src/tests/game_state_transition_test.py) and [Django model integration test](../../../src/tests/game_model_test.py). Keep test assertions aligned with the existing game rules and model behavior.

The starting observation is a local run of [PR #74](https://github.com/Phoxine/gomoku/pull/74) at `1b09a6a` with temporary subprocess tracking. All 229 tests passed and coverage recorded 254 of 259 executable lines (98.07%). The measured gaps were `game_service.py` lines 86, 88, 93 and 99, and `game.py` line 54. Use the behavior names below to locate them if line numbers have shifted.

## Milestones

1. After [PR #74](https://github.com/Phoxine/gomoku/pull/74) lands, start an isolated worktree from synchronized `origin/main`. From its root, run `bash scripts/init-worktree-env.sh` and `bash scripts/compose.sh up --build -d`. Record the commit and rerun the coverage command below to confirm which gaps remain.
2. Add focused cases in `game_state_transition_test.py` for an invalid status, an invalid current player, a winner attached to a game in progress or a drawn game, and a non-`Move` argument. Assert the expected `ValueError` or `TypeError` and its diagnostic. Build malformed state explicitly and use the existing valid-state fixture for the wrong move type so the intended guard is reached. Keep these cases independent of Django.
3. Extend the existing model integration test after it creates a saved `Game`. Assert that `str(game)` contains the expected representation of its actual primary key and status. Use the existing temporary PostgreSQL test database and its cleanup.

## Validation and pull request

Run these commands from the worktree root:

```bash
bash scripts/compose.sh exec -T app uv run pytest -q tests/game_state_transition_test.py tests/game_model_test.py
bash scripts/compose.sh exec -T app uv run pytest --cov=app --cov-config=/workspace/pyproject.toml --cov-report=term-missing --cov-report=xml tests
```

Both runs must pass. Inspect the terminal report or `src/coverage.xml` and confirm the five target lines are recorded as covered. Use the refreshed baseline to explain any unrelated gaps. Run the full [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing).

Deliver the cases together in one test PR after the subprocess coverage configuration in PR #74 has landed. Record the before-and-after coverage, tests added, and CI results in the PR and this plan. Archive the plan once the acceptance checks pass.

## Recovery

If the coverage run does not record the model assertion, check that subprocess tracking is active and the model test executed. Inspect the app and database services with `bash scripts/compose.sh ps -a` if Django startup fails. For PostgreSQL failures, check the first failing assertion or setup error before retrying. Keep the worktree's database volume and use the existing integration test's per-run database setup and cleanup.

## Progress and decisions

- [x] 2026-11-23. Identified five uncovered lines after enabling subprocess tracking.
- [ ] Confirm the baseline on the merged configuration.
- [ ] Add and verify the game state and model tests.
- [ ] Record CI results and archive the plan.

## Outcomes and retrospective

Implementation and verification are pending.
