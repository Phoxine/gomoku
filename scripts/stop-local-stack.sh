#!/usr/bin/env bash
set -euo pipefail

if (( $# != 0 )); then
  echo "Usage: bash scripts/stop-local-stack.sh (no arguments)" >&2
  exit 2
fi

unset CDPATH GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR
cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
GOMOKU_REQUIRE_PATH_BOUND_PROJECT=1 exec bash scripts/compose.sh down
