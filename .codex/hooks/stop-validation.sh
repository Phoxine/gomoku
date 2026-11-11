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
  echo "Skipping final validation: no Docker Compose file was found at the repository root." >&2
  printf '{}\n'
  exit 0
fi

env_file="$repo_root/.env"
if [[ ! -f "$env_file" ]]; then
  echo "Skipping final validation: this worktree has no root .env file." >&2
  printf '{}\n'
  exit 0
fi

compose=(bash "$repo_root/scripts/compose.sh")

if ! running_services="$("${compose[@]}" ps --status running --services)"; then
  echo "Skipping final validation: unable to query Docker Compose services for this worktree." >&2
  printf '{}\n'
  exit 0
fi

if ! grep -qx app <<< "$running_services"; then
  echo "Skipping final validation: Docker Compose app service is not running for this worktree." >&2
  printf '{}\n'
  exit 0
fi

# 1. Validate code formatting
echo "🧼 Checking code formatting with ruff..." >&2
"${compose[@]}" exec -T app uv run ruff format --check app/ tests/ >&2 || exit 2

# 2. Perform static analysis and linting
echo "🔍 Linting code with ruff..." >&2
"${compose[@]}" exec -T app uv run ruff check app/ tests/ >&2 || exit 2

# 3. Execute unit tests
echo "🧪 Running unit tests with pytest..." >&2
"${compose[@]}" exec -T app uv run pytest >&2 || exit 2

printf '{}\n'
