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
