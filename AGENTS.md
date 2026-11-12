# AGENTS.md

## Project Overview
This is a web-based interactive Gomoku game built with Python 3.14 + Django + Django ORM + Postgres inside Docker containers.

## Codex Configuration Index
Refer to modular configuration files for deep technical alignment:
- **Sandbox & Strategy:** [.codex/config.toml](.codex/config.toml) (`workspace-write` sandbox).
- **Automated Guardrails:** [.codex/hooks/pre_tool_use_policy.py](.codex/hooks/pre_tool_use_policy.py) and [.codex/hooks/stop-validation.sh](.codex/hooks/stop-validation.sh).
- **Specialized Workflows:** [.agents/skills/review/SKILL.md](.agents/skills/review/SKILL.md) and [docs/codex/workflows/fix-issue.md](docs/codex/workflows/fix-issue.md).

---

## 🎯 Gomoku Core Domain Rules
*High-value business logic constraints that must be enforced during feature development:*
- **Board Grid Dimensions:** Fixed **15x15 grid** (coordinates `x, y` must be integers ranging from `0` to `14`).
- **Win Condition Algorithm:** A player wins when **5 continuous stones of the same color** align horizontally, vertically, or diagonally.
- **Framework-Agnostic Logic:** Game state and win-checking algorithms **must reside in [src/app/services/game_service.py](src/app/services/game_service.py)** without Django or database dependencies.

---

## 🛠️ Architecture & Coding Standards
- **Naming Conventions:** Pythonic `snake_case` for files/functions (with type hints) and `PascalCase` for classes.
- **Layer Isolation:** Django views/APIs ([`src/app/api/`](src/app/api/)) call `services` only; `services` communicate with databases via `repositories`. **Never import Django ORM Models directly into the API layer.** See [.codex/rules/api.md](.codex/rules/api.md).
- **Type Hinting:** Strictly use Python 3.14 native type hinting (e.g., `list[int]`, `dict[str, int]`).

---

## 🔒 Security & Secrets Management
Supplemented by a Pre-Tool-Use command-text hook (not a replacement for file-access controls):
- **Zero Raw SQL:** Use Django ORM or parameterized queries; raw string formatting is prohibited.
- **Credential Protection:** Never read, output, or commit `src/.env` or sensitive key/pem files. The hook blocks selected command patterns only; it is not comprehensive file-access protection. See [.codex/rules/security.md](.codex/rules/security.md).

---

## 📂 Repository Structure Key Paths
- [`src/app/`](src/app/) -- Main application source code ([`api/`](src/app/api/), [`services/`](src/app/services/), [`repositories/`](src/app/repositories/), [`models/`](src/app/models/)).
- [`src/tests/`](src/tests/) -- Application unit tests.
- [`docs/`](docs/) & [`.codex/`](.codex/) -- Documentation, rules, and configuration hooks.

---

## Environment Setup
The development environment is entirely containerized. Do not install project dependencies or run databases on the local host.

### Core Environment Variables & Multi-Worktree Isolation
Each worktree must use its own Docker Compose project, environment files, containers, network, and database volume:
- Run `bash scripts/init-worktree-env.sh` in each feature worktree before starting Docker Compose. It creates a local root `.env`, fills blank isolation settings, and copies `src/.env.example` to `src/.env` if needed.
- `COMPOSE_PROJECT_NAME` belongs in the worktree's **root `.env`**. The initializer derives it from the branch name and a stable hash of the canonical worktree path, then preserves that project name across branch renames; values in the app service's `env_file` (`src/.env`) are loaded too late to select the project.
- Keep `POSTGRES_PASSWORD` in the root `.env`. Keep Django application settings such as `DJANGO_SECRET_KEY` and `DEBUG` in `src/.env`.
- Compose supplies `DATABASE_URL` to the app and connects it to the `db` service on that worktree's private Compose network.
- Do not publish the database port to the host. The app reaches Postgres using `db:5432`; each Compose project owns a separate network and `postgres_data` volume.
- Use `bash scripts/compose.sh` for every local Compose command. It resolves the project from the current worktree's root `.env` and explicitly selects that project, so an exported `COMPOSE_PROJECT_NAME` cannot redirect commands to another stack. Never symlink `.env` files between worktrees.
- The initializer preserves existing legacy and directory-default project names to keep their database volumes attached. Before switching an existing default project, it checks for its `postgres_data` volume and requires the original project name and password or an explicit database migration.

## 🔄 Quality Gates & Workflow Boundaries
- **Testing & Formatting:** Every service function requires a corresponding unit test in [`src/tests/`](src/tests/) (e.g., `user_service_test.py`). When this worktree's app container is running, the `Stop` hook ([.codex/hooks/stop-validation.sh](.codex/hooks/stop-validation.sh)) checks formatting, lint, and tests against the container selected by this worktree's `COMPOSE_PROJECT_NAME` through `scripts/compose.sh`. If this worktree has no initialized environment or its app service is stopped, the hook skips validation.
- **Worktree-aware development:** Every new branch and Git worktree must start from `main`, never from the currently checked-out feature or task branch. Synchronize `main` with `origin/main` first. Use a dedicated worktree per parallel task, with `feature/gomoku-<task>` for product features, `infra/<task>` for development tooling or infrastructure, `fix/<task>` for bug fixes, and `docs/<task>` for documentation updates. Initialize that worktree's environment and start its own Docker Compose project before development.
- **Push validation and cleanup:** Before every push of a task branch, ensure the worktree’s isolated Docker Compose services are running and run the full Stop hook validation; push only after it passes. After a successful push, run `bash scripts/compose.sh down` in that worktree to stop and remove its containers and network while retaining its database volume. If the push fails, leave the environment running for further work. Before any subsequent push, restart the isolated services and run the full validation again. Never use `down -v` without explicit authorization.
- **Self-Correction:** If the Stop hook fails, read the terminal output, fix the code/tests within the same session, and re-run until it passes 🟢.
- **Boundaries:**
  - ✅ **Always:** Work in task-appropriate branches inside dedicated worktrees, write unit tests in [`src/tests/`](src/tests/), and use the isolated container stack for the active worktree.
  - ⚠️ **Ask first:** Database schema changes (especially when concurrent migrations may conflict), `AGENTS.md` updates, or adding dependencies to `pyproject.toml`.
  - 🚫 **Never:** Share Docker Compose project names or database volumes between worktrees, commit secrets, or push directly to `main`.
- **Git & PR Workflow:** Always branch from the synchronized `main` branch. Use `feature/gomoku-<task-name>` for product features, `infra/<task-name>` for infrastructure changes, `fix/<task-name>` for bug fixes, and `docs/<task-name>` for documentation updates; commit atomically, and open PRs using `gh` CLI following [`docs/codex/workflows/fix-issue.md`](docs/codex/workflows/fix-issue.md) before final human review.
