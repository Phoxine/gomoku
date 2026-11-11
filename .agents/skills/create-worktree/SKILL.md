---
name: create-worktree
description: Create a separate Git worktree and isolated Docker Compose stack for parallel feature development in this repository. Use when asked to start a feature in another session instead of changing the current worktree.
---

# Create an Isolated Feature Worktree

Keep the current worktree and branch unchanged. Always create new branches from the repository's `main`, never from the currently checked-out task branch. Synchronize `main` with `origin/main` before branching. Derive a short slug from the request and create a sibling checkout at `../gomoku-<task-slug>`. Use `feature/gomoku-<task-slug>` for product features and `infra/<task-slug>` for worktree, Docker, CI, or other development infrastructure. If the branch or path already exists, inspect it and ask before reusing or changing it.

```bash
# Product feature example; use origin/main as the base.
git fetch origin main
git worktree add ../gomoku-online-match -b feature/gomoku-online-match origin/main
cd ../gomoku-online-match
bash scripts/init-worktree-env.sh
bash scripts/compose.sh up --build -d
```

For infrastructure work, use the `infra/<task-slug>` branch namespace instead.

The initializer creates a private root `.env` with a `COMPOSE_PROJECT_NAME` derived from the readable branch name and a stable hash of the canonical worktree path. This prevents sanitized branch-name collisions. It generates a PostgreSQL password when one is missing and copies `src/.env.example` to `src/.env` if needed. Compose reads `COMPOSE_PROJECT_NAME` from the root `.env`; do not put it only in `src/.env`, because service `env_file` values do not select the Compose project. Never symlink either env file from another worktree.

Use `bash scripts/compose.sh` for startup, validation, and cleanup. It passes the root `.env` project name explicitly, so exported shell variables cannot redirect the command. Each Compose project has its own containers, default network, and `postgres_data` volume. The database has no host-published port, and the worktree is mounted into only its own app container. If a future service needs a host-published port, assign a distinct per-worktree host port in the root `.env` before starting it.

Tell the user the branch name, absolute worktree path, and Compose project name so another session can open that directory. Do not commit, push, merge, or remove worktrees unless requested.

The resolver uses Docker Compose's dotenv parser with a minimal probe configuration. The initializer serializes concurrent runs, creates and updates environment files atomically, cleans temporary files on exit, and Git ignores `.env.*` temporary files. Existing legacy project names remain unchanged so their volumes stay attached; require explicit database migration before changing them.

For the environment variable split and cleanup behavior, see [`docs/codex/workflows/multi-session-worktrees.md`](../../../docs/codex/workflows/multi-session-worktrees.md).
