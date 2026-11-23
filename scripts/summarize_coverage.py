"""Print Python line coverage as Markdown and optionally enforce a minimum."""

import argparse
from pathlib import Path
from xml.etree import ElementTree


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--fail-under", type=int, help="minimum line coverage percent")
    args = parser.parse_args()
    report = args.report
    minimum = args.fail_under
    if minimum is not None and not 0 <= minimum <= 100:
        parser.error("--fail-under must be between 0 and 100")

    try:
        root = ElementTree.parse(report).getroot()
        covered = int(root.attrib["lines-covered"])
        total = int(root.attrib["lines-valid"])
    except (OSError, ElementTree.ParseError, KeyError, ValueError) as error:
        parser.exit(
            1,
            f"Cannot read line counts from coverage report {report} "
            f"({type(error).__name__}).\n",
        )

    if root.tag != "coverage" or not 0 <= covered <= total or total == 0:
        parser.exit(1, f"Invalid line counts in coverage report {report}.\n")

    print("### Python line coverage\n")
    print(
        f"**{covered / total:.2%}** ({covered:,} of {total:,} executable lines covered)"
    )
    if minimum is not None:
        below_minimum = covered * 100 < total * minimum
        status = "fail" if below_minimum else "pass"
        print(f"\nRequired minimum: **{minimum}%** ({status}).")
        if below_minimum:
            parser.exit(1, f"Python line coverage is below the {minimum}% minimum.\n")


if __name__ == "__main__":
    main()
