---
name: create-worktree
description: Create a separate Git worktree and isolated Docker Compose stack for repository changes. Use by default for each new task unless the user explicitly directs work in the current worktree or names another existing branch or worktree.
---

# Create an Isolated Feature Worktree

Keep the current worktree and branch unchanged. Use this workflow by default for each new task that changes repository files, including sequential tasks; do not create a worktree for read-only requests. If the user explicitly directs work in the current worktree or names another existing branch or worktree, inspect that target and use it if the request is unambiguous and the work will not overwrite or mix unrelated changes. Ask only if the target is ambiguous or using it could overwrite or mix unrelated changes.

Always create new branches from synchronized `origin/main`, never from the currently checked-out task branch. Derive a short slug from the request and create a sibling checkout at `../gomoku-<task-slug>`. Use `feature/gomoku-<task-slug>` for product features, `infra/<task-slug>` for worktree, Docker, CI, or other development infrastructure, `fix/<task-slug>` for bug fixes, `docs/<task-slug>` for documentation, and `refactor/<task-slug>` for refactoring without functional changes. If the branch or path already exists and the user has not explicitly named it, inspect it and ask before reusing or changing it.

```bash
# Product feature example; use origin/main as the base.
git fetch origin main
git worktree add ../gomoku-online-match -b feature/gomoku-online-match origin/main
cd ../gomoku-online-match
bash scripts/init-worktree-env.sh
bash scripts/compose.sh up --build -d
```

For infrastructure work, use the `infra/<task-slug>` branch namespace instead.

The initializer creates a private root `.env` with a `COMPOSE_PROJECT_NAME` derived from the readable branch name and a stable hash of the canonical worktree path. This prevents sanitized branch-name collisions and keeps the initialized project name stable if the branch is renamed. It generates a PostgreSQL password when one is missing and copies `src/.env.example` to `src/.env` if needed. Compose reads `COMPOSE_PROJECT_NAME` from the root `.env`; do not put it only in `src/.env`, because service `env_file` values do not select the Compose project. Never symlink either env file from another worktree.

Use `bash scripts/compose.sh` for startup, validation, and cleanup. It passes the root `.env` project name explicitly, so exported shell variables cannot redirect the command. Each Compose project has its own containers, default network, and `postgres_data` volume. The database has no host-published port, and the worktree is mounted into only its own app container. If a future service needs a host-published port, assign a distinct per-worktree host port in the root `.env` before starting it.

Tell the user the branch name, absolute worktree path, and Compose project name so another session can open that directory. Do not commit, push, merge, or remove worktrees unless requested.

The resolver uses Docker Compose's dotenv parser with a minimal probe configuration. The initializer serializes concurrent runs, creates and updates environment files atomically, cleans temporary files on exit, and Git ignores `.env.*` temporary files. Existing legacy and directory-default project names remain available so their volumes stay attached. If a default project's database volume exists, preserve its project name and original password or migrate the database explicitly before switching.

For the environment variable split and cleanup behavior, see [`docs/codex/workflows/multi-session-worktrees.md`](../../../docs/codex/workflows/multi-session-worktrees.md).
