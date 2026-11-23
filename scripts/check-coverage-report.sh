#!/usr/bin/env bash
set -euo pipefail

report="$1"
if [[ ! -f "$report" || ! -s "$report" ]]; then
    printf 'Coverage report is missing or empty at %s. Check the pytest XML output path and the Compose workspace mount.\n' "$report" >&2
    exit 1
fi
