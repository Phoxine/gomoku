#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
branch_name="$(git -C "$repo_root" branch --show-current)"

if [[ -z "$branch_name" ]]; then
  echo "Run this script from a feature branch, not a detached HEAD." >&2
  exit 1
fi

project_suffix="$(printf '%s' "$branch_name" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's/[^a-z0-9_-]+/_/g; s/^[^a-z0-9]+//; s/_+$//')"
if [[ -z "$project_suffix" ]]; then
  echo "Could not derive a Docker project name from branch '$branch_name'." >&2
  exit 1
fi
project_name="gomoku_${project_suffix}"

root_env="$repo_root/.env"
app_env="$repo_root/src/.env"

if [[ -L "$root_env" || -L "$app_env" ]]; then
  echo "Worktree .env files must be local files, not symlinks shared with another worktree." >&2
  exit 1
fi

if [[ ! -e "$root_env" ]]; then
  if ! command -v openssl >/dev/null 2>&1; then
    echo "OpenSSL is required to generate a local PostgreSQL password." >&2
    exit 1
  fi
  umask 077
  printf 'COMPOSE_PROJECT_NAME=%s\nPOSTGRES_PASSWORD=%s\n' \
    "$project_name" "$(openssl rand -hex 32)" > "$root_env"
else
  existing_project="$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$root_env" | tail -n 1)"
  if [[ -n "$existing_project" && "$existing_project" != "$project_name" ]]; then
    echo "The root .env belongs to a different Docker project. Keep its secrets and set COMPOSE_PROJECT_NAME=$project_name manually." >&2
    exit 1
  fi

  needs_password="false"
  if ! grep -q '^POSTGRES_PASSWORD=.' "$root_env"; then
    if ! command -v openssl >/dev/null 2>&1; then
      echo "OpenSSL is required to generate a local PostgreSQL password." >&2
      exit 1
    fi
    needs_password="true"
    postgres_password="$(openssl rand -hex 32)"
  fi

  if [[ "$existing_project" != "$project_name" || "$needs_password" == "true" ]]; then
    temp_env="$(mktemp "$repo_root/.env.XXXXXX")"
    awk -v project_name="$project_name" -v postgres_password="${postgres_password:-}" '
      /^COMPOSE_PROJECT_NAME=/ {
        print "COMPOSE_PROJECT_NAME=" project_name
        project_seen = 1
        next
      }
      /^POSTGRES_PASSWORD=/ {
        if (postgres_password != "") {
          print "POSTGRES_PASSWORD=" postgres_password
        } else {
          print
        }
        password_seen = 1
        next
      }
      { print }
      END {
        if (!project_seen) print "COMPOSE_PROJECT_NAME=" project_name
        if (!password_seen && postgres_password != "") print "POSTGRES_PASSWORD=" postgres_password
      }
    ' "$root_env" > "$temp_env"
    chmod 600 "$temp_env"
    mv "$temp_env" "$root_env"
  fi
fi

if [[ ! -e "$app_env" ]]; then
  cp "$repo_root/src/.env.example" "$app_env"
fi

chmod 600 "$root_env" "$app_env"

echo "Initialized isolated Docker settings for $project_name."
