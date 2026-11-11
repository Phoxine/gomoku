#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
root_env="$repo_root/.env"
app_env="$repo_root/src/.env"
lock_dir="$repo_root/.worktree-env.lock"
temp_root_env=""
temp_app_env=""
temp_probe_env=""
project_name="$(bash "$repo_root/scripts/worktree-project-name.sh")"
legacy_project="$(bash "$repo_root/scripts/worktree-project-name.sh" legacy)"

if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another worktree environment initialization is running, or a stale lock exists at $lock_dir." >&2
  exit 1
fi

# cleanup_worktree_env removes partial environment files and releases the initialization lock.
# The EXIT trap calls it after successful initialization or any handled failure.
cleanup_worktree_env() {
  if [[ -n "$temp_root_env" && -e "$temp_root_env" ]]; then
    rm -f -- "$temp_root_env"
  fi
  if [[ -n "$temp_app_env" && -e "$temp_app_env" ]]; then
    rm -f -- "$temp_app_env"
  fi
  if [[ -n "$temp_probe_env" && -e "$temp_probe_env" ]]; then
    rm -f -- "$temp_probe_env"
  fi
  rmdir "$lock_dir" 2>/dev/null || true
}

trap cleanup_worktree_env EXIT
trap 'exit 1' HUP INT TERM
umask 077

if [[ -L "$root_env" || -L "$app_env" ]]; then
  echo "Worktree .env files must be local files, not symlinks shared with another worktree." >&2
  exit 1
fi

if [[ -e "$root_env" ]]; then
  if ! existing_project="$(bash "$repo_root/scripts/resolve-compose-project-name.sh" "$root_env")"; then
    echo "Could not safely resolve this worktree's existing Compose project name." >&2
    exit 1
  fi

  if [[ -n "$existing_project" && "$existing_project" != "$project_name" && "$existing_project" != "$legacy_project" ]]; then
    echo "The root .env belongs to a different Docker project. Keep its database volume and resolve the project-name mismatch explicitly." >&2
    exit 1
  fi

  if [[ "$existing_project" == "$legacy_project" && "$existing_project" != "$project_name" ]]; then
    echo "Keeping the legacy Compose project name to preserve its existing database volume. Migrate the database explicitly before switching to the hashed project name." >&2
  fi

  temp_probe_env="$(mktemp "$repo_root/.env.XXXXXX")"
  awk '!/^[[:space:]]*(export[[:space:]]+)?COMPOSE_PROJECT_NAME[[:space:]]*[=:]/' "$root_env" > "$temp_probe_env"
  chmod 600 "$temp_probe_env"
  if ! password_present="$(
    env -u COMPOSE_PROJECT_NAME -u POSTGRES_PASSWORD docker compose \
      --project-directory "$repo_root" \
      --env-file "$temp_probe_env" \
      -f "$repo_root/scripts/compose-env-probe.yaml" \
      config --environment \
      | awk -F= '
        $1 == "POSTGRES_PASSWORD" {
          resolved_value = substr($0, index($0, "=") + 1)
          found = 1
        }
        END {
          if (found && length(resolved_value) > 0) print "yes"
          else print "no"
        }
      '
  )"; then
    echo "Docker Compose could not read environment values from the root .env file." >&2
    exit 1
  fi
  rm -f -- "$temp_probe_env"
  temp_probe_env=""
else
  existing_project=""
  password_present="no"
fi

if [[ "$password_present" != "yes" ]]; then
  if ! command -v openssl >/dev/null 2>&1; then
    echo "OpenSSL is required to generate a local PostgreSQL password." >&2
    exit 1
  fi
  postgres_password="$(openssl rand -hex 32)"
else
  postgres_password=""
fi

if [[ ! -e "$root_env" ]]; then
  temp_root_env="$(mktemp "$repo_root/.env.XXXXXX")"
  printf 'COMPOSE_PROJECT_NAME=%s\nPOSTGRES_PASSWORD=%s\n' \
    "$project_name" "$postgres_password" > "$temp_root_env"
  chmod 600 "$temp_root_env"
  mv "$temp_root_env" "$root_env"
  temp_root_env=""
elif [[ -z "$existing_project" || "$password_present" != "yes" ]]; then
  temp_root_env="$(mktemp "$repo_root/.env.XXXXXX")"
  awk \
    -v project_name="$project_name" \
    -v update_project="$([[ -z "$existing_project" ]] && printf yes || printf no)" \
    -v postgres_password="$postgres_password" \
    -v update_password="$([[ "$password_present" == "yes" ]] && printf no || printf yes)" '
      /^[[:space:]]*(export[[:space:]]+)?COMPOSE_PROJECT_NAME[[:space:]]*[=:]/ {
        if (update_project == "yes") print "COMPOSE_PROJECT_NAME=" project_name
        else print
        project_seen = 1
        next
      }
      /^[[:space:]]*(export[[:space:]]+)?POSTGRES_PASSWORD[[:space:]]*=/ {
        if (update_password == "yes") print "POSTGRES_PASSWORD=" postgres_password
        else print
        password_seen = 1
        next
      }
      { print }
      END {
        if (!project_seen && update_project == "yes") print "COMPOSE_PROJECT_NAME=" project_name
        if (!password_seen && update_password == "yes") print "POSTGRES_PASSWORD=" postgres_password
      }
    ' "$root_env" > "$temp_root_env"
  chmod 600 "$temp_root_env"
  mv "$temp_root_env" "$root_env"
  temp_root_env=""
fi

if [[ ! -e "$app_env" ]]; then
  temp_app_env="$(mktemp "$repo_root/src/.env.XXXXXX")"
  cp "$repo_root/src/.env.example" "$temp_app_env"
  chmod 600 "$temp_app_env"
  mv "$temp_app_env" "$app_env"
  temp_app_env=""
fi

chmod 600 "$root_env" "$app_env"

if [[ "$existing_project" == "$legacy_project" && "$existing_project" != "$project_name" ]]; then
  echo "Initialized environment while retaining legacy project $existing_project."
else
  echo "Initialized isolated Docker settings for $project_name."
fi
