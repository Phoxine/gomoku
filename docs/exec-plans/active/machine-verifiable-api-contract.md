# Machine-Verifiable API Contract

## Goal and scope

Assess a machine-readable contract for the game API when a second consumer is planned or recurring client and server shape mismatches are observed. The first candidate is an OpenAPI description for the existing endpoints. Start from the [game API reference](../../domains/game/apis.md), [URL configuration](../../../src/config/urls.py), [DTOs](../../../src/app/api/game_dto.py), [HTTP handlers](../../../src/app/api/game_views.py), and [API integration tests](../../../src/tests/game_api_test.py).

## Milestones

1. Record the trigger, affected consumers, and concrete examples of contract drift or duplicated integration work. If the trigger is absent, record the evidence and leave this plan deferred.
2. Inventory the CSRF route, game creation, game retrieval, and move submission. Map paths, methods, request bodies, status codes, and JSON response shapes. Include the observed CSRF behavior, such as a middleware rejection whose body can be HTML, and maintain the documented error behavior.
3. Compare a small hand-authored OpenAPI contract with generation from the existing Django views or DTOs. Try both against the move endpoint before choosing the maintenance source. Prefer a route that reuses the existing DTO contract and avoids contradictory shape definitions. Establish which description owns wire shapes and which page owns usage and domain meaning. Keep new dependencies within the project's approval policy.
4. If adopted, verify the contract syntax and compare real responses in the PostgreSQL-backed API tests. Use `bash scripts/compose.sh exec -T app uv run pytest -q tests/game_api_test.py` for the existing baseline. Document the exact contract check and any regeneration command in the PR.

## Acceptance and pull requests

- **API contract PR.** Include the adoption decision and baseline evidence. If adopted, include the machine-readable contract, its maintenance instructions, and contract checks. Compare an accepted move response and rejected requests with the live endpoint. An intentional scratch mismatch, such as changing a documented integer coordinate to a string, must fail and identify the affected operation and field. Add version-controlled passing and rejected cases to the relevant job when executable CI tooling is added.
- **Optional client adoption PR.** Wait for the verified contract and a specific consumer. Demonstrate that an actual consumer builds or validates requests against the contract before removing duplicated shape declarations.

If the prototype drifts from Django behavior, compare route and middleware behavior with the DTOs before retrying. Keep temporary contracts and clients outside tracked changes until the approach is selected. Revert an unhelpful validator or consumer adoption independently.

## Worktree and recovery

Run commands from this plan's dedicated worktree. Record `git status --short` and `git rev-parse HEAD` before starting. When the work needs Django and PostgreSQL, run `bash scripts/init-worktree-env.sh` and `bash scripts/compose.sh up --build -d`. Confirm `app` is listed by `bash scripts/compose.sh ps --status running --services`. If startup is interrupted, inspect `bash scripts/compose.sh ps -a` and follow the [Compose troubleshooting guide](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) before retrying in the same worktree.

Run `bash scripts/check-docs.sh` after staging documentation changes. Use the full [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Confirm Ruff formatting, Ruff lint, and pytest completed. If the hook reports `Skipping final validation`, restore the running app and retry. After pushing, use `bash scripts/stop-local-stack.sh` to stop the containers and keep the worktree's database volume.

## Progress and decisions

- [x] 2026-11-20. Defined scope and acceptance from baseline `eff8579`.
- [ ] Record whether an adoption trigger has occurred.
- [ ] Inventory routes and compare contract prototypes on move submission.
- [ ] Record the adoption decision and run contract checks if adopted.

## Outcomes and retrospective

Pending implementation or adoption review. Record the evidence, decisions, open gaps, and follow-up before moving this plan to `docs/exec-plans/completed/`.
