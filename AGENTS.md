# AGENTS.md

Gomoku is a browser-based game built with Python 3.14, Django, and PostgreSQL in Docker.

## Find project knowledge

- Start at the [documentation index](docs/index.md) for design documents, product specifications, and setup. Use [ARCHITECTURE.md](ARCHITECTURE.md) to locate code and trace the API, service, repository, and database boundaries.
- Go to the [game domain design](docs/domains/game/context-designs.md#game-service) for game rules and state transitions. Check the [rules tests](src/tests/game_service_test.py) and [state transition tests](src/tests/game_state_transition_test.py) for executable examples.
- Use the [development setup](README.md#development-setup) and [Codex host prerequisites](docs/codex/prerequisites.md) for build and environment commands. See the [Codex configuration](.codex/config.toml), [command rules](.codex/rules/default.rules), and [command-text hook](.codex/hooks/pre_tool_use_policy.py) for tooling behavior.

## Choose the workflow

| Task | Instructions |
| --- | --- |
| Start repository changes or troubleshoot an isolated environment | [create-worktree](.agents/skills/create-worktree/SKILL.md) and its [isolation reference](.agents/skills/create-worktree/references/multi-session-worktrees.md) |
| Investigate and fix a reported issue | [fix-issue](.agents/skills/fix-issue/SKILL.md) |
| Change a feature | Update its English documentation alongside the implementation. [document-feature](.agents/skills/document-feature/SKILL.md) |
| Change the database schema after approval | [migrate](.agents/skills/migrate/SKILL.md) |
| Review and deliver a completed change | [review](.agents/skills/review/SKILL.md) and [create-pr](.agents/skills/create-pr/SKILL.md) |
| Change a skill or a subagent | Use [validate-skill](.agents/skills/validate-skill/SKILL.md) for skill scope, overlap, and validation. Also follow skill-creator and run its format validator when available. Use [validate-subagent](.agents/skills/validate-subagent/SKILL.md) to verify registration, actual dispatch, and role-specific behavior before finalizing a subagent. |

## Worktree, validation, and delivery

- Use a dedicated task branch and worktree for repository changes, including sequential tasks. Reuse an existing target only when the user explicitly selects it. Inspect it and preserve unrelated changes. If the task depends on uncommitted changes, ask whether to continue in the existing worktree or transfer them before creating a worktree. Read-only tasks can use the current worktree.
- Run project dependencies and databases in Docker. Give each worktree its own Compose project and database volume.
- Every service function needs a corresponding unit test in [`src/tests/`](src/tests/). The [Stop hook](.codex/hooks/stop-validation.sh) runs formatting, lint, and tests in this worktree's running app container. It skips when the environment is uninitialized or the app is stopped.
- When code or version-controlled documentation changes are complete, use [create-pr](.agents/skills/create-pr/SKILL.md) to commit and push the task branch and open or update its PR. Respect requests to keep changes local or otherwise limit delivery. Local-only working notes and read-only tasks require no PR.
- Before any task-branch push, including a push without a PR or a repeat push, follow [push validation](.agents/skills/create-pr/SKILL.md#3-validate-before-pushing). Start the isolated services and run the full Stop hook. If it fails or skips, resolve the issue and rerun before pushing. Follow the [post-push cleanup](.agents/skills/create-pr/SKILL.md#4-push-the-branch) on success and retain the database volume. Keep the environment running if the push fails.

## Architecture and security constraints

- The board is 15×15 with integer coordinates from 0 to 14. Five or more consecutive stones of one color win horizontally, vertically, or diagonally. Keep game rules and state transitions in `src/app/domain/game/service/game_service.py`, independent of Django and the database. [Game domain design](docs/domains/game/context-designs.md)
- Route application operations and data access in `src/app/api/` through domain services. Services use domain repositories for persistence. Keep ORM model imports out of the API layer, use request and response DTOs, and avoid returning ORM models. [API rules](.codex/rules/api.md)
- Use `snake_case` for Python files and functions, `PascalCase` for classes, and native Python 3.14 type hints.
- Use Django ORM or parameterized queries. Prohibit raw SQL string formatting. Never read, print, or commit `.env`, `*.pem`, `*.key`, or credential files. The command-text hook checks selected patterns. [Security rules](.codex/rules/security.md)
- Obtain explicit authorization before changing the schema, editing `AGENTS.md`, adding dependencies to `pyproject.toml`, deleting a database volume, merging a PR, or removing a worktree. Never push directly to `main` or share Compose project names or database volumes.

## Delegate independent work

- **`explorer`** investigates unfamiliar modules or cross-layer dependencies read-only when useful. **`tech_researcher`** evaluates uncertain approaches, including compatibility, costs, boundaries, and risks. Compare independent alternatives separately when useful.
- **`test_doc_worker`** adds unit tests and English documentation after changes to domain logic or API endpoints. Assign files that are outside the main session's active edits.
- **`code_reviewer`** reviews every changed file read-only before finalizing any repository change or running push validation. Cover relevant correctness, security, architecture, framework-independent game rules, typing, performance, concurrency, CI, and container isolation. Follow the [review and re-review loop](.agents/skills/review/SKILL.md#remediation-loop).
- **`test_runner`** runs isolated tests or diagnoses failures through the current worktree's Compose wrapper where delegation is useful. Request Docker approval when required.
- Keep Compose lifecycle operations and Stop hook execution and remediation in the main session. When subagents run, include their scopes and outcomes in a `### 🤖 Subagent Execution Summary` section in the final response.
