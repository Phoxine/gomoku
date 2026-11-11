# Codex Host Prerequisites

Install `uv` on the host before using Codex with this repository. The
PreToolUse hook runs the command policy through `uv`; the hook reports a clear
error and exits if `uv` is unavailable.
