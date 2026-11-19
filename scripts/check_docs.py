"""Check repository Markdown links and documentation index coverage."""

from __future__ import annotations

import os
import posixpath
import re
import subprocess
import sys
from html import unescape
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

DESIGN_INDEX = PurePosixPath("docs/design-docs/index.md")
PRODUCT_INDEX = PurePosixPath("docs/product-specs/index.md")
DESIGN_DIRECTORY = PurePosixPath("docs/domains/game")
VERIFICATION_STATUSES = {"verified", "partially verified", "pending"}

DESTINATION = r"<(?P<angle>[^>]+)>|(?P<bare>(?:\\.|[^()\s\\]|\([^()\s]*\))+)"
LINK = re.compile(
    r"(?<!\\)!?\[(?P<label>(?:\\.|[^\[\]\\]|\[[^\[\]]*\])*)\]\(\s*"
    r"(?:" + DESTINATION + r")(?=[\s)]).*?\)"
)
REFERENCE = re.compile(r"^[ ]{0,3}\[[^\]]+\]:\s*(?:" + DESTINATION + r")")
FENCE = re.compile(r"^\s*(~{3,}|\x60{3,})(.*)$")
INLINE_CODE = re.compile(r"(?<!\x60)(\x60+)(?!\x60).*?(?<!\x60)\1(?!\x60)")
COMMENT_START = re.compile(INLINE_CODE.pattern + r"|<!--")
HEADING = re.compile(r"^[ ]{0,3}#{1,6}[ \t]+(.+?)\s*#*\s*$")
SETEXT = re.compile(r"^[ ]{0,3}(?:=+|-+)[ \t]*$")
UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)(_+)(?=\S)(.+?)(?<=\S)\1(?!\w)")
ANCHOR = re.compile(r"""<a\s+[^>]*?\b(?:id|name)=["']([^"']+)["']""")


def markdown_lines(content: str) -> list[tuple[int, str]]:
    """Keep source line numbers while skipping fenced examples and comments."""
    lines = []
    fence = ""
    in_comment = False
    for number, line in enumerate(content.splitlines(), 1):
        delimiter = None if in_comment else FENCE.match(line)
        if fence:
            if (
                delimiter
                and delimiter[1].startswith(fence)
                and not delimiter[2].strip()
            ):
                fence = ""
        elif delimiter:
            fence = delimiter[1]
        else:
            visible, in_comment = strip_comments(line, in_comment)
            lines.append((number, visible))
    return lines


def strip_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    visible = []
    offset = 0
    while True:
        if in_comment:
            closing = line.find("-->", offset)
            if closing == -1:
                return "".join(visible), True
            offset = closing + 3
        opening = next(
            (
                match
                for match in COMMENT_START.finditer(line, offset)
                if match[0] == "<!--"
            ),
            None,
        )
        if opening is None:
            visible.append(line[offset:])
            return "".join(visible), False
        visible.append(line[offset : opening.start()])
        offset = opening.end()
        in_comment = True


def link_destinations(line: str, *, include_definitions: bool = True) -> list[str]:
    text = INLINE_CODE.sub("", line)
    reference = REFERENCE.match(text)
    if reference:
        return [reference["angle"] or reference["bare"]] if include_definitions else []
    matches = LINK.finditer(text)
    return [match["angle"] or match["bare"] for match in matches]


def relative_target(
    source: PurePosixPath, destination: str
) -> tuple[PurePosixPath, str] | None:
    if destination.startswith("//") or re.match(
        r"^[a-zA-Z][a-zA-Z0-9+.-]*:", destination
    ):
        return None
    path, _, fragment = destination.partition("#")
    path = unquote(path.partition("?")[0])
    if not path:
        return source, unquote(fragment)
    target = PurePosixPath(path[1:]) if path.startswith("/") else source.parent / path
    return PurePosixPath(posixpath.normpath(target)), unquote(fragment)


