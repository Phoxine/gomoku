#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

compose_file=""
for candidate in compose.yaml compose.yml docker-compose.yaml docker-compose.yml; do
  if [[ -f "$candidate" ]]; then
    compose_file="$candidate"
    break
  fi
done

if [[ -z "$compose_file" ]]; then
  echo "Skipping final validation: no Docker Compose file was found at the repository root."
  exit 0
fi

if ! docker compose -f "$compose_file" ps --status running --services | grep -qx app; then
  echo "Skipping final validation: Docker Compose app service is not running."
  exit 0
fi

docker compose -f "$compose_file" exec -T app uv run pytest
