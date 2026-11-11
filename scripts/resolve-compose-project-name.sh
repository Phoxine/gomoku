#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
env_file="${1:-$repo_root/.env}"
probe_file="$repo_root/scripts/compose-env-probe.yaml"

if [[ ! -f "$env_file" || -L "$env_file" ]]; then
  echo "A local root .env file is required to resolve this worktree's Docker project." >&2
  exit 1
fi

if ! awk '
  /^[[:space:]]*(export[[:space:]]+)?COMPOSE_PROJECT_NAME[[:space:]]*[=:]/ {
    value = $0
    sub(/^[^=:]*[=:]/, "", value)
    sub(/^[[:space:]]+/, "", value)
    sub(/^#.*/, "", value)
    sub(/[[:space:]]+#.*$/, "", value)
    sub(/[[:space:]]+$/, "", value)
    configured = value != "" && value != "\"\"" && value != "\047\047"
  }
  END { exit !configured }
' "$env_file"; then
  exit 0
fi

if ! project_name="$(
  env -u COMPOSE_PROJECT_NAME -u POSTGRES_PASSWORD docker compose \
    --project-directory "$repo_root" \
    --env-file "$env_file" \
    -f "$probe_file" \
    config --environment \
    | awk -F= '
      $1 == "COMPOSE_PROJECT_NAME" {
        project_name = substr($0, index($0, "=") + 1)
        found = 1
      }
      END {
        if (!found) exit 1
        print project_name
      }
    '
)"; then
  echo "Docker Compose could not parse COMPOSE_PROJECT_NAME from the root .env file." >&2
  exit 1
fi

printf '%s\n' "$project_name"
