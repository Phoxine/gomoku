# AGENTS.md

## Project Overview
This is a web-based interactive Gomoku game built with Python 3.14 + Django + Django ORM + Postgres inside Docker containers.

## Codex Configuration Index
Refer to modular configuration files for deep technical alignment:
- **Sandbox & Strategy:** `.codex/config.toml` (`workspace-write` sandbox).
- **Automated Guardrails:** `.codex/hooks/pre_tool_use_policy.py` and `.codex/hooks/stop-validation.sh`.
- **Specialized Workflows:** `.agents/skills/review/SKILL.md` and `docs/codex/workflows/fix-issue.md`.

---

## 🎯 Gomoku Core Domain Rules
*High-value business logic constraints that must be enforced during feature development:*
- **Board Grid Dimensions:** Fixed **15x15 grid** (coordinates `x, y` must be integers ranging from `0` to `14`).
- **Win Condition Algorithm:** A player wins when **5 continuous stones of the same color** align horizontally, vertically, or diagonally.
- **Framework-Agnostic Logic:** Game state and win-checking algorithms **must reside in `src/app/services/game_service.py`** without Django or database dependencies.

---

## 🛠️ Architecture & Coding Standards
- **Naming Conventions:** Pythonic `snake_case` for files/functions (with type hints) and `PascalCase` for classes.
- **Layer Isolation:** Django views/APIs (`src/app/api/`) call `services` only; `services` communicate with databases via `repositories`. **Never import Django ORM Models directly into the API layer.** See `.codex/rules/api.md`.
- **Type Hinting:** Strictly use Python 3.14 native type hinting (e.g., `list[int]`, `dict[str, int]`).

---

## 🔒 Security & Secrets Management
Enforced via Pre-Tool-Use hooks:
- **Zero Raw SQL:** Use Django ORM or parameterized queries; raw string formatting is prohibited.
- **Credential Protection:** Never read, output, or commit `src/.env` or sensitive key/pem files. See `.codex/rules/security.md`.

---

## 📂 Repository Structure Key Paths
- `src/app/` -- Main application source code (`api/`, `services/`, `repositories/`, `models/`).
- `src/tests/` -- Application unit tests.
- `docs/` & `.codex/` -- Documentation, rules, and configuration hooks.

---

## 🔄 Quality Gates & Workflow Boundaries
- **Testing & Formatting:** Every service function requires a corresponding unit test in `src/tests/` (e.g., `user_service_test.py`). Code validation (Ruff, Pytest) runs automatically via the `Stop` hook (`.codex/hooks/stop-validation.sh`).
- **Boundaries:**
  - ✅ **Always:** Work in feature branches, write unit tests, rely on `Stop` hooks.
  - ⚠️ **Ask first:** Database schema changes, `AGENTS.md` updates, or adding dependencies to `pyproject.toml`.
  - 🚫 **Never:** Commit secrets, push directly to `main`, or bypass test failures.
- **Git & PR Workflow:** Create feature branches (`feature/gomoku-<task-name>`), commit atomically, and open PRs using `gh` CLI following `docs/codex/workflows/fix-issue.md` before final human review.
