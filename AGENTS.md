# AGENTS.md

## Project Overview
This is a web-based interactive Gomoku game built with Python 3.14 + Django + Django ORM + Postgres inside Docker containers.

## Codex Configuration Index
Refer to modular configuration files for deep technical alignment:
- **Sandbox & Strategy:** [.codex/config.toml](.codex/config.toml) (`workspace-write` sandbox).
- **Automated Guardrails:** [.codex/hooks/pre_tool_use_policy.py](.codex/hooks/pre_tool_use_policy.py) and [.codex/hooks/stop-validation.sh](.codex/hooks/stop-validation.sh).
- **Skills:** [.agents/skills/create-pr/SKILL.md](.agents/skills/create-pr/SKILL.md), [.agents/skills/create-worktree/SKILL.md](.agents/skills/create-worktree/SKILL.md), and [.agents/skills/review/SKILL.md](.agents/skills/review/SKILL.md).
- **Architecture & Security Rules:** [.codex/rules/api.md](.codex/rules/api.md) and [.codex/rules/security.md](.codex/rules/security.md).
- **Workflows:** [feature documentation](docs/codex/workflows/feature-documentation.md), [issue fixes](docs/codex/workflows/fix-issue.md), [multi-session worktrees](docs/codex/workflows/multi-session-worktrees.md), and [subagent validation](docs/codex/workflows/subagent-validation.md).
- **Environment Prerequisites:** [docs/codex/prerequisites.md](docs/codex/prerequisites.md).

---

## 🤖 Subagent Orchestration Strategy

Use specialized subagents to support independent work while respecting higher-priority session instructions:
- **New or modified subagents:** Before finalizing a new or modified subagent, test its registration, actual dispatch, and role-specific behavior using the [subagent validation workflow](docs/codex/workflows/subagent-validation.md).
- **Codebase Exploration (`explorer`):** For unfamiliar modules or cross-layer dependencies (such as API, domain, and repository interactions), delegate independent read-only exploration where useful.
- **Parallel Tests and Documentation (`test_doc_worker`):** After implementing domain logic or API endpoints, delegate unit tests in `src/tests/` and English feature documentation. Assign file targets that do not overlap with active edits.
- **Code and Architecture Review (`code_reviewer`):** Before finalizing a feature or running push validation, delegate a read-only review of correctness, security, layer isolation, framework-independent game rules, typing, performance, and concurrency.
- **Test Execution and Diagnostics (`test_runner`):** When isolated test execution or failure analysis can be delegated, use this role to run tests through the current worktree's Compose wrapper and report the results. Request approval when Docker access requires it.
- **Technical Research (`tech_researcher`):** When evaluating an uncertain technical approach, delegate a read-only assessment of compatibility, costs, architectural boundaries, and risks. Assign independent alternatives separately when comparison is useful.
- **Container and Hook Execution:** Keep Docker Compose lifecycle commands (such as `up` and `down`) and Stop hook execution and self-correction in the main session to prevent concurrent container races within the worktree.
- **Final Delegation Report:** When subagents are spawned, include a concise `### 🤖 Subagent Execution Summary` section in the final response, listing each subagent’s delegated scope and key outcome.

---

## 🎯 Gomoku Core Domain Rules
*High-value business logic constraints that must be enforced during feature development:*
- **Board Grid Dimensions:** Fixed **15x15 grid** (coordinates `x, y` must be integers ranging from `0` to `14`).
- **Win Condition Algorithm:** A player wins when **5 continuous stones of the same color** align horizontally, vertically, or diagonally.
- **Framework-Agnostic Logic:** Game state and win-checking algorithms **must reside in [src/app/domain/game/service/game_service.py](src/app/domain/game/service/game_service.py)** without Django or database dependencies.

---

## 🛠️ Architecture & Coding Standards
- **Naming Conventions:** Pythonic `snake_case` for files/functions (with type hints) and `PascalCase` for classes.
- **Layer Isolation:** Django views/APIs ([`src/app/api/`](src/app/api/)) call domain services only; domain services communicate with databases via domain repositories. **Never import Django ORM Models directly into the API layer.** See [.codex/rules/api.md](.codex/rules/api.md).
- **DTOs:** Enforce DTO usage for API requests and responses; never return ORM models directly (see [.codex/rules/api.md](.codex/rules/api.md)).
- **Type Hinting:** Strictly use Python 3.14 native type hinting (e.g., `list[int]`, `dict[str, int]`).

