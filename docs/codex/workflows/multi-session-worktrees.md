# Multi-Session Worktree Workflow

Use one Git worktree and one Docker Compose project for each task that changes repository files, whether tasks are concurrent or sequential. Use the current worktree/branch or a specific existing target only when the user explicitly directs it. Read-only requests do not require a new worktree. Compose project names scope the containers, default network, and named volumes; each worktree also has its own local environment files and bind-mounted source tree.

```bash
git fetch origin main
git worktree add ../gomoku-feature-name -b feature/gomoku-feature-name origin/main
cd ../gomoku-feature-name
bash scripts/init-worktree-env.sh
bash scripts/compose.sh up --build -d
```

Run `bash scripts/compose.sh` for local Compose commands. The wrapper explicitly selects the root `.env` project and ignores conflicting exported project or database-password variables. The initializer derives `COMPOSE_PROJECT_NAME` from a readable branch slug and a stable hash of the canonical worktree path, then preserves that name across branch renames. It generates a local database password when one is missing and copies `src/.env.example` to `src/.env` when needed. It parses dotenv values with Docker Compose's parser using a minimal probe configuration, so blank passwords and a missing `src/.env` do not block initialization. It refuses symlinked env files and foreign project names. Existing legacy and directory-default project names remain supported to keep their current database volumes attached. If a default project's database volume exists, preserve its project name and original password or migrate the database explicitly before switching.

Compose uses the default project-scoped network and `postgres_data` volume. The database is not published on a host port; the app reaches it at `db:5432`. Keep project dependencies and databases in Docker. If a future service needs a host-published port, assign a distinct host port in each worktree's root `.env` and use that variable in the Compose port mapping.

```bash
bash scripts/compose.sh ps
bash scripts/compose.sh exec app uv run pytest
bash scripts/compose.sh down
```

`bash scripts/compose.sh down` stops and removes this project's containers and network while retaining its database volume. `bash scripts/compose.sh down -v` also deletes this worktree's database data.

For another feature, create another branch and worktree and initialize its environment separately. Do not share `.env` files or Compose project names between worktrees. Initialization uses a worktree-local lock and atomic file replacement. Temporary `.env.*` files are removed on normal exit or handled signals and ignored by Git. See [`scripts/init-worktree-env.sh`](../../../scripts/init-worktree-env.sh) for the initializer behavior.

## Environment Variables and Isolation

Each worktree must use its own Docker Compose project, environment files, containers, network, and database volume:
- Run `bash scripts/init-worktree-env.sh` in each feature worktree before starting Docker Compose. It creates a local root `.env`, fills blank isolation settings, and copies `src/.env.example` to `src/.env` if needed.
- `COMPOSE_PROJECT_NAME` belongs in the worktree's **root `.env`**. The initializer derives it from the branch name and a stable hash of the canonical worktree path, then preserves that project name across branch renames; values in the app service's `env_file` (`src/.env`) are loaded too late to select the project.
- Keep `POSTGRES_PASSWORD` in the root `.env`. Keep Django application settings such as `DJANGO_SECRET_KEY` and `DEBUG` in `src/.env`.
- Compose supplies `DATABASE_URL` to the app and connects it to the `db` service on that worktree's private Compose network.
- Do not publish the database port to the host. The app reaches Postgres using `db:5432`; each Compose project owns a separate network and `postgres_data` volume.
- Use `bash scripts/compose.sh` for every local Compose command. It resolves the project from the current worktree's root `.env` and explicitly selects that project, so an exported `COMPOSE_PROJECT_NAME` cannot redirect commands to another stack. Never symlink `.env` files between worktrees.
- The initializer preserves existing legacy and directory-default project names to keep their database volumes attached. Before switching an existing default project, it checks for its `postgres_data` volume and requires the original project name and password or an explicit database migration.
