#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
env_file="${1:-$repo_root/.env}"
probe_file="$repo_root/scripts/compose-env-probe.yaml"
dotenv_parser="$repo_root/scripts/compose-env-project.awk"

if [[ ! -f "$env_file" || -L "$env_file" ]]; then
  echo "A local root .env file is required to resolve this worktree's Docker project." >&2
  exit 1
fi

if [[ "$(awk -v MODE=detect -f "$dotenv_parser" "$env_file")" != "yes" ]]; then
  exit 0
fi

if ! project_name="$(
  env -u COMPOSE_PROJECT_NAME -u POSTGRES_PASSWORD docker compose \
    --project-directory "$repo_root" \
    --env-file "$env_file" \
    -f "$probe_file" \
    config --format yaml \
    | awk '
      /^name: / { project_name = substr($0, 7); found = 1 }
      $1 == "gomoku.project-present:" && $2 == "present" { configured = 1 }
      END {
        if (!found) exit 1
        if (configured) print project_name
      }
    '
)"; then
  echo "Docker Compose could not parse COMPOSE_PROJECT_NAME from the root .env file." >&2
  exit 1
fi

printf '%s\n' "$project_name"
