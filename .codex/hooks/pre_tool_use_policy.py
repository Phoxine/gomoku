#!/usr/bin/env python3
import json
import re
import sys

try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, UnicodeDecodeError):
    print("Command policy skipped: hook input was empty or malformed JSON.", file=sys.stderr)
    sys.exit(0)

tool_input = payload.get("tool_input", {}) if isinstance(payload, dict) else {}
command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
if not isinstance(command, str):
    command = ""

blocked_patterns = [
    r"rm\s+-rf\s+/",
    r"git\s+push\s+--force",
    r"dropdb\b",
    r"DROP\s+DATABASE",
    r"\bcat\s+(?:\./)?(?:src/)?\.env\b",
    r"BEGIN\s+PRIVATE\s+KEY",
]

for pattern in blocked_patterns:
    if re.search(pattern, command, re.IGNORECASE):
        print(f"Blocked unsafe command: {command}", file=sys.stderr)
        sys.exit(2)

sys.exit(0)
