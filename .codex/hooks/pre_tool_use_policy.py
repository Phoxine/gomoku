#!/usr/bin/env python3
"""Conservative command-text guard; sandbox and DB permissions remain essential.

Literal shell words, simple variable references, quoting, simple separators
and static redirections are inspected. Variable values are not resolved.
Unsupported syntax falls back to the existing text checks and is not fully
inspected. This cannot inspect programs, scripts, or other tool calls. Rules
prompt only outside the sandbox; Compose volume approval is not guaranteed
when the sandbox can access Docker.
"""

from __future__ import annotations

import json
import re
import sys


class UnsupportedCommand(ValueError):
    """The command cannot be inspected safely."""


class UnsupportedBacktick(UnsupportedCommand):
    """An incomplete or ambiguous backtick substitution."""


def backtick_end(command: str, start: int) -> tuple[int, str]:
    """Extract old-style command substitution using shell backslash rules."""
    content: list[str] = []
    i = start + 1
    while i < len(command):
        char = command[i]
        if char == "`":
            return i, "".join(content)
        if char == "\\" and i + 1 < len(command):
            following = command[i + 1]
            if following in "$`\\\n":
                if following != "\n":
                    content.append(following)
                i += 2
                continue
        content.append(char)
        i += 1
    raise UnsupportedBacktick


def substitution_end(command: str, start: int) -> int:
    """Find a balanced command substitution without executing or inspecting it."""
    depth = 1
    quote = ""
    i = start + 2
    while i < len(command):
        char = command[i]
        if char == "\\" and quote != "'":
            i += 2
            continue
        if char == "`" and quote != "'":
            i, _ = backtick_end(command, i)
            i += 1
            continue
        if quote == "'":
            if char == "'":
                quote = ""
        elif char in "'\"" and not quote:
            quote = char
        elif char == '"' and quote == '"':
            quote = ""
        elif not quote and char == "(":
            depth += 1
        elif not quote and char == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise UnsupportedCommand


