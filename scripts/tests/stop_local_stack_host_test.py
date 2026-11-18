import hashlib
import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import Mock, call


cleanup = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "stop-local-stack-host.py")
)["cleanup"]


class HostCleanupTest(unittest.TestCase):
    worktree = Path("/repo-worktrees/game")
    suffix = hashlib.sha256(os.fsencode(worktree)).hexdigest()[:16]
    project = f"gomoku_game_{suffix}"
    container = "a" * 64
    network = "b" * 64

    def test_stops_only_owned_resources_without_removing_volumes(self):
        docker = Mock(side_effect=[
            f"{self.container}\t{self.project}\t{self.worktree}\trunning\n",
            f"{self.network}\t{self.project}\n{'c' * 64}\tforeign\n",
            "", "", "",
        ])
        cleanup(docker, self.worktree)

        self.assertEqual(docker.call_args_list[2:], [
            call("container", "stop", "--", self.container),
            call("container", "rm", "--", self.container),
            call("network", "rm", "--", self.network),
        ])

    def test_rejects_legacy_project_before_mutating_docker(self):
        docker = Mock(side_effect=[
            f"{self.container}\tlegacy\t{self.worktree}\trunning\n", "",
        ])
        with self.assertRaisesRegex(ValueError, "disagree"):
            cleanup(docker, self.worktree)
        self.assertEqual(docker.call_count, 2)

    def test_rejects_multiple_path_bound_projects_before_mutating_docker(self):
        docker = Mock(side_effect=[
            f"{self.container}\t{self.project}\t{self.worktree}\trunning\n",
            f"{self.network}\tgomoku_other_{self.suffix}\n",
        ])
        with self.assertRaisesRegex(ValueError, "Multiple path-bound"):
            cleanup(docker, self.worktree)
        self.assertEqual(docker.call_count, 2)

    def test_no_resources_is_a_noop(self):
        docker = Mock(side_effect=["", ""])
        cleanup(docker, self.worktree)
        self.assertEqual(docker.call_count, 2)

    def test_rejects_same_project_with_a_foreign_container(self):
        docker = Mock(side_effect=[
            f"{self.container}\t{self.project}\t/foreign\trunning\n",
            f"{self.network}\t{self.project}\n",
        ])
        with self.assertRaisesRegex(ValueError, "disagree"):
            cleanup(docker, self.worktree)
        self.assertEqual(docker.call_count, 2)

    def test_rejects_network_without_a_container_to_confirm_ownership(self):
        docker = Mock(side_effect=["", f"{self.network}\t{self.project}\n"])
        with self.assertRaisesRegex(ValueError, "network ownership"):
            cleanup(docker, self.worktree)
        self.assertEqual(docker.call_count, 2)
