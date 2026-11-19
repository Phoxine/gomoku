# AGENTS.md

## Project Overview
This is a web-based interactive Gomoku game built with Python 3.14 + Django + Django ORM + Postgres inside Docker containers.

## Find guidance by task

- **Start development or run tests.** See [Environment setup and testing](#environment-setup-and-testing).
- **Find code or product behavior.** Use the [architecture code map](ARCHITECTURE.md#code-map) and the [documentation index](docs/index.md).
- **Change game rules.** Start with the [game service design](docs/domains/game/context-designs.md#game-service), [rules tests](src/tests/game_service_test.py), and [state transition tests](src/tests/game_state_transition_test.py).
- **Change an API or database schema.** Read the [API rules](.codex/rules/api.md) and [game API contract](docs/domains/game/apis.md). For schema work, see the [database schema](docs/domains/game/db-schemas.md) and the [migration skill](.agents/skills/migrate/SKILL.md).
- **Fix an issue or review a change.** Use the [issue fix skill](.agents/skills/fix-issue/SKILL.md) or the [review skill](.agents/skills/review/SKILL.md).
- **Deliver a pull request.** See the [delivery policy](#git-and-pull-request-workflow) and the [create-pr skill](.agents/skills/create-pr/SKILL.md).
- **Inspect Codex configuration.** See the [sandbox configuration](.codex/config.toml), [command policy hook](.codex/hooks/pre_tool_use_policy.py), and [Stop hook](.codex/hooks/stop-validation.sh).

## Environment setup and testing

The development environment is entirely containerized. Do not install project dependencies or run databases on the local host. See the [host prerequisites](docs/codex/prerequisites.md) and [development setup](README.md#development-setup) for build and startup.

Each worktree must use its own Docker Compose project and database volume. Use `bash scripts/compose.sh` from that worktree for local Compose commands. See the [worktree skill](.agents/skills/create-worktree/SKILL.md) and [isolation reference](.agents/skills/create-worktree/references/multi-session-worktrees.md).

Every service function requires a corresponding unit test in [`src/tests/`](src/tests/). Run the suite with the worktree's app container running:

```bash
bash scripts/compose.sh exec app uv run pytest
```

---

## 🤖 Subagent Orchestration Strategy

Use specialized subagents to support independent work while respecting higher-priority session instructions:
- **New or modified subagents:** Before finalizing a new or modified subagent, test its registration, actual dispatch, and role-specific behavior using the [subagent validation skill](.agents/skills/validate-subagent/SKILL.md).
- **Codebase Exploration (`explorer`):** For unfamiliar modules or cross-layer dependencies (such as API, domain, and repository interactions), delegate independent read-only exploration where useful.
- **Parallel Tests and Documentation (`test_doc_worker`):** After implementing domain logic or API endpoints, delegate unit tests in `src/tests/` and English feature documentation. Assign file targets that do not overlap with active edits.
- **Code and Architecture Review (`code_reviewer`):** Before finalizing any repository change or running push validation, delegate a read-only review covering all files changed for the task. Review the relevant application and infrastructure concerns, including correctness, security, layer isolation, framework-independent game rules, typing, performance, concurrency, CI, and container isolation. Follow the review skill's remediation and re-review loop.
- **Test Execution and Diagnostics (`test_runner`):** When isolated test execution or failure analysis can be delegated, use this role to run tests through the current worktree's Compose wrapper and report the results. Request approval when Docker access requires it.
- **Technical Research (`tech_researcher`):** When evaluating an uncertain technical approach, delegate a read-only assessment of compatibility, costs, architectural boundaries, and risks. Assign independent alternatives separately when comparison is useful.
- **Container and Hook Execution:** Keep Docker Compose lifecycle commands (such as `up` and `down`) and Stop hook execution and self-correction in the main session to prevent concurrent container races within the worktree.
- **Final Delegation Report:** When subagents are spawned, include a concise `### 🤖 Subagent Execution Summary` section in the final response, listing each subagent’s delegated scope and key outcome.

---

## 🎯 Gomoku Core Domain Rules
*High-value business logic constraints that must be enforced during feature development:*
- **Board Grid Dimensions:** Fixed **15x15 grid** (coordinates `x, y` must be integers ranging from `0` to `14`).
- **Win condition.** A player wins when **at least five consecutive stones of the same color** align horizontally, vertically, or diagonally.
- **Framework-Agnostic Logic:** Game state and win-checking algorithms **must reside in [src/app/domain/game/service/game_service.py](src/app/domain/game/service/game_service.py)** without Django or database dependencies.

---

## 🛠️ Architecture & Coding Standards
- **Naming Conventions:** Pythonic `snake_case` for files/functions (with type hints) and `PascalCase` for classes.
- **Application boundaries.** See the [architecture guide](ARCHITECTURE.md#architectural-boundaries) for dependency direction and the [API rules](.codex/rules/api.md) for DTO and ORM access requirements.
- **Type Hinting:** Strictly use Python 3.14 native type hinting (e.g., `list[int]`, `dict[str, int]`).

---

## 🔒 Security & Secrets Management
Never read, print, or commit credentials. Follow the [security rules](.codex/rules/security.md) for protected files, input validation, SQL, and logging. The Pre-Tool-Use hook checks selected command patterns. File-access restrictions apply independently.

---

## Feature Documentation

For every feature, create or update English documentation alongside the implementation, following [the feature documentation skill](.agents/skills/document-feature/SKILL.md).

---

## 🔄 Quality Gates & Workflow Boundaries
- **Skill changes:** When creating or modifying a project skill, use the [validate-skill workflow](.agents/skills/validate-skill/SKILL.md) to assess its scope, overlap, and validation. When skill-creator is available, also follow its guidance, including format validation.
- **Uncommitted prerequisites:** If a task depends on changes that exist only as uncommitted work, ask whether to continue in the existing worktree or transfer the required changes to a new worktree before creating it. Preserve unrelated changes.
- **Worktree-aware development:** For repository changes, including sequential tasks, use a dedicated task branch and worktree by default. Use an existing target only when the user explicitly selects it; inspect it first and preserve unrelated changes. Read-only requests do not require a new worktree. Follow the [create-worktree skill](.agents/skills/create-worktree/SKILL.md) for base selection, branch naming, and isolated environment setup.
- **Push validation and cleanup.** Before every task-branch push, including push-only requests, run the full [Stop hook validation](.agents/skills/create-pr/SKILL.md#3-validate-before-pushing) against the worktree's running isolated Compose stack. Push only after formatting, lint, and tests have run and passed. Follow the [post-push cleanup procedure](.agents/skills/create-pr/SKILL.md#4-push-the-branch) and retain the database volume.
- **Self-Correction:** If the Stop hook fails, read the terminal output, fix the code/tests within the same session, and re-run until it passes 🟢.
- **Boundaries:**
  - ⚠️ **Ask first.** Obtain explicit approval before changing the database schema, deleting a database volume, updating `AGENTS.md`, or adding dependencies to `pyproject.toml`.
  - 🚫 **Never:** Share Docker Compose project names or database volumes between worktrees, commit secrets, or push directly to `main`.

## Git and Pull Request Workflow

- When code or version-controlled documentation changes are complete, follow [create-pr](.agents/skills/create-pr/SKILL.md) to commit and push the task branch, then open or update its PR. Respect explicit limits such as local-only or push-only delivery. Read-only tasks and local-only working notes require no PR.
- Merge a PR or remove a worktree only with explicit authorization.
