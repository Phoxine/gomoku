#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

# Pass the NUL-delimited index listing without mounting linked worktree metadata.
git -C "$root" ls-files --stage -z |
    docker run --rm --interactive --network none \
        --volume "$root:/workspace:ro" --workdir /workspace \
        python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f \
        sh -c '
            checker_status=0
            python -B scripts/check_docs.py --index-stdin || checker_status=$?
            python -B -m unittest discover -s scripts/tests -p check_docs_test.py || exit $?
            exit "$checker_status"
        '