def tokenize(command: str, substitutions: list[str] | None = None) -> list[list[str]]:
    """Parse literal words without losing quoted command separators."""
    commands: list[list[str]] = [[]]
    word: list[str] = []
    started = False
    quote = ""
    i = 0
    while i < len(command):
        char = command[i]
        if quote == "'":
            if char == "'":
                quote = ""
            else:
                word.append(char)
        elif quote == '"':
            if char == '"':
                quote = ""
            elif char == "$":
                if command.startswith("$(", i):
                    end = substitution_end(command, i)
                    if substitutions is not None:
                        substitutions.append(command[i + 2 : end])
                    i = end
                    word.append("\0substitution")
                    i += 1
                    continue
                match = re.match(
                    r"\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*(?::[-+=?][^{}$`]*)?\})",
                    command[i:],
                )
                if not match:
                    raise UnsupportedCommand
                word.append("\0variable")
                i += len(match.group()) - 1
            elif char == "`":
                end, content = backtick_end(command, i)
                if substitutions is not None:
                    substitutions.append(content)
                i = end
                word.append("\0substitution")
            elif char == "\\":
                if i + 1 >= len(command):
                    raise UnsupportedCommand
                following = command[i + 1]
                if following in '$`"\\\n':
                    if following != "\n":
                        word.append(following)
                    i += 1
                else:
                    word.append(char)
            else:
                word.append(char)
        elif char in "'\"":
            quote = char
            started = True
        elif char == "\\":
            i += 1
            if i >= len(command) or command[i] in "\n\r":
                raise UnsupportedCommand
            word.append(command[i])
            started = True
        elif char in " \t":
            if started:
                commands[-1].append("".join(word))
                word = []
                started = False
        elif char in ";&|\n":
            if started:
                commands[-1].append("".join(word))
                word = []
                started = False
            if char == "\n" and not commands[-1]:
                i += 1
                continue
            if not commands[-1]:
                raise UnsupportedCommand
            if char in "&|" and i + 1 < len(command) and command[i + 1] == char:
                i += 1
            elif char == "&":
                raise UnsupportedCommand
            commands.append([])
        elif char in "<>":
            if started:
                # An adjacent numeric word is a file descriptor, not an argument.
                if not "".join(word).isdigit():
                    commands[-1].append("".join(word))
                word = []
                started = False
            operator = char
            if i + 1 < len(command) and command[i + 1] == char:
                operator += char
                i += 1
            if operator not in {"<", ">", ">>"}:
                raise UnsupportedCommand
            if (
                operator in {"<", ">"}
                and i + 1 < len(command)
                and command[i + 1] == "&"
            ):
                i += 2
                start = i
                while i < len(command) and command[i].isdigit():
                    i += 1
                if i == start:
                    if i < len(command) and command[i] == "-":
                        i += 1
                    else:
                        raise UnsupportedCommand
                if i < len(command) and command[i] not in " \t;&|<>":
                    raise UnsupportedCommand
                i -= 1
            else:
                commands[-1].append("\0redirect")
        elif char == "$":
            if command.startswith("$(", i):
                end = substitution_end(command, i)
                if substitutions is not None:
                    substitutions.append(command[i + 2 : end])
                i = end
                word.append("\0substitution")
                started = True
                i += 1
                continue
            match = re.match(
                r"\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*(?::[-+=?][^{}$`]*)?\})",
                command[i:],
            )
            if not match:
                raise UnsupportedCommand
            word.append("\0variable")
            started = True
            i += len(match.group()) - 1
        elif char == "#" and not started:
            end = command.find("\n", i)
            if end == -1:
                break
            i = end - 1
        elif char in "*?[]":
            word.append("\0glob")
            started = True
        elif char == "`":
            end, content = backtick_end(command, i)
            if substitutions is not None:
                substitutions.append(content)
            i = end
            word.append("\0substitution")
            started = True
        elif char in "\r(){}~!":
            raise UnsupportedCommand
        else:
            word.append(char)
            started = True
        i += 1
    if quote:
        raise UnsupportedCommand
    if started:
        commands[-1].append("".join(word))
    if not commands[-1] and len(commands) > 1:
        if command.rstrip(" \t").endswith("\n"):
            commands.pop()
        else:
            raise UnsupportedCommand
    stripped = []
    for args in commands:
        result = []
        index = 0
        while index < len(args):
            if args[index] == "\0redirect":
                if index + 1 >= len(args) or args[index + 1] == "\0redirect":
                    raise UnsupportedCommand
                index += 2
            else:
                result.append(args[index])
                index += 1
        stripped.append(result)
    return stripped


def git_blocked(args: list[str]) -> bool:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        option = args[i]
        if option in {
            "-C",
            "-c",
            "--git-dir",
            "--work-tree",
            "--namespace",
            "--exec-path",
        }:
            if i + 1 == len(args):
                return True
            i += 2
        elif option in {
            "--no-pager",
            "--paginate",
            "-p",
            "-P",
            "--bare",
            "--no-replace-objects",
            "--literal-pathspecs",
            "--no-optional-locks",
        } or option.startswith(
            (
                "--git-dir=",
                "--work-tree=",
                "--namespace=",
                "--exec-path=",
                "--config-env=",
            )
        ):
            i += 1
        else:
            return True
    if i == len(args):
        return False
    operation, options = args[i], args[i + 1 :]
    if operation == "push":
        return any(
            long_option_matches(arg, "--force")
            or long_option_matches(arg, "--force-with-lease")
            or (arg.startswith("-") and not arg.startswith("--") and "f" in arg)
            or arg.startswith("+")
            for arg in options
        )
    return operation == "reset" and any(
        long_option_matches(arg, "--hard") for arg in options
    )


def long_option_matches(arg: str, option: str) -> bool:
    """Match the full option and unambiguous long-option abbreviations."""
    name = arg.split("=", 1)[0]
    return name.startswith("--") and len(name) > 2 and option.startswith(name)


