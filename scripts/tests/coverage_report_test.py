"""Check the report validation used before CI artifact upload."""

import subprocess
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "check-coverage-report.sh"


class CoverageReportTest(unittest.TestCase):
    def test_accepts_nonempty_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "coverage.xml"
            report.write_text("<coverage />\n", encoding="utf-8")
            result = subprocess.run(
                ["bash", str(CHECKER), str(report)], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_missing_or_empty_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "coverage.xml"
            for exists in (False, True):
                with self.subTest(exists=exists):
                    if exists:
                        report.touch()
                    result = subprocess.run(
                        ["bash", str(CHECKER), str(report)],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        f"Coverage report is missing or empty at {report}", result.stderr
                    )
