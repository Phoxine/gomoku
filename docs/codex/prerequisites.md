# Codex Host Prerequisites

Install `uv` on the host before using Codex with this repository. The
PreToolUse hook runs the command policy through `uv`; the hook reports a clear
error and exits if `uv` is unavailable.

## Optional: allow writes to task worktrees

When using the `workspace-write` sandbox, you can add the shared task worktree
directory to your personal `~/.codex/config.toml`. Replace the example with the
absolute path to `gomoku-worktrees` on your machine:

```toml
[sandbox_workspace_write]
writable_roots = ["/absolute/path/to/gomoku-worktrees"]
```

If the table or `writable_roots` already exists, update it rather than adding a
duplicate, and preserve any existing paths. This grants write access to all
contents of that directory. Start a new Codex session and verify its effective
permissions; managed policies may restrict them. Git worktree creation also
updates shared Git metadata and may still require approval.

## Optional: allow routine Compose cleanup without a prompt

The host cleanup helper is for a local Docker Unix socket and worktrees that use
Gomoku's path-bound Compose project names. It stops and removes that worktree's
Compose containers and networks, while retaining its database volume.

Review `scripts/stop-local-stack-host.py` in a trusted checkout, then install a
copy outside Codex's writable roots. Run this once on each machine:

```bash
/usr/bin/python3 --version
install -d -m 700 "$HOME/.local/libexec/gomoku"
install -m 500 scripts/stop-local-stack-host.py "$HOME/.local/libexec/gomoku/stop-local-stack.py"
```

Set the following values in `$HOME/.local/libexec/gomoku/cleanup.json`. Use
absolute paths and the socket for the same local engine used by Compose.
`command -v docker` gives the executable path, and `docker context inspect`
shows the current context's endpoint.

```json
{
  "repository_root": "/absolute/path/to/gomoku",
  "worktrees_root": "/absolute/path/to/gomoku-worktrees",
  "docker_binary": "/usr/local/bin/docker",
  "docker_host": "unix:///absolute/path/to/docker.sock"
}
```

Add this rule to `~/.codex/rules/default.rules`, substituting your actual home
directory. Keep the installed helper and its configuration outside the paths
Codex can write.

```python
prefix_rule(
    pattern = ["/usr/bin/python3", "-I", "-S", "/absolute/home/.local/libexec/gomoku/stop-local-stack.py"],
    decision = "allow",
)
```

Open a new Codex session and run the exact command below from the root of the
worktree you intend to stop, substituting the same absolute path as in the rule.
The helper accepts no arguments and checks that the checkout is registered as a
Gomoku worktree before contacting Docker.

```bash
/usr/bin/python3 -I -S /absolute/home/.local/libexec/gomoku/stop-local-stack.py
```

Without the host helper, run `bash scripts/stop-local-stack.sh` and approve
Docker access if prompted. Use that same fallback for a leftover network when
no Compose containers remain to confirm its ownership. For a legacy Compose
project, verify which worktree owns it before using `bash scripts/compose.sh down`.
Obtain explicit authorization before deleting a database volume.
