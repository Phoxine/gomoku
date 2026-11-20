# Documentation Audit

Use this checklist when reviewing the knowledge base. Start from [AGENTS.md](../AGENTS.md), the [architecture guide](../ARCHITECTURE.md), and the [documentation index](index.md). Cover the [design index](design-docs/index.md) and the [product index](product-specs/index.md), including every page they list.

## Checklist

- [ ] **Record the baseline.** Note the date, the commit reviewed (`git rev-parse HEAD`), and any in-scope working-tree changes. Use `git ls-files '*.md'` to inventory versioned Markdown.
- [ ] **Run the documentation checker.** From the repository root, run `bash scripts/check-docs.sh`. Stage new Markdown paths that should be included. Record the result. The command validates repository-relative links, index coverage, and design verification status, then runs the checker regression tests. It exits with a nonzero status if either fails.
- [ ] **Find the owning page.** For each area, identify where the authoritative description belongs and follow links from the entry points. Check repeated descriptions for disagreement and link to the owning page when a summary suffices.
- [ ] **Check for stale or unused pages.** Look for superseded instructions, outdated verification evidence, and pages without a path from the relevant index. Search for references by filename and confirm the page's purpose before proposing removal or archiving.
- [ ] **Compare claims with implementation.** Follow the design index's evidence links. For each design and product page, compare the documented behavior with the relevant source, migrations, or tests. Record what you actually checked and which checks you ran. If the evidence is incomplete, record what remains to verify and update the design status as appropriate.
- [ ] **Record and close findings.** Add a dated record below with the scope, checker result, and one row per area. Record the owning page, evidence, result, and follow-up. Resolve findings in the audit change or link to a versioned follow-up with a concrete next step. Rerun affected checks after corrections.

The command requires Git and Docker. It works from the main checkout and linked worktrees without starting PostgreSQL or installing Python dependencies on the host. Git supplies the tracked path listing, and the container reads current working-tree content through a read-only mount.

Reuse this table for each run.

| Area and owning page | Evidence checked | Result | Follow-up |
| --- | --- | --- | --- |
| Page and claim reviewed | Navigation, code, migration, test, or command output | Pass, finding, or verification pending | Fix link, versioned follow-up, or none |

Consider scheduled audits and automated correction PRs after another run confirms the checklist is repeatable.

## Audit record

### 2026-11-20

Reviewed baseline `7d93e13` and the documentation changes in the audit PR. Scope included navigation from AGENTS.md, architecture, and all pages in the design and product indexes. The documentation checker passed after staging the audit page.

Compared the design pages and their linked source and tests with the verification baseline `a9374b9`. The API clarification about middleware running before method handling matched the API integration test. The schema edits about PostgreSQL types, Django-managed defaults, and the last mover matched the model, migration, and state transition. The existing design verification still applies to those edits.

| Area and owning page | Evidence checked | Result | Follow-up |
| --- | --- | --- | --- |
| Navigation and ownership in the [documentation index](index.md), [architecture guide](../ARCHITECTURE.md), and [core beliefs](design-docs/core-beliefs.md) | Walked from AGENTS.md to both indexes and their pages, checked the tracked Markdown inventory for in-scope pages, and compared layer responsibilities with the [API rules](../.codex/rules/api.md). | All in-scope pages have a navigation path and a current purpose. Architecture and principles point to the detailed contracts and rules. | None |
| Rules, state transitions, and persistence coordination in the [game domain design](domains/game/context-designs.md) | Read the [rules service](../src/app/domain/game/service/game_service.py), [state types](../src/app/domain/game/state.py), [transition tests](../src/tests/game_state_transition_test.py), [application service](../src/app/domain/game/service/application_service.py), and [repository](../src/app/domain/game/repository/game_repository.py). | Board size, win-before-draw order, turn handling, state copying, transaction scope, and row locking matched the design. | None |
| Routes and wire behavior in the [game API contract](domains/game/apis.md) | Compared the [routes](../src/config/urls.py), [handlers](../src/app/api/game_views.py), [DTOs](../src/app/api/game_dto.py), [API integration test](../src/tests/game_api_test.py), and [Django's CSRF guidance](https://docs.djangoproject.com/en/6.1/howto/csrf/). | Routes, fields, and error codes matched. The CSRF guidance overstated the header requirement for form POSTs. | Corrected the [API contract](domains/game/apis.md) to describe the form field and header. |
| Storage in the [database schema](domains/game/db-schemas.md) | Compared the [model](../src/app/domain/game/model/game.py), [initial migration](../src/app/domain/game/migrations/0001_initial.py), and [board constraint](../src/app/domain/game/model/board_constraint.py). | The documented fields, defaults, nullability, primary key, and check constraints matched the model and migration. | None |
| Player-visible behavior in the [local two-player specification](product-specs/local-two-player-game.md) | Read the [page template](../src/app/template/game.html), [browser code](../src/app/static/game/game.js), [browser interaction tests](../scripts/tests/game_web_interactions_test.js), and game rules above. | Creating, restoring, and loading games by ID, turns, and win or draw behavior matched the specification. The routes and browser code matched the documented access model and current scope. | None |
