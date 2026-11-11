# AGENTS.md

## Project Overview
This is a web-based interactive Gomoku game built with Python3.14 + Django + Django ORM + Postgres. It is developed and run entirely inside Docker containers.

## Naming Conventions
- File name: snake_case (ex: user_service.py)
- Function name: snake_case (type hint needed, including parameter & return type)
- Class name: PascalCase (ex: UserService)
- Environment variable: UPPER_SNAKE_CASE (ex: DATABASE_URL)

## Environment Setup
The development environment is entirely containerized. Do not install dependencies or run databases on the local host.

### 🔑 Core Environment Variables
Agent must ensure `src/.env` is created from `src/.env.example` before starting containers. Key variables include:
- `DATABASE_URL`: Django ORM connection string targeting the `db` service (e.g., `postgresql+psycopg://postgres:password@db:5432/gomoku`).
- `DJANGO_SECRET_KEY`: Secure key for Django application.
- `DEBUG`: Set to `True` for development logs.

### 🛠️ Container Lifecycle
Always interact with the environment using Docker Compose:
- **Initialize & Start:** `docker compose up --build -d`
- **Stop Environment:** `docker compose down`
- **View Logs:** `docker compose logs -f`

## Commands
All linting, formatting, migrations, and testing must be executed inside the running `app` container:

- **Lint with ruff:** `docker compose exec app uvx ruff check --fix src/app/`
- **Format with ruff:** `docker compose exec app uvx ruff format src/app/`
- **Run tests:** `docker compose exec app uv run pytest`
- **Database migrations:** `docker compose exec app uv run python src/app/manage.py migrate`

## Repository Structure
UV workspace repo. Key paths:
 - src/app/ -- all components of the application
     - models/ -- Django ORM models (User, Game, Move, History)
     - repositories/ -- database access layer (user_repository, game_repository, move_repository)
     - services/ -- main business logic (user_service, game_service, move_service)
     - api/ -- Django API endpoints (user_api, game_api, move_api)
     - template/ -- Django templates for frontend
 - src/tests/ -- service unit tests, named after the service file
 - src/.env -- local environment configuration (never commit)
 - docs/ -- documentation files
 - docker/ -- Dockerfile for containerization

## Testing Requirements
- Every service function must have unit tests.
- Put tests in `src/tests/` with the same name as the service file (ex: user_service_test.py).
- Run tests via Docker using `docker compose exec app uv run pytest`.

## Security Requirements
- **SQL Injection Prevention:** Always use Django's ORM or parameterized queries. Never use raw string formatting for SQL execution.
- **Input Validation:** Validate board coordinates (e.g., `x, y` must be integers between 0 and 14) at the API layer before passing to services.
- **Secrets Management:** Never commit `.env` or hardcode credentials in any files.

## Coding Standards
- **Type Hinting:** Strictly use Python 3.14 native type hinting (e.g., `list[int]` instead of `List[int]`).
- **Architecture Isolation:** Django views/APIs must only call `services`. `services` must talk to databases only via `repositories`. Never import models directly in `api/`.
- **Gomoku Logic:** Game state calculations (win checking, valid moves) must reside entirely in `src/app/services/game_service.py` and remain framework-agnostic.

## Boundaries
- ✅ **Always:** Write application code to `src/app/` and tests to `src/tests/`, run tests inside Docker before commits, follow naming conventions.
- ⚠️ **Ask first:** Database schema changes, `AGENTS.md` changes, adding dependencies to `pyproject.toml`.
- 🚫 **Never:** Commit secrets or API keys.

## Docker Deployment and Development Guidelines
- **Base image:** Use `python:3.14-slim`.
- **Dependency installation:** Copy `pyproject.toml` and `uv.lock` and use `uv` to install dependencies inside the Dockerfile, caching this layer before copying `src/app/` source code.
- **Services:**
  - `app`: The main Django application container.
  - `db`: A PostgreSQL database container with a persistent volume configured.

## Git and Pull Request Workflow
Agent has full permission to manage branches and create PRs using the host's `git` and `gh` CLI. Follow this workflow:

1. **Checkout Branch:** Always create a new branch from `main`. Do not work directly on `main`.
   - Pattern: `feature/gomoku-<task-name>`
   - Command: `git checkout -b feature/gomoku-core-logic`
2. **Commit Changes:** Group code modifications into logical, atomic commits.
   - Command: `git commit -am "feat: implement win-checking algorithm"`
3. **Push & Create PR:** Push to remote and use GitHub CLI (`gh`) to open a PR.
   - Command: `git push origin feature/gomoku-core-logic`
   - Command: `gh pr create --title "feat: Gomoku Core Logic" --body "Implemented game service logic and verified via pytest inside docker." --base main`
