#!/usr/bin/env python3
import json
import re
import sys

payload = json.load(sys.stdin)
command = ""

try:
    command = payload.get("tool_input", {}).get("command", "")
except Exception:
    command = ""

blocked_patterns = [
    r"rm\s+-rf\s+/",
    r"git\s+push\s+--force",
    r"dropdb\b",
    r"DROP\s+DATABASE",
    r"cat\s+\.env",
    r"BEGIN\s+PRIVATE\s+KEY",
]

for pattern in blocked_patterns:
    if re.search(pattern, command, re.IGNORECASE):
        print(f"Blocked unsafe command: {command}", file=sys.stderr)
        sys.exit(1)

sys.exit(0)
