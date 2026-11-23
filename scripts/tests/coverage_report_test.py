"""Check the report validation and summary used in CI."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "check-coverage-report.sh"
SUMMARIZER = CHECKER.with_name("summarize_coverage.py")


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


class CoverageSummaryTest(unittest.TestCase):
    def test_reports_percentage_and_line_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "coverage.xml"
            report.write_text(
                '<coverage lines-covered="254" lines-valid="259" />',
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SUMMARIZER), str(report)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout,
                "### Python line coverage\n\n"
                "**98.07%** (254 of 259 executable lines covered)\n",
            )

    def test_rejects_an_invalid_report_without_printing_a_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "coverage.xml"
            for xml in ("<coverage>", '<coverage lines-covered="4" lines-valid="3" />'):
                with self.subTest(xml=xml):
                    report.write_text(xml, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(SUMMARIZER), str(report)],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(f"coverage report {report}", result.stderr)
                    self.assertEqual(result.stdout, "")
