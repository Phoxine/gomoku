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
docker compose up --build -d
```

For infrastructure work, use the `infra/<task-slug>` branch namespace instead.

The initializer creates a private root `.env` with a branch-specific `COMPOSE_PROJECT_NAME` and a generated PostgreSQL password when one is missing. It copies `src/.env.example` to `src/.env` if needed. Compose reads `COMPOSE_PROJECT_NAME` from the root `.env`; do not put it only in `src/.env`, because service `env_file` values do not select the Compose project. Never symlink either env file from another worktree.

Each Compose project has its own containers, default network, and `postgres_data` volume. The database has no host-published port, and the worktree is mounted into only its own app container. Run Compose commands from the new worktree root so they use its configuration. If a future service needs a host-published port, assign a distinct per-worktree host port in the root `.env` before starting it.

Tell the user the branch name, absolute worktree path, and Compose project name so another session can open that directory. Do not commit, push, merge, or remove worktrees unless requested.

For the environment variable split and cleanup behavior, see [`docs/codex/workflows/multi-session-worktrees.md`](../../../docs/codex/workflows/multi-session-worktrees.md).
