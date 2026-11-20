# Worktree Observability

## Goal and scope

Make a recurring performance problem or intermittent failure diagnosable in a single isolated worktree. Start with existing service logs and add metrics or traces only when needed to answer the recorded debugging question. Use the [architecture and request flow](../../../ARCHITECTURE.md), [security rules](../../../.codex/rules/security.md), [Compose configuration](../../../compose.yaml), and [worktree isolation guide](../../../.agents/skills/create-worktree/references/multi-session-worktrees.md). The [Harness Engineering example](https://openai.com/index/harness-engineering/#increasing-application-legibility) exposes runtime evidence per worktree.

## Milestones

1. Record one reproducible symptom and the evidence currently available. For an HTTP scenario, run `APP_PORT=8765 bash scripts/start-local-server.sh` in a fresh worktree, substituting an unused port. Confirm the page responds within a bounded readiness window before submitting moves. Run `bash scripts/compose.sh ps` and inspect the relevant app or database logs with `bash scripts/compose.sh logs --tail 50 app db`. Check what can already be diagnosed from status and timing events. If no recurring diagnostic gap is present, record that result and leave the plan deferred.
2. Pick a specific diagnostic question, such as whether slow move requests spend time waiting on a database operation. Prototype structured request events using a unique request identifier for logs. If logs cannot answer the question, try a duration metric or a trace in an optional development Compose profile. Define any labels, ports, storage, and cleanup. Avoid request identifiers as metric labels and follow the project's logging rules for secrets and player data.
3. Compare the same isolated scenario before and after instrumentation. For a controlled failure, use an invalid move request in a test game and verify which response and events identify the failure. Start two worktrees with different web ports and any collector ports kept distinct. Generate traffic in one worktree and verify only its collector or logs show that traffic. Confirm normal startup and tests also work with the optional instrumentation disabled.

## Acceptance and pull requests

- **Diagnostic logs PR.** Deliver only after a recurring gap is documented. Demonstrate that a successful move and a controlled rejected move yield distinct status events, correlate a request within the worktree, and leave request bodies, cookies, and credentials out of telemetry. Record the exact commands needed to reproduce and inspect evidence.
- **Optional metrics or traces PR.** Proceed after testing the log baseline and identifying the missing signal. Document the query or trace needed to answer the diagnostic question. Verify two-worktree isolation, startup with the profile disabled, bounded local retention, and cleanup. The browser smoke test and API contract plans are independent.

If startup or isolation breaks, disable the optional profile and recheck the default stack. Inspect only the affected worktree's Compose resources before retrying. Remove prototype instrumentation in its own change if it adds cost without new evidence.

## Worktree and recovery

Run commands from this plan's dedicated worktree. Record `git status --short` and `git rev-parse HEAD` before starting. When the work needs Django and PostgreSQL, run `bash scripts/init-worktree-env.sh` and `bash scripts/compose.sh up --build -d`. Confirm `app` is listed by `bash scripts/compose.sh ps --status running --services`. If startup is interrupted, inspect `bash scripts/compose.sh ps -a` and follow the [Compose troubleshooting guide](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) before retrying in the same worktree.

Run `bash scripts/check-docs.sh` after staging documentation changes. Use the full [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Confirm Ruff formatting, Ruff lint, and pytest completed.

If the hook reports `Skipping final validation`, address the stated cause. If the tracked `compose.yaml` is accidentally missing, confirm the deletion with `git status --short` and restore the file from the intended commit. If the root `.env` is missing or has no project name, run `bash scripts/init-worktree-env.sh` for a fresh worktree. For a previously initialized worktree, recover its original project name and local credentials before retrying so its database volume remains attached. Stop if the original settings cannot be recovered. Once the configuration is valid, start the intended stack as described above, confirm `app` is running, and rerun the hook.

After pushing, use `bash scripts/stop-local-stack.sh` to stop the containers and keep the worktree's database volume.

## Progress and decisions

- [x] 2026-11-20. Defined scope and acceptance from baseline `eff8579`.
- [ ] Record a concrete diagnostic gap and capture the existing baseline.
- [ ] Test whether request events answer the diagnostic question.
- [ ] Add and verify a richer signal only if the gap persists.

## Outcomes and retrospective

Pending implementation or adoption review. Record the evidence, decisions, open gaps, and follow-up before moving this plan to `docs/exec-plans/completed/`.
