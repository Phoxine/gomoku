"""Regression checks for worktree isolation; Compose config needs no daemon."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCKER = shutil.which("docker")


class WorktreeEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Example.Repo_"
        self.root.mkdir()
        shutil.copytree(
            REPO / "scripts",
            self.root / "scripts",
            ignore=shutil.ignore_patterns("tests"),
        )
        shutil.copytree(REPO / ".codex/hooks", self.root / ".codex/hooks")
        (self.root / "src").mkdir()
        (self.root / "src/.env.example").write_text("DEBUG=True\n")
        shutil.copy(REPO / "compose.yaml", self.root / "compose.yaml")
        self.env = os.environ.copy()
        self.env.pop("COMPOSE_PROJECT_NAME", None)
        self.env.pop("POSTGRES_PASSWORD", None)
        self.env["REAL_DOCKER"] = DOCKER
        self.env["CALL_LOG"] = str(Path(self.temp.name) / "calls")
        bin_dir = Path(self.temp.name) / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text("""#!/usr/bin/env python3
import os, subprocess, sys
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(repr(args) + "\\n")
if args[:2] == ["volume", "ls"]:
    project = os.environ.get("VOLUME_PROJECT", "!")
    if "label=com.docker.compose.project=" + project in args:
        print("synthetic_postgres_data")
    sys.exit(0)
if "config" in args:
    sys.exit(subprocess.call([os.environ["REAL_DOCKER"], *args]))
if "ps" in args:
    if os.environ.get("PROBE_FAIL"):
        sys.exit(1)
    print(os.environ.get("SERVICES", ""))
    sys.exit(0)
if "exec" in args:
    sys.exit(int(os.environ.get("EXEC_FAIL", "0")))
sys.exit(99)
""")
        docker.chmod(0o755)
        self.env["PATH"] = str(bin_dir) + os.pathsep + self.env["PATH"]
        self.run_command("git", "init", "-b", "infra/original")

    def run_command(self, *args, ok=True):
        result = subprocess.run(
            args, cwd=self.root, env=self.env, text=True, capture_output=True
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def script(self, name, *args, ok=True):
        return self.run_command("bash", str(self.root / name), *args, ok=ok)

    def write_env(self, text):
        (self.root / ".env").write_text(text)

    def project(self):
        return self.script("scripts/worktree-project-name.sh").stdout.strip()

    def test_absent_and_blank_project_do_not_use_directory_default(self):
        for text in [
            "POSTGRES_PASSWORD=synthetic\n",
            "COMPOSE_PROJECT_NAME=\n",
            'COMPOSE_PROJECT_NAME=""\n',
        ]:
            with self.subTest(text=text):
                self.write_env(text)
                self.assertEqual(
                    self.script("scripts/resolve-compose-project-name.sh").stdout, ""
                )
                self.script(".codex/hooks/stop-validation.sh")
        self.assertFalse(Path(self.env["CALL_LOG"]).exists())

    def test_initializer_accepts_missing_name_and_preserves_password(self):
        self.write_env("POSTGRES_PASSWORD=synthetic\n")
        self.script("scripts/init-worktree-env.sh")
        self.assertIn("POSTGRES_PASSWORD=synthetic", (self.root / ".env").read_text())
        self.assertIn("COMPOSE_PROJECT_NAME=gomoku_", (self.root / ".env").read_text())

    def test_multiline_quotes_ignore_embedded_assignments(self):
        for quote in ["'", '"']:
            with self.subTest(quote=quote):
                text = (
                    f"OTHER={quote}first\nCOMPOSE_PROJECT_NAME=foreign\n"
                    f"POSTGRES_PASSWORD=embedded\nlast{quote}\n"
                )
                self.write_env(text)
                self.assertEqual(
                    self.script("scripts/resolve-compose-project-name.sh").stdout, ""
                )
                self.write_env(text + "COMPOSE_PROJECT_NAME=actual\n")
                self.assertEqual(
                    self.script(
                        "scripts/resolve-compose-project-name.sh"
                    ).stdout.strip(),
                    "actual",
                )
                self.write_env(text)
                self.script("scripts/init-worktree-env.sh")
                self.assertTrue((self.root / ".env").read_text().startswith(text))

    def test_branch_rename_retains_owned_project_and_runs_hook_checks(self):
        project = self.project()
        self.write_env(f"COMPOSE_PROJECT_NAME={project}\nPOSTGRES_PASSWORD=synthetic\n")
        self.run_command("git", "branch", "-m", "infra/renamed")
        self.assertEqual(self.project(), project)
        self.env["SERVICES"] = "app"
        self.script(".codex/hooks/stop-validation.sh")
        calls = Path(self.env["CALL_LOG"]).read_text()
        self.assertIn("'ruff', 'format'", calls)
        self.assertIn("'ruff', 'check'", calls)
        self.assertIn("'pytest'", calls)
        self.env["EXEC_FAIL"] = "1"
        self.assertEqual(
            self.script(".codex/hooks/stop-validation.sh", ok=False).returncode, 2
        )

    def test_foreign_hash_is_not_owned(self):
        self.write_env(
            "COMPOSE_PROJECT_NAME=gomoku_foreign_0000000000000000\n"
            "POSTGRES_PASSWORD=synthetic\n"
        )
        self.assertNotEqual(self.project(), "gomoku_foreign_0000000000000000")
        self.assertNotEqual(
            self.script("scripts/init-worktree-env.sh", ok=False).returncode, 0
        )

    def test_probe_failure_blocks_but_stopped_app_skips(self):
        self.write_env(
            f"COMPOSE_PROJECT_NAME={self.project()}\nPOSTGRES_PASSWORD=synthetic\n"
        )
        self.script(".codex/hooks/stop-validation.sh")
        self.env["PROBE_FAIL"] = "1"
        self.assertEqual(
            self.script(".codex/hooks/stop-validation.sh", ok=False).returncode, 2
        )

    def test_password_reference_keeps_project_variable(self):
        project = self.project()
        original = (
            f"COMPOSE_PROJECT_NAME={project}\n"
            "POSTGRES_PASSWORD=${COMPOSE_PROJECT_NAME}\n"
        )
        self.write_env(original)
        self.env["VOLUME_PROJECT"] = project
        self.script("scripts/init-worktree-env.sh")
        self.assertEqual((self.root / ".env").read_text(), original)

    def test_existing_selected_or_default_volume_requires_password(self):
        project = self.project()
        for volume_project in [project, "examplerepo_"]:
            with self.subTest(project=volume_project):
                original = f"COMPOSE_PROJECT_NAME={volume_project}\n"
                self.write_env(original)
                self.env["VOLUME_PROJECT"] = volume_project
                result = self.script("scripts/init-worktree-env.sh", ok=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Restore the original password", result.stderr)
                self.assertEqual((self.root / ".env").read_text(), original)

    def test_directory_normalization_matches_compose(self):
        self.assertEqual(
            self.script("scripts/worktree-project-name.sh", "directory").stdout.strip(),
            "examplerepo_",
        )
        result = self.run_command(
            DOCKER,
            "compose",
            "--project-directory",
            str(self.root),
            "--env-file",
            "/dev/null",
            "-f",
            str(self.root / "scripts/compose-env-probe.yaml"),
            "config",
            "--format",
            "json",
        )
        self.assertEqual(json.loads(result.stdout)["name"], "examplerepo_")


if __name__ == "__main__":
    unittest.main()
