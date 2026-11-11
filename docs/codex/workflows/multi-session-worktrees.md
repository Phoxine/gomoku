# Multi-Session Worktree Workflow

Use one Git worktree and one Docker Compose project for each concurrently developed feature. Compose project names scope the containers, default network, and named volumes; each worktree also has its own local environment files and bind-mounted source tree.

```bash
git fetch origin main
git worktree add ../gomoku-feature-name -b feature/gomoku-feature-name origin/main
cd ../gomoku-feature-name
bash scripts/init-worktree-env.sh
docker compose up --build -d
```

Run Compose commands from the worktree root. The initializer derives `COMPOSE_PROJECT_NAME` from the branch, generates a local database password when one is missing, and copies `src/.env.example` to `src/.env` when needed. It refuses to use symlinked env files or silently repurpose a root `.env` configured for another project.

Compose uses the default project-scoped network and `postgres_data` volume. The database is not published on a host port; the app reaches it at `db:5432`. Keep project dependencies and databases in Docker. If a future service needs a host-published port, assign a distinct host port in each worktree's root `.env` and use that variable in the Compose port mapping.

```bash
docker compose ps
docker compose exec app uv run pytest
docker compose down
```

`docker compose down` stops and removes this project's containers and network while retaining its database volume. `docker compose down -v` also deletes this worktree's database data.

For another feature, create another branch and worktree and initialize its environment separately. Do not share `.env` files or Compose project names between worktrees. See [`scripts/init-worktree-env.sh`](../../../scripts/init-worktree-env.sh) for the initializer behavior.