def blocked(command: str, depth: int = 0) -> bool:
    if depth > 8 or len(command) > 100000:
        return True
    if any(
        re.search(pattern, command, re.IGNORECASE)
        for pattern in [
            r"rm\s+-rf\s+/",
            r"git\s+push\s+--force",
            r"dropdb\b",
            r"DROP\s+(?:DATABASE|TABLE)\b",
            r"\bcat\s+(?:\./)?(?:src/)?\.env\b",
            r"BEGIN\s+PRIVATE\s+KEY",
        ]
    ):
        return True
    try:
        substitutions: list[str] = []
        commands = tokenize(command, substitutions)
    except UnsupportedBacktick:
        return True
    except UnsupportedCommand:
        # An unsupported construct can hide a later executable substitution.
        # Reject rather than silently ignoring backticks in that case.
        if "`" in command:
            return True
        # Parenthesized shell groups may contain commands after a failed parse.
        # Do not silently allow them when this tokenizer cannot inspect them.
        if "(" in command or ")" in command:
            return True
        # Preserve a safely tokenizable command prefix when later syntax is
        # unsupported. This remains best-effort, not a shell security boundary.
        boundaries = [m.start() for m in re.finditer(r"\s+", command)]
        for end in reversed(boundaries[-128:]):
            prefix = command[:end]
            try:
                tokenize(prefix)
            except UnsupportedCommand:
                continue
            return blocked(prefix, depth + 1)
        return False
    if any(blocked(substitution, depth + 1) for substitution in substitutions):
        return True
    for args in commands:
        while args and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", args[0]):
            args = args[1:]
        if not args:
            continue
        executable = args[0].rsplit("/", 1)[-1]
        if executable == "env":
            args = args[1:]
            while args and args[0].startswith("-"):
                option = args.pop(0)
                if option == "--":
                    break
                if option in {"-i", "--ignore-environment"}:
                    continue
                if option in {"-u", "--unset"}:
                    if not args:
                        return True
                    args.pop(0)
                    continue
                if option.startswith("--unset=") or (
                    option.startswith("-u") and len(option) > 2
                ):
                    continue
                # Unknown options may change how the remaining arguments execute.
                return True
            while args and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", args[0]):
                args = args[1:]
            if not args:
                continue
            if blocked(" ".join(shlex_quote(arg) for arg in args), depth + 1):
                return True
        elif executable in {"sh", "bash", "zsh"}:
            if len(args) < 3 or args[1] not in {"-c", "-lc", "-cl"}:
                continue
            if blocked(args[2], depth + 1):
                return True
        elif executable in {
            "eval",
            "exec",
            "command",
            "builtin",
            "sudo",
            "xargs",
            "nohup",
            "time",
            "nice",
            "timeout",
            "setsid",
        }:
            if executable == "eval":
                if blocked(" ".join(args[1:]), depth + 1):
                    return True
                continue
            index = 1
            while index < len(args) and args[index].startswith("-"):
                option = args[index]
                if option == "--":
                    index += 1
                    break
                value_options = {
                    "sudo": {"-u", "-g", "-h", "-p", "-C", "-T", "-r", "-t"},
                    "nice": {"-n", "--adjustment"},
                    "timeout": {"-k", "--kill-after", "-s", "--signal"},
                    "xargs": {"-n", "-P", "-I", "-L", "-s", "-d", "-a"},
                }
                if option in value_options.get(executable, set()):
                    index += 2
                elif option.startswith("--") and "=" not in option:
                    # Unknown long options might consume a command-like argument.
                    return True
                else:
                    index += 1
            if executable == "timeout":
                index += 1  # required duration
            if index < len(args) and blocked(
                " ".join(shlex_quote(arg) for arg in args[index:]), depth + 1
            ):
                return True
        elif executable == "rm":
            options = []
            for arg in args[1:]:
                if arg == "--":
                    break
                if arg.startswith("-"):
                    options.append(arg)
            recursive = any(
                long_option_matches(arg, "--recursive")
                or (not arg.startswith("--") and ("r" in arg or "R" in arg))
                for arg in options
            )
            force = any(
                long_option_matches(arg, "--force")
                or (not arg.startswith("--") and "f" in arg)
                for arg in options
            )
            if recursive and force:
                return True
        elif executable == "git" and git_blocked(args[1:]):
            return True
    return False


def shlex_quote(word: str) -> str:
    """Quote a literal for recursive wrapper inspection."""
    return "'" + word.replace("'", "'\\''") + "'"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):  # fmt: skip
        print(
            "Command policy skipped: hook input was empty or malformed JSON.",
            file=sys.stderr,
        )
        return 0
    tool_input = payload.get("tool_input", {}) if isinstance(payload, dict) else {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if isinstance(command, str) and blocked(command):
        print(
            "Blocked by command policy: unsafe or unsupported shell syntax.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
