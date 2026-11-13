---
name: migrate
description: Safely plan, generate, apply, and verify Django database schema migrations in an isolated worktree environment. Use before modifying database models, generating migration files, applying migrations, or handling data backfills.
---

# Database Schema Migration Workflow

Follow this workflow whenever a task changes database schema, adds or edits Django migrations, applies migrations to a persistent worktree database, or backfills data.

## 1. Confirm scope and get approval

- Confirm the current worktree, branch, and task scope. Use only the current worktree's Docker Compose project through `bash scripts/compose.sh`.
- Before modifying Django models, generating or editing migration files, or performing a data backfill, obtain the user's explicit approval as required by `AGENTS.md`. Approval to change models does not by itself authorize applying a migration to a persistent database; confirm the target environment if that is not clear.
- Before asking, summarize the proposed schema changes, affected tables and columns, defaults, nullability, indexes and constraints, data backfill, compatibility with the previous application version, and any destructive or potentially locking operations.
- Treat approval as limited to the described changes and target. Ask again before expanding the scope or applying changes to a different database.
- Do not apply migrations to a production database under this workflow. Production deployment requires a separate, explicitly authorized deployment procedure.

## 2. Check worktree isolation and migration conflicts

- Never share database volumes between worktrees. Never run `down -v` unless the user explicitly authorizes deleting the database volume.
- Fetch the latest `main` and inspect migration changes since the branch base before generating a migration:

  ```bash
  git fetch origin main
  git diff origin/main -- 'src/app/**/migrations/*.py'
  ```

- Start this worktree's own services and confirm the app is running before using Django management commands:

  ```bash
  bash scripts/compose.sh up --build -d
  bash scripts/compose.sh ps --status running --services
  ```

  The output must include `app`. Resolve startup problems before running migration commands. Do not use a local-host Python environment or database.

- Check the affected app's migration dependencies and graph for duplicate migration names or numbering and multiple leaf migrations. Before writing a file, use `makemigrations` with `--dry-run` to detect graph conflicts without creating a migration:

  ```bash
  bash scripts/compose.sh exec app uv run python manage.py makemigrations <app_label> --name <descriptive_name> --dry-run
  ```

  If Django reports conflicts or concurrent migrations are present, stop and coordinate before creating or merging migrations.

## 3. Generate and inspect migrations

- Generate a migration inside the isolated app container, scoped to the affected app and named descriptively:

  ```bash
  bash scripts/compose.sh exec app uv run python manage.py makemigrations <app_label> --name <descriptive_name>
  ```

- Inspect every generated or edited migration before applying it. Check operation order, dependencies, table and column names, nullability, defaults, constraints, indexes, and reverse behavior. Review generated SQL when useful:

  ```bash
  bash scripts/compose.sh exec app uv run python manage.py sqlmigrate <app_label> <migration_name>
  ```

- Prefer backward-compatible expand-and-contract changes when old and new application versions may overlap. Assess table size, database behavior, locks, and deployment order; adding a nullable field or default does not by itself guarantee a zero-downtime change.
- Keep large data backfills separate from schema changes. Make backfills safe to retry and suitable for the table size; use historical models in data migrations rather than importing current models.
- Provide a meaningful `reverse_code` for reversible `RunPython` operations. If an operation cannot be reversed safely, state that explicitly in the migration and deployment notes; do not claim reversibility with a no-op reverse function.
- After generating migrations, check that model state and migration state agree:

  ```bash
  bash scripts/compose.sh exec app uv run python manage.py makemigrations --check --dry-run
  ```

## 4. Apply, verify, and test rollback

- Apply only the approved migration to this worktree's isolated database, then inspect the migration state:

  ```bash
  bash scripts/compose.sh exec app uv run python manage.py migrate <app_label> <target_migration> --plan
  bash scripts/compose.sh exec app uv run python manage.py migrate <app_label> <target_migration>
  bash scripts/compose.sh exec app uv run python manage.py showmigrations
  ```

- Review the exact plan before applying it, including any apply and unapply operations. The app-scoped command applies the requested target and its dependencies and may unapply later migrations. If the work requires applying every pending migration, first verify the full plan is within the user's approval; do not use an unscoped `migrate` command to apply unreviewed changes.
- Check whether the plan will unapply any already-applied migrations. If it will, or if an operation can delete or irreversibly alter data, stop and obtain explicit approval for that rollback and its data impact before proceeding.
- Test backward and forward migration on disposable test data when feasible. Confirm the target migration and app label before rolling back; never run rollback against a shared or production database as part of local validation. Document any data that cannot be restored.
- Add or update tests for migration behavior and affected application behavior, especially for data migrations. Update the applicable `docs/domains/<domain>/db-schemas.md` following the feature documentation workflow.
- Before treating the Stop hook as passed, confirm `app` is running with `bash scripts/compose.sh ps --status running --services`, then run:

  ```bash
  bash .codex/hooks/stop-validation.sh
  ```

  If the hook prints `Skipping final validation`, validation did not run even if it exits successfully. Resolve the Compose issue, confirm `app` is running, and rerun the hook until formatting, lint, and tests complete without being skipped.

## 5. Report migration and rollback notes

- Include a **Migration & Rollback Notes** subsection under the PR template's **Screenshots / Notes (Optional)** section and in the final summary whenever the change includes migrations. Cover:
  - Migration file names and app labels.
  - Backward compatibility with the previous application version and deployment ordering concerns.
  - Data backfill behavior and any destructive or irreversible effects.
  - Step-by-step rollback target and command, plus data caveats. Use `bash scripts/compose.sh exec app uv run python manage.py migrate <app_label> <target_migration>` for local worktree instructions; do not imply this is a production runbook.
- If there is no migration or backfill, state that in the summary when relevant.