def heading_anchors(lines: list[tuple[int, str]]) -> set[str]:
    slugs = set()
    custom_anchors = set()
    previous = ""
    previous_number = 0
    for number, line in lines:
        heading = HEADING.match(line)
        text = ""
        if heading:
            text = heading[1]
        elif number == previous_number + 1 and SETEXT.fullmatch(line):
            text = previous
        if text:
            text = LINK.sub(r"\g<label>", text)
            text = UNDERSCORE_EMPHASIS.sub(r"\2", text)
            slug = re.sub(r"[^\w -]", "", unescape(text).strip().lower())
            slug = slug.replace(" ", "-")
            unique_slug = slug
            suffix = 1
            while unique_slug in slugs:
                unique_slug = f"{slug}-{suffix}"
                suffix += 1
            slugs.add(unique_slug)
        custom_anchors.update(ANCHOR.findall(INLINE_CODE.sub("", line)))
        previous = "" if text else line
        previous_number = number
    return slugs | custom_anchors


def tracked_files(root: Path) -> set[PurePosixPath]:
    listing = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
    files = set()
    for entry in listing.split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            if metadata.split()[0] in (b"100644", b"100755"):
                files.add(PurePosixPath(os.fsdecode(name)))
    return files


def check_indexes(
    documents: dict[PurePosixPath, list[tuple[int, str]]],
) -> list[str]:
    errors = []
    index_directories = {
        DESIGN_INDEX: DESIGN_DIRECTORY,
        PRODUCT_INDEX: PRODUCT_INDEX.parent,
    }
    for index, directory in index_directories.items():
        if index not in documents:
            errors.append(f"{index}: missing documentation index")
            continue
        indexed = set()
        for number, line in documents[index]:
            if index == DESIGN_INDEX:
                if "|" not in line:
                    continue
                document, _, rest = line.strip().strip("|").partition("|")
                targets = link_destinations(document, include_definitions=False)
                status = rest.partition("|")[0].strip(" *_\x60").casefold()
                if targets and status not in VERIFICATION_STATUSES:
                    errors.append(
                        f"{index}:{number}: missing or invalid verification status "
                        f"for {targets[0]!r}"
                    )
            else:
                targets = link_destinations(line, include_definitions=False)
            for target in targets:
                resolved = relative_target(index, target)
                if resolved:
                    indexed.add(resolved[0])

        expected = {
            path
            for path in documents
            if path != index and path.is_relative_to(directory)
        }
        for path in sorted(expected - indexed):
            errors.append(f"{index}: missing index entry for {path.as_posix()!r}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    files = tracked_files(root)
    available = set()
    for path in files:
        candidate = root / path
        if candidate.is_file() and candidate.resolve() == candidate:
            available.add(path)
    directories = {parent for path in available for parent in path.parents}
    documents = {}
    errors = []
    for path in sorted(files):
        if path.suffix.lower() == ".md":
            if path not in available:
                errors.append(
                    f"{path.as_posix()!r}: tracked Markdown file is unavailable"
                )
                continue
            try:
                documents[path] = markdown_lines(
                    (root / path).read_text(encoding="utf-8")
                )
            except UnicodeDecodeError:
                errors.append(f"{path.as_posix()!r}: Markdown must be UTF-8")

    anchors = {path: heading_anchors(lines) for path, lines in documents.items()}
    for source, lines in documents.items():
        for number, line in lines:
            for destination in link_destinations(line):
                resolved = relative_target(source, destination)
                if resolved is None:
                    continue
                target, fragment = resolved
                location = f"{source.as_posix()!r}:{number}"
                if target not in available and target not in directories:
                    errors.append(f"{location}: broken relative link {destination!r}")
                elif fragment and target in anchors and fragment not in anchors[target]:
                    errors.append(
                        f"{location}: missing heading anchor in {destination!r}"
                    )

    errors.extend(check_indexes(documents))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Documentation checks passed for {len(documents)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
