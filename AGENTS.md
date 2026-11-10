# AGENTS.md

## Project Overview
This is a web-based interactive Gomoku game built with Python3.14 + Django + Postgres + SqlAlchemy.

## Naming Conventions
- File name：snake_case（ex：user_service.py）
- Function name：snake_case (type hint needed, including parameter & return type)
- Class name：PascalCase (ex：UserService)
- Environment variable：UPPER_SNAKE_CASE (ex：DATABASE_URL)

## Environment Setup


## Commands
 - Lint with ruff: `uvx ruff check --fix app/`
 - Format with ruff: `uvx ruff format app/`
 - Run tests: `uv run pytest`


## Repository Structure
UV workspace repo. Key paths:
 - app/ -- all components of the application
     - models/ -- SQlAlchemy models(User, Game, Move, History)
     - repositories/ -- database access layer (user_repository, game_repository, move_repository)
     - services/ -- main business logic (user_service, game_service, move_service)
     - api/ -- Django REST Framework API endpoints (user_api, game_api, move_api)
     - template/ -- Django templates for frontend
     - tests/ -- unit tests for services
 - docs/ -- documentation files

## Testing Requirements
- every service function must have unit tests
- put tests in `app/tests/` with the same name as the service file (ex：user_service_test.py)
- run tests using `uv run pytest`

## Security Requirements

## Coding Standards

## Boundaries
- ✅ **Always:** Write to `app/` and `app/tests/`, run tests before commits, follow naming conventions
- ⚠️ **Ask first:** Database schema changes, adding dependencies
- 🚫 **Never:** Commit secrets or API keys

## Docker Deployment and Development Guidelines

This project uses Docker and Docker Compose for container management.

### 📁 Related Files
- `Dockerfile`: Builds the application image (located in the repository root).
- `docker-compose.yml`: Defines the local development environment and multi-container setup.

### ⚙️ Dockerfile Guidelines
- Base image: Use `python:3.14-slim` (adjust this to match the project's language).
- Dependency installation: Copy `requirements.txt` or `package.json` and install dependencies before copying the source code to take advantage of Docker's build cache.

### 🛠️ Docker Compose Services
- **app**: The main application container, built with `build: .`.
- **db** (optional): A PostgreSQL database container with a persistent volume configured.

### 🚀 Common Commands
Use the following commands when testing or updating the containers:
```bash
# Build and start all services
docker compose up --build -d

# View container logs
docker compose logs -f

# Stop and remove containers
docker compose down
```
