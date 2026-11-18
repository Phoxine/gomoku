"""Installed outside the workspace to stop a path-bound Compose project."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


PROJECT = "com.docker.compose.project"
NETWORK = "com.docker.compose.network"
CONTAINER_FIELDS = (
    '{{.ID}}\t{{.Label "com.docker.compose.project"}}'
    '\t{{.Label "com.docker.compose.project.working_dir"}}\t{{.State}}'
)
NETWORK_FIELDS = '{{.ID}}\t{{.Label "com.docker.compose.project"}}'
HOST_ENV = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
}


def cleanup(docker, worktree):
    """Stop and remove only Compose resources belonging to this worktree."""
    suffix = hashlib.sha256(os.fsencode(worktree)).hexdigest()[:16]
    project_pattern = re.compile(rf"gomoku_[a-z0-9_-]+_{suffix}")
    containers = docker(
        "container",
        "ls",
        "--all",
        "--no-trunc",
        "--filter",
        f"label={PROJECT}",
        "--format",
        CONTAINER_FIELDS,
    )
    networks = docker(
        "network",
        "ls",
        "--no-trunc",
        "--filter",
        f"label={NETWORK}",
        "--format",
        NETWORK_FIELDS,
    )
    container_rows = [line.split("\t") for line in containers.splitlines()]
    network_rows = [line.split("\t") for line in networks.splitlines()]
    if any(
        (owner == str(worktree)) != bool(project_pattern.fullmatch(project))
        for _, project, owner, _ in container_rows
    ):
        raise ValueError("Compose container labels disagree with this worktree's path.")
    container_rows = [row for row in container_rows if row[2] == str(worktree)]
    network_rows = [
        (network_id, project)
        for network_id, project in network_rows
        if project_pattern.fullmatch(project)
    ]
    projects = {row[1] for row in container_rows + network_rows}
    if len(projects) > 1:
        raise ValueError("Multiple path-bound Compose projects found. Verify ownership manually.")
    if network_rows and not container_rows:
        raise ValueError("Cannot confirm network ownership without a Compose container.")
    if any(not re.fullmatch(r"[a-f0-9]{64}", row[0]) for row in container_rows + network_rows):
        raise ValueError("Docker returned an unexpected resource ID.")

    running = [row[0] for row in container_rows if row[3] in {"running", "restarting", "paused"}]
    if running:
        docker("container", "stop", "--", *running)
    if container_rows:
        docker("container", "rm", "--", *(row[0] for row in container_rows))
    if network_rows:
        docker("network", "rm", "--", *(row[0] for row in network_rows))


def main():
    if len(sys.argv) != 1:
        raise ValueError("Usage: stop-local-stack.py (no arguments)")
    installation = Path(__file__).resolve().parent
    config = json.loads((installation / "cleanup.json").read_text())
    repository = Path(config["repository_root"]).resolve(strict=True)
    worktrees = Path(config["worktrees_root"]).resolve(strict=True)
    worktree = Path.cwd().resolve()
    if worktree != repository and worktree.parent != worktrees:
        raise ValueError("Run cleanup from the root of a configured Gomoku worktree.")

    registered = subprocess.check_output(
        ["/usr/bin/git", "-C", str(repository), "worktree", "list", "--porcelain", "-z"],
        env=HOST_ENV,
        text=True,
    )
    if not any(
        entry.startswith("worktree ") and Path(entry[9:]).resolve() == worktree
        for entry in registered.split("\0")
    ):
        raise ValueError("The current directory is not a registered Gomoku worktree.")

    binary = Path(config["docker_binary"]).resolve(strict=True)
    host = config["docker_host"]
    if not host.startswith("unix:///"):
        raise ValueError("Cleanup requires a local Docker Unix socket.")
    for root in (repository, worktrees):
        if any(path == root or root in path.parents for path in (installation, binary)):
            raise ValueError("Install the cleanup helper and Docker outside Gomoku workspaces.")

    def docker(*args):
        return subprocess.check_output(
            [str(binary), "--config", str(installation), "--host", host, *args],
            env=HOST_ENV,
            text=True,
        )

    cleanup(docker, worktree)


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Compose cleanup failed: {error}", file=sys.stderr)
        sys.exit(1)
