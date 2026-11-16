import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".codex/hooks/pre_tool_use_policy.py"
spec = importlib.util.spec_from_file_location("command_policy", HOOK)
assert spec is not None and spec.loader is not None
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def test_hook_syntax_supports_host_python_310() -> None:
    ast.parse(HOOK.read_text(), feature_version=(3, 10))


def test_hook_uses_postponed_annotations_for_python_39() -> None:
    tree = ast.parse(HOOK.read_text(), feature_version=(3, 9))
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf folder",
        "rm --force --recursive folder",
        "rm --for --rec folder",
        "rm -fr folder",
        "git push origin branch --force",
        "git push origin branch --for",
        "git -C repo --no-pager push --force-with-lease=main:abc",
        "git push origin +branch:branch",
        "env NAME=value git push -f",
        "env -i git reset --hard HEAD",
        "env -u FOO git reset --hard HEAD",
        "env --unset=FOO -- rm -fr folder",
        "env --unknown git status",
        "NAME=value git reset --hard",
        "git --no-pager reset HEAD --hard",
        "git reset --har HEAD",
        "git reset --hard > output.log",
        "rm -fr folder 2> errors.log",
        "git reset --hard >> output.log",
        "git reset --hard 2>&1",
        "rm -fr folder > output.log 2>&1",
        'git reset --hard "$target"',
        "rm -fr $target",
        'git push --force "${branch}"',
        'echo "$target" && git reset --hard HEAD',
        'git reset --hard "${target:-HEAD}"',
        "rm -fr ${target:-folder}",
        "echo safe\ngit reset --hard HEAD\n",
        "git reset --hard *.txt",
        "echo $(date); git reset --hard HEAD",
        'echo "$(git reset --hard HEAD)"',
        "echo $(rm -fr folder)",
        "echo `rm -fr folder`",
        'echo "`git reset --hard HEAD`"',
        'echo "\\q`git reset --hard HEAD`"',
        "echo `git status; rm -fr folder`",
        "echo `echo \\`rm -fr folder\\``",
        "echo $(echo `git reset --hard HEAD`)",
        "echo `unterminated",
        "echo ${foo%a} `git reset --hard HEAD`",
        "echo ${foo%a} `rm -fr folder`",
        "echo ${foo%a} `git status`",
        'echo "$(echo $(git reset --hard HEAD))"',
        "echo \"$(printf 'a;b')\"; rm -fr folder",
        "rm -fr folder # trailing comment",
        'git reset --hard "${target:-$(echo HEAD)}"',
        "echo okay && git push -f",
        "sh -c 'git push -f'",
        "command git reset --hard HEAD",
        "exec rm -fr folder",
        "sudo -u user git reset --hard HEAD",
        "nohup rm -fr folder",
        "timeout 5 git push --force",
        "eval 'git reset --hard HEAD'",
        "(echo ok); git reset --hard HEAD",
        "echo {a,b}; rm -fr folder",
        "echo {a,b}; git push -f origin main",
        "echo ~; git reset --hard HEAD",
        "git status 2>&1\ngit reset --hard HEAD",
        "bash -e -c 'git reset --hard HEAD'",
        "bash -ec 'rm -fr folder'",
        "bash -o errexit -c 'git push -f'",
        "bash -eo pipefail -c 'git reset --hard HEAD'",
        "bash +eO extglob -c 'rm -fr folder'",
        "bash -eoc pipefail 'git status'",
        "bash -eo",
        "zsh -oshwordsplit -c 'git reset --hard HEAD'",
        "zsh -o shwordsplit -c 'git reset --hard HEAD'",
        "if true; then rm -fr folder; fi",
        "for f in a; do git push -f; done",
        "while true; do git reset --hard; done",
        "printf hello | sh",
        "bash -s",
        "$X -rf dir",
        "exec -a worker git reset --hard HEAD",
        "exec -la worker rm -fr folder",
        "exec -a",
        "git --unknown status",
        "psql -c 'DROP TABLE games'",
        "dropdb database",
        "cat .env",
    ],
)
def test_blocks_unsafe_or_unsupported_commands(command: str) -> None:
    assert policy.blocked(command)


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git --no-pager push origin branch",
        "git -C repo reset --soft HEAD",
        "rm -r folder",
        "rm -f file",
        "echo 'a ; b | c'",
        "echo a\\;b",
        "env NAME=value git status",
        "env -i -u FOO -- git status",
        "env --unset=FOO NAME=value git status",
        "sh -c 'git status'",
        "echo one && echo two",
        "bash scripts/init-worktree-env.sh",
        "bash .codex/hooks/stop-validation.sh",
        "bash scripts/compose.sh up --build -d",
        "bash scripts/compose.sh down",
        "docker compose down",
        "bash scripts/compose.sh ps --all",
        "bash scripts/compose.sh exec -T app uv run pytest -q tests",
        "bash scripts/compose.sh exec app uv run pytest",
        "bash scripts/compose.sh exec app uv run python manage.py check",
        "bash scripts/compose.sh ps --status running --services",
        "bash scripts/compose.sh -f compose.web.yaml up -d",
        "bash scripts/start-local-server.sh",
        "bash scripts/compose.sh exec app uv run python manage.py migrate",
        "docker compose down --volumes",
        "bash scripts/compose.sh down --remove-orphans --volumes",
        "echo $(git status)",
        "echo `git status`",
        'echo "`git status`"',
        'echo "\\q`git status`"',
        'echo "\\`git reset --hard HEAD\\`"',
        "echo '`git reset --hard HEAD`'",
        "echo \\`git\\ reset\\ --hard\\ HEAD\\`",
        "echo `printf 'git reset --hard HEAD'`",
        "echo $NAME",
        'git status "$target"',
        'rm -r "${target}"',
        'echo "git reset --hard ${target:-HEAD}"',
        "echo safe\ngit status\n",
        'echo "git reset --hard *.txt"',
        "echo $(printf 'git reset --hard'); git status",
        "echo \"$(printf 'git reset --hard HEAD')\"",
        "echo safe # git reset --hard HEAD",
        "echo *.txt",
        "echo value > file",
        "git status > output.log",
        "git status 2> errors.log",
        "git status 2>&1",
        "git status > output.log 2>&1",
        "sudo git status",
        "command git status",
        "nohup git status",
        "eval 'git status'",
        "timeout 5 echo git reset --hard HEAD",
        "sudo echo git reset --hard HEAD",
        "git status 2>&1\ngit status",
        "bash -e -c 'git status'",
        "bash -eo pipefail -c 'git status'",
        "bash +eO extglob -c 'git status'",
        "zsh -o shwordsplit -c 'git status'",
        "zsh -c 'git status'",
        "bash scripts/start-local-server.sh",
        "exec -a worker git status",
        "exec -la worker echo 'git reset --hard HEAD'",
    ],
)
def test_allows_inspectable_safe_commands(command: str) -> None:
    assert not policy.blocked(command)


def test_hook_does_not_echo_blocked_command() -> None:
    secret = "sensitive-value"
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"command": "git push -f " + secret}}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert secret not in result.stderr + result.stdout


def test_hook_blocks_zsh_attached_option_before_command() -> None:
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(
            {"tool_input": {"command": "zsh -oshwordsplit -c 'git reset --hard HEAD'"}}
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2


def test_hook_does_not_invent_approval_decision() -> None:
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(
            {
                "tool_input": {"command": "docker compose down --volumes"},
                "approved": True,
            }
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
