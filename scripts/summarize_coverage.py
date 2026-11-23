"""Print the overall Python line coverage as Markdown."""

import argparse
from pathlib import Path
from xml.etree import ElementTree


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    report = parser.parse_args().report

    try:
        root = ElementTree.parse(report).getroot()
        covered = int(root.attrib["lines-covered"])
        total = int(root.attrib["lines-valid"])
    except (OSError, ElementTree.ParseError, KeyError, ValueError):
        parser.exit(1, f"Cannot read line counts from coverage report {report}.\n")

    if root.tag != "coverage" or not 0 <= covered <= total or total == 0:
        parser.exit(1, f"Invalid line counts in coverage report {report}.\n")

    print("### Python line coverage\n")
    print(f"**{covered / total:.2%}** ({covered:,} of {total:,} executable lines covered)")


if __name__ == "__main__":
    main()
