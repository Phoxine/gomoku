# Subagent Validation

Validate every newly added subagent before finalizing the change. A valid TOML file or a successful parent-agent response alone does not prove that the intended subagent ran. Follow higher-priority session instructions and permission requirements throughout this workflow.

## 1. Check registration and configuration

- Confirm that the role is registered under `[agents.<role>]` in `.codex/config.toml`, with a description and a `config_file` path relative to that configuration file.
- Parse the project configuration and the referenced role file as TOML. Confirm the role's sandbox mode, reasoning effort, instructions, and path match its intended responsibilities.
- Verify that Codex loads the effective configuration from the target worktree. For an app-server client, use `config/read` with that worktree's absolute `cwd` and inspect the role entry.

## 2. Dispatch and exercise the role

Use a normal, non-ephemeral Codex session in the target worktree. Explicitly request the new role and give it a small representative task with an observable result. Do not let the parent perform the task as a substitute. Examples:

- For a read-only reviewer, review a specific existing file and report findings or a clean result.
- For a test runner, execute an appropriate test through `bash scripts/compose.sh` in the worktree's isolated container. The main session manages container startup and shutdown; do not run lifecycle commands concurrently.
- For a researcher, assess a specific proposal against the existing architecture and return the requested assessment.
- For a role that edits files, use a disposable fixture or isolated temporary worktree and verify both the expected output and its allowed edit boundaries.

Record evidence that the requested role actually started, completed its task, and returned a result. Verify its role name and relevant runtime settings, not just the parent agent's claim. Check the observed actions and output against the role's instructions and sandbox constraints.

If the usual interface does not expose these events, a local Codex app-server client can inspect them:

1. Start `codex app-server --listen stdio://` in the target worktree. Initialize it and send `initialized`.
2. Use `config/read`, then `thread/start` with the worktree's `cwd` and an approval policy that can handle required requests. Start a turn that explicitly asks to spawn the role and wait for its result.
3. Observe the child `subAgentActivity` start and completion events. Use `thread/read` on the child thread to verify `agentRole`; check the reported reasoning effort and the child and parent completion results.
4. Handle permission requests using the normal approval process. Inspect the exact command and working directory; never automatically approve unrelated commands or bypass the sandbox. A Docker socket denial is not a test pass: request approval for the specific Compose command when required, retry, and verify the test result.

App-server uses newline-delimited JSON requests and notifications. Its protocol is experimental; consult the installed version's `codex app-server generate-json-schema --experimental --out <directory>` output if event or request fields differ. Do not use ephemeral sessions when validating child dispatch if they cannot retain the parent thread.

## 3. Report and resolve failures

Report the role, task, verified dispatch and completion, and result, including test counts where applicable. Distinguish configuration checks from actual execution. Fix role configuration or instructions and repeat the affected checks when they fail.

If execution is blocked by permissions, unavailable infrastructure, or a higher-priority restriction, report the specific blocker and mark the role's validation incomplete; do not claim success from static checks or fabricated results. Do not disable safeguards or grant broad permissions to make a test pass.
