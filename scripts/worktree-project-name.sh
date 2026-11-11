#!/usr/bin/env bash
set -euo pipefail

mode="${1:-hashed}"
repo_root="$(git rev-parse --show-toplevel)"
branch_name="$(git -C "$repo_root" branch --show-current)"

if [[ -z "$branch_name" ]]; then
  echo "Run this script from a branch, not a detached HEAD." >&2
  exit 1
fi

project_suffix="$(printf '%s' "$branch_name" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's/[^a-z0-9_-]+/_/g; s/^[^a-z0-9]+//; s/_+$//')"
if [[ -z "$project_suffix" ]]; then
  echo "Could not derive a Docker project name from branch '$branch_name'." >&2
  exit 1
fi

if [[ "$mode" == "legacy" ]]; then
  printf 'gomoku_%s\n' "$project_suffix"
  exit 0
fi

if [[ "$mode" != "hashed" ]]; then
  echo "Usage: bash scripts/worktree-project-name.sh [hashed|legacy]" >&2
  exit 2
fi

project_suffix="${project_suffix:0:32}"
worktree_path="$(cd "$repo_root" && pwd -P)"
if command -v shasum >/dev/null 2>&1; then
  worktree_hash="$(printf '%s' "$worktree_path" | shasum -a 256 | cut -c 1-16)"
elif command -v sha256sum >/dev/null 2>&1; then
  worktree_hash="$(printf '%s' "$worktree_path" | sha256sum | cut -c 1-16)"
else
  echo "A SHA-256 utility (shasum or sha256sum) is required to isolate worktrees." >&2
  exit 1
fi

printf 'gomoku_%s_%s\n' "$project_suffix" "$worktree_hash"
