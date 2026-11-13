#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

root_env="$repo_root/.env"
app_env="$repo_root/src/.env"
project_name="$(bash "$repo_root/scripts/worktree-project-name.sh")"
default_project="$(bash "$repo_root/scripts/worktree-project-name.sh" directory)"
legacy_default_project="gomoku"

if [[ ! -f "$root_env" ]]; then
  if ! existing_default_volumes="$(docker volume ls --quiet \
    --filter "label=com.docker.compose.project=$project_name" \
    --filter label=com.docker.compose.volume=postgres_data)"; then
    echo "Could not inspect Docker volumes; refusing to create credentials without checking the existing database." >&2
    exit 1
  fi
  if [[ "$default_project" != "$project_name" ]]; then
    if ! default_project_volumes="$(docker volume ls --quiet \
      --filter "label=com.docker.compose.project=$default_project" \
      --filter label=com.docker.compose.volume=postgres_data)"; then
      echo "Could not inspect Docker volumes; refusing to create credentials without checking the directory-default database." >&2
      exit 1
    fi
  else
    default_project_volumes="$existing_default_volumes"
  fi
  if [[ "$legacy_default_project" != "$project_name" && "$legacy_default_project" != "$default_project" ]]; then
    if ! legacy_default_volumes="$(docker volume ls --quiet \
      --filter "label=com.docker.compose.project=$legacy_default_project" \
      --filter label=com.docker.compose.volume=postgres_data)"; then
      echo "Could not inspect Docker volumes; refusing to create credentials without checking the legacy database." >&2
      exit 1
    fi
  else
    legacy_default_volumes=""
  fi
  if [[ -n "$existing_default_volumes" || -n "$default_project_volumes" || -n "$legacy_default_volumes" ]]; then
    echo "An existing database volume for this, the directory-default, or the legacy Compose project is protected. Restore its original .env and POSTGRES_PASSWORD, or choose a documented database migration before starting a new project." >&2
    exit 1
  fi

  app_port="${APP_PORT:-8000}"
  postgres_password="$(openssl rand -hex 32)"
  temp_env="$(mktemp "$repo_root/.env.XXXXXX")"
  trap 'rm -f -- "$temp_env"' EXIT
  printf 'COMPOSE_PROJECT_NAME=%s\nPOSTGRES_PASSWORD=%s\nAPP_PORT=%s\n' \
    "$project_name" \
    "$postgres_password" "$app_port" > "$temp_env"
  chmod 600 "$temp_env"
  mv "$temp_env" "$root_env"
  trap - EXIT
fi

configured_project="$(bash "$repo_root/scripts/resolve-compose-project-name.sh" "$root_env")"
legacy_local_project="gomoku_main_local"
if [[ "$configured_project" == "$legacy_local_project" ]]; then
  if ! old_project_volume="$(docker volume ls --quiet \
    --filter "label=com.docker.compose.project=$configured_project" \
    --filter label=com.docker.compose.volume=postgres_data)"; then
    echo "Could not inspect the existing local database volume; refusing to change the Compose project name." >&2
    exit 1
  fi
  if [[ -n "$old_project_volume" ]]; then
    echo "The $configured_project database volume exists. Keep its Compose project name or migrate its database before changing it." >&2
    exit 1
  fi

  temp_env="$(mktemp "$repo_root/.env.XXXXXX")"
  trap 'rm -f -- "$temp_env"' EXIT
  awk -v MODE=update \
    -v project_name="$project_name" \
    -v update_project=yes \
    -v update_password=no \
    -f "$repo_root/scripts/compose-env-project.awk" "$root_env" > "$temp_env"
  chmod 600 "$temp_env"
  mv "$temp_env" "$root_env"
  trap - EXIT
  configured_project="$project_name"
fi

if [[ "$configured_project" != "$project_name" && \
  "$configured_project" != "$(bash "$repo_root/scripts/worktree-project-name.sh" legacy)" && \
  "$configured_project" != "$(bash "$repo_root/scripts/worktree-project-name.sh" directory)" ]]; then
  echo "The root .env project name does not belong to this checkout. Keep its database settings or migrate the database explicitly." >&2
  exit 1
fi

if [[ ! -f "$app_env" ]]; then
  cp "$repo_root/src/.env.example" "$app_env"
  chmod 600 "$app_env"
fi

if ! grep -Eq '^[[:space:]]*(export[[:space:]]+)?COMPOSE_PROJECT_NAME[[:space:]]*=[[:space:]]*[a-z0-9][a-z0-9_-]*([[:space:]]*(#.*)?)?$' "$root_env"; then
  echo "Set a valid COMPOSE_PROJECT_NAME in the repository-root .env file." >&2
  exit 1
fi

if ! grep -Eq '^[[:space:]]*(export[[:space:]]+)?POSTGRES_PASSWORD[[:space:]]*=[[:space:]]*[^[:space:]#]+([[:space:]]*(#.*)?)?$' "$root_env"; then
  echo "Set POSTGRES_PASSWORD in the repository-root .env file." >&2
  exit 1
fi

if ! grep -Eq '^[[:space:]]*(export[[:space:]]+)?DEBUG[[:space:]]*=[[:space:]]*True([[:space:]]*(#.*)?)?$' "$app_env"; then
  echo "Set DEBUG=True in src/.env before starting the local development server." >&2
  exit 1
fi

if ! grep -Eq '^[[:space:]]*(export[[:space:]]+)?APP_PORT[[:space:]]*=[[:space:]]*[0-9]+([[:space:]]*(#.*)?)?$' "$root_env"; then
  printf '\nAPP_PORT=%s\n' "${APP_PORT:-8000}" >> "$root_env"
fi

bash "$repo_root/scripts/compose.sh" -f compose.web.yaml up --build -d
bash "$repo_root/scripts/compose.sh" exec app uv run python manage.py migrate

port="${APP_PORT:-$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?APP_PORT[[:space:]]*=[[:space:]]*([0-9]+).*/\2/p' "$root_env" | tail -n 1)}"
printf 'Gomoku is running at http://localhost:%s/\n' "$port"
