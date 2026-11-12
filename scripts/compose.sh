#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
root_env="$repo_root/.env"

if [[ ! -f "$root_env" || -L "$root_env" ]]; then
  echo "Run 'bash scripts/init-worktree-env.sh' before starting this worktree's Docker stack." >&2
  exit 1
fi

project_name="$(bash "$repo_root/scripts/resolve-compose-project-name.sh" "$root_env")"
if [[ -z "$project_name" || ! "$project_name" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
  echo "The root .env must define a non-empty, valid COMPOSE_PROJECT_NAME. Re-run the worktree initializer." >&2
  exit 1
fi

expected_project="$(bash "$repo_root/scripts/worktree-project-name.sh")"
legacy_project="$(bash "$repo_root/scripts/worktree-project-name.sh" legacy)"
default_project="$(bash "$repo_root/scripts/worktree-project-name.sh" directory)"
if [[ "$project_name" != "$expected_project" && "$project_name" != "$legacy_project" && "$project_name" != "$default_project" ]]; then
  echo "The root .env project name does not belong to this worktree. Re-run the initializer or migrate the existing database explicitly." >&2
  exit 1
fi

exec env -u COMPOSE_PROJECT_NAME -u POSTGRES_PASSWORD docker compose \
  --project-directory "$repo_root" \
  --env-file "$root_env" \
  --project-name "$project_name" \
  -f "$repo_root/compose.yaml" \
  "$@"
