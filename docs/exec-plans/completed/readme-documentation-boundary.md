# README and development documentation

## Goal and scope

Keep the root project overview useful to people discovering or trying Gomoku. Give contributors and agents a development guide for setup, local server configuration, maintenance, and CI. Route agent instructions, skill references, and repository documents to the pages that own those procedures.

The baseline at `6e5abe8` had eight direct links to the root overview across seven files. The [agent instructions](../../../AGENTS.md), [architecture guide](../../../ARCHITECTURE.md), [documentation index](../../index.md), and [schema probe](../../domains/game/db-schemas.md) used the development setup section. The [Compose troubleshooting reference](../../../.agents/skills/create-worktree/references/compose-troubleshooting.md) used the local play section. The [knowledge base maintenance plan](knowledge-base-maintenance.md) linked twice to the Python image update policy and also mentioned its location in prose. The [dependency and security update triage plan](../active/dependency-and-security-update-triage.md), added by [PR #73](https://github.com/Phoxine/gomoku/pull/73), added a third link to the same policy. The other two plans from that PR had no direct links to the root overview.

## README outline

- **Gomoku.** Open with a short description of the 15×15 game, two players sharing a device, and the win condition. Link to the local two-player specification for supported behavior and limitations.
- **Quick start.** List Docker and Docker Compose as prerequisites, run `bash scripts/start-local-server.sh` from the repository root, and open the URL printed by the script. Show `bash scripts/compose.sh down` to stop the server and keep saved games.
- **Documentation.** Link to the documentation index and development guide. Send readers to the guide for custom ports, contributor setup, tests, and maintenance.

Lichess pairs a short run command with linked development setup. Pygame follows its setup instructions with a runnable example. FastAPI tells readers what to open in the browser after running its example. For Gomoku, use those patterns to give readers a clear path from the project description to a playable board and then to deeper documentation. [Lichess](https://github.com/lichess-org/lila#installation) · [Pygame](https://github.com/pygame/pygame#installation) · [FastAPI](https://github.com/fastapi/fastapi#check-it)

## Milestones

1. Add `docs/development.md` and link it from the documentation index. Move the detailed environment setup, Django management commands, manual local web setup, Python image pin policy, and PR coverage instructions there. Rewrite the root overview using the outline above.
2. Update the seven sources in the inventory. In the PR #73 triage plan, replace the Python image policy link with `../../development.md#python-container-image-updates`. Preserve the historical evidence in the completed maintenance plan and point its policy links to the same section. Update the [documentation audit](../../documentation-audit.md) to check that workflow references lead to the relevant owning page.
3. From an isolated checkout, follow the quick start to a playable board and verify that stopping and restarting retains a test game. Verify the new routes from the root overview, agent instructions, skill reference, architecture guide, documentation index, and triage plan. For the Compose port-conflict path, confirm that the destination explains how to choose a distinct `APP_PORT` and that the reference still preserves the worktree and authorization boundaries.

## Acceptance and pull requests

- **Planning change.** Keep this plan in the active directory for review. The worktree diff should contain only this plan. Run the documentation checker from the worktree root after registering the new path in Git.
- **Implementation PR.** Land the guide, overview, and reference updates together so every replacement link resolves on merge. From the worktree root, run `git grep -niE 'README[.]md'` and expect no remaining references to the root overview in agent instructions, skills, or internal documentation. Run `bash scripts/check-docs.sh` after registering new Markdown paths and complete the [isolated pre-push checks](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing).

## Recovery

If the documentation checker reports a broken path or heading, inspect the target and the relative path from the referring file, then rerun the checker. After rebasing, repeat the reference inventory to catch links introduced by other branches.

## Progress and decisions

- [x] 2026-11-24. Rechecked the inventory after PR #73 merged and reviewed public README examples to define the Gomoku outline.
- [x] 2026-11-24. Reviewed and merged the plan in [PR #85](https://github.com/Phoxine/gomoku/pull/85).
- [x] 2026-11-24. Moved the procedures, redirected the references, and verified the quick start.

## Outcomes and retrospective

- Redirected all eight links across the seven inventoried files to the [development guide](../../development.md). The reference scan returned no matches. The Compose troubleshooting reference leads to the custom port instructions and retains its worktree and authorization guidance.
- Ran the quick start in an isolated checkout and used headless Chrome to create a game and place a stone. Stopped the stack with the documented command and restarted it. A fresh browser profile loaded the same game by ID and showed the saved stone and next turn.
- The Markdown checker and its 28 regression tests passed. The Stop hook completed Ruff formatting and lint checks and all 235 pytest tests.

The audit checklist now asks reviewers to check where agent, skill, and internal documentation links lead. Repeat the reference scan when moving a procedure or policy.