---

## 🔒 Security & Secrets Management
Supplemented by a Pre-Tool-Use command-text hook (not a replacement for file-access controls):
- **Zero Raw SQL:** Use Django ORM or parameterized queries; raw string formatting is prohibited.
- **Credential Protection:** Never read, output, or commit any `.env`, `*.pem`, `*.key`, or credential files. The hook blocks selected command patterns only; it is not comprehensive file-access protection. See [.codex/rules/security.md](.codex/rules/security.md).

---

## 📂 Repository Structure Key Paths
- [`src/app/`](src/app/) -- Main application source code: `api/` and `template/` sit directly under `app/`; domain code belongs under [`domain/`](src/app/domain/), organized by domain (for example, `domain/game/service/`, `domain/game/model/`, and `domain/game/repository/`). Tests remain under [`src/tests/`](src/tests/).
- [`src/tests/`](src/tests/) -- Application unit tests.
- [`docs/`](docs/) & [`.codex/`](.codex/) -- Documentation, rules, and configuration hooks.

---

## Feature Documentation

For every feature, create or update English documentation alongside the implementation, following [the feature documentation workflow](docs/codex/workflows/feature-documentation.md).

---

## Environment Setup
The development environment is entirely containerized. Do not install project dependencies or run databases on the local host.

### Core Environment Variables & Multi-Worktree Isolation
Each worktree must use its own Docker Compose project and isolated environment. Follow the [multi-session worktree workflow](docs/codex/workflows/multi-session-worktrees.md) for initialization, environment variables, database isolation, and cleanup.

## 🔄 Quality Gates & Workflow Boundaries
- **Testing & Formatting:** Every service function requires a corresponding unit test in [`src/tests/`](src/tests/) (e.g., `user_service_test.py`). When this worktree's app container is running, the `Stop` hook ([.codex/hooks/stop-validation.sh](.codex/hooks/stop-validation.sh)) checks formatting, lint, and tests against the container selected by this worktree's `COMPOSE_PROJECT_NAME` through `scripts/compose.sh`. If this worktree has no initialized environment or its app service is stopped, the hook skips validation.
- **Worktree-aware development:** Every new branch and Git worktree must start from `main`, never from the currently checked-out feature or task branch. Synchronize `main` with `origin/main` first. Use a dedicated worktree per parallel task, with `feature/gomoku-<task>` for product features, `infra/<task>` for development tooling or infrastructure, `fix/<task>` for bug fixes, `docs/<task>` for documentation updates, and `refactor/<task>` for refactoring without functional changes. Initialize that worktree's environment and start its own Docker Compose project before development.
- **Push validation and cleanup:** Before every push of a task branch, ensure the worktree’s isolated Docker Compose services are running and run the full Stop hook validation; push only after it passes. After a successful push, run `bash scripts/compose.sh down` in that worktree to stop and remove its containers and network while retaining its database volume. If the push fails, leave the environment running for further work. Before any subsequent push, restart the isolated services and run the full validation again. Never use `down -v` without explicit authorization.
- **Self-Correction:** If the Stop hook fails, read the terminal output, fix the code/tests within the same session, and re-run until it passes 🟢.
- **Boundaries:**
  - ✅ **Always:** Work in task-appropriate branches inside dedicated worktrees, write unit tests in [`src/tests/`](src/tests/), and use the isolated container stack for the active worktree.
  - ⚠️ **Ask first:** Database schema changes (especially when concurrent migrations may conflict), `AGENTS.md` updates, or adding dependencies to `pyproject.toml`.
  - 🚫 **Never:** Share Docker Compose project names or database volumes between worktrees, commit secrets, or push directly to `main`.
## Git & Pull Request Workflow
- When creating or submitting a PR, follow the `create-pr` skill in [`.agents/skills/create-pr/SKILL.md`](.agents/skills/create-pr/SKILL.md).
