"""Check repository Markdown links and documentation index coverage."""

from __future__ import annotations

import os
import posixpath
import re
import string
import subprocess
import sys
from bisect import bisect_right
from collections.abc import Iterator
from html import unescape
from itertools import groupby
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

DESIGN_INDEX = PurePosixPath("docs/design-docs/index.md")
PRODUCT_INDEX = PurePosixPath("docs/product-specs/index.md")
DESIGN_DIRECTORY = PurePosixPath("docs/domains/game")
VERIFICATION_STATUSES = {"verified", "partially verified", "pending"}

DESTINATION = (
    r"<(?P<angle>(?:\\.|[^<>\n\\])+)>|(?P<bare>(?:\\.|[^()\s\\]|\([^()\s]*\))+)"
)
LINK_SPACE = r"[ \t]*(?:\n[ \t]*)?"
TITLE_LINE_BREAK = r"\n(?![ \t]*\n)"
TITLE = (
    rf"""(?:"(?:\\.|[^"\\\n]|{TITLE_LINE_BREAK})*"|"""
    rf"""'(?:\\.|[^'\\\n]|{TITLE_LINE_BREAK})*'|"""
    rf"\((?:\\.|[^()\\\n]|{TITLE_LINE_BREAK})*\))"
)
OPTIONAL_TITLE = rf"(?:(?=[ \t\n]){LINK_SPACE}{TITLE})?"
LINK = re.compile(
    r"(?<!\\)!?\[(?P<label>(?:\\.|[^\[\]\\\n]|\[[^\[\]\n]*\]|\n(?![ \t]*\n))*)\]\("
    + LINK_SPACE
    + rf"(?:{DESTINATION}){OPTIONAL_TITLE}{LINK_SPACE}\)"
)
REFERENCE = re.compile(
    rf"^[ ]{{0,3}}\[(?P<name>[^\]\n]+)\]:{LINK_SPACE}"
    rf"(?:{DESTINATION}){OPTIONAL_TITLE}[ \t]*$",
    re.MULTILINE,
)
REFERENCE_USE = re.compile(r"(?<!\\)(!?)\[([^\[\]\n]+)\](?:\[([^\[\]\n]*)\])?")
FENCE = re.compile(r"^ {0,3}(~{3,}|\x60{3,})(.*)$")
QUOTE = re.compile(r"^ {0,3}>[ \t]?")
INDENT = re.compile(r"^[ \t]*")
LIST_ITEM = re.compile(r"^ {0,3}(?:[-+*]|[0-9]{1,9}[.)]) {1,4}(?=\S)")
THEMATIC_BREAK = r"(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})(?=\n|$)"
INLINE_BOUNDARY = (
    r"(?: {0,3}>[ \t]?)*[ \t]*"
    rf"(?:\n|#{{1,6}}(?=[ \t\n]|$)|~{{3,}}|\x60{{3,}}|<!--|{THEMATIC_BREAK})"
)
INLINE_CODE = re.compile(
    # Backslashes escape in pairs. An unpaired one escapes the first backtick.
    r"(?<![\\\x60])(?:\\\\)*(?:\\\x60)?(?P<code_ticks>\x60+)(?!\x60)"
    rf"(?:[^\n]|\n(?!{INLINE_BOUNDARY}))*?"
    r"(?<!\x60)(?P=code_ticks)(?!\x60)"
)
DOCUMENT_LITERAL = re.compile(
    REFERENCE.pattern + "|" + INLINE_CODE.pattern, re.MULTILINE
)
COMMENT_OR_LITERAL = re.compile(
    r"(?P<comment><!--[\s\S]*?(?:-->|\Z))|" + DOCUMENT_LITERAL.pattern,
    re.MULTILINE,
)
BLOCK_COMMENT = re.compile(r"^ {0,3}<!--")
MARKDOWN_ESCAPE = re.compile(
    rf"\\([{re.escape(string.punctuation)}])|&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);"
)
HEADING = re.compile(r"^[ ]{0,3}#{1,6}[ \t]+(.+?)\s*#*\s*$")
ATX_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
SETEXT = re.compile(r"^[ ]{0,3}(?:=+|-+)[ \t]*$")
UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)(_+)(?=\S)(.+?)(?<=\S)\1(?!\w)")
ANCHOR = re.compile(r"""<a\s+[^>]*?\b(?:id|name)=["']([^"']+)["']""")


Container = tuple[int, tuple[int, ...]]
MarkdownLine = tuple[int, Container, str]


def within_container(container: Container, parent: Container) -> bool:
    depth, items = parent
    return container[0] >= depth and container[1][: len(items)] == items


def markdown_blocks(lines: list[MarkdownLine]) -> Iterator[list[MarkdownLine]]:
    def block_key(pair: tuple[int, MarkdownLine]) -> tuple[int, Container, int]:
        index, (number, container, line) = pair
        boundary = number if not line.strip() or ATX_HEADING.match(line) else 0
        return number - index, container, boundary

    for _, group in groupby(enumerate(lines), key=block_key):
        block: list[MarkdownLine] = []
        for _, line in group:
            block.append(line)
            if SETEXT.fullmatch(line[2]):
                yield block
                block = []
        if block:
            yield block


def markdown_lines(content: str) -> list[MarkdownLine]:
    """Keep source line numbers while skipping code blocks and comments."""
    lines = []
    fence = ""
    root: Container = (0, ())
    fence_container = comment_container = previous_container = root
    previous_depth = 0
    list_items: list[tuple[int, int]] = []
    in_comment = False
    in_paragraph = False
    for number, line in enumerate(content.splitlines(), 1):
        depth = 0
        block_container = fence_container if fence else comment_container
        while (not (fence or in_comment) or depth < block_container[0]) and (
            quote := QUOTE.match(line)
        ):
            depth += 1
            line = line[quote.end() :]
        if depth != previous_depth:
            list_items.clear()
            previous_depth = depth
        leading = INDENT.match(line)[0]
        indent = len(leading.expandtabs(4))
        line = " " * indent + line[len(leading) :]
        if line.strip():
            while list_items and indent < list_items[-1][0]:
                list_items.pop()
        margin = list_items[-1][0] if list_items else 0
        line = line[margin:]
        container = (depth, tuple(start for _, start in list_items))
        if container != previous_container:
            in_paragraph = False
        if not within_container(container, comment_container):
            in_comment = False
        if in_comment:
            in_comment = "-->" not in line
            continue

        if fence and within_container(container, fence_container):
            delimiter = FENCE.match(line)
            if (
                container == fence_container
                and delimiter
                and delimiter[1].startswith(fence)
                and not delimiter[2].strip()
            ):
                fence = ""
            continue
        fence = ""
        if item := LIST_ITEM.match(line):
            list_items.append((margin + item.end(), number))
            container = (depth, (*container[1], number))
            line = line[item.end() :]
            in_paragraph = False
        previous_container = container
        delimiter = FENCE.match(line)
        if delimiter and (delimiter[1].startswith("~") or "\x60" not in delimiter[2]):
            fence, fence_container = delimiter[1], container
            in_paragraph = False
            continue
        if not in_paragraph and line.startswith("    "):
            continue
        if BLOCK_COMMENT.match(line):
            comment_container = container
            in_comment = "-->" not in line
            in_paragraph = False
            continue
        lines.append((number, container, line))
        in_paragraph = bool(line.strip()) and not (
            ATX_HEADING.match(line) or SETEXT.fullmatch(line)
        )
    # Inline comments and code spans compete within the same block.
    cleaned: list[MarkdownLine] = []
    for block in markdown_blocks(lines):
        text = "\n".join(line for _, _, line in block)
        visible = COMMENT_OR_LITERAL.sub(
            lambda match: "\n" * match[0].count("\n") if match["comment"] else match[0],
            text,
        )
        cleaned.extend(
            (number, container, line)
            for (number, container, _), line in zip(block, visible.split("\n"))
        )
    return cleaned


def index_link_destinations(line: str) -> list[str]:
    text = INLINE_CODE.sub("", line)
    if REFERENCE.match(text):
        return []
    return [match["angle"] or match["bare"] for match in LINK.finditer(text)]


def mask_match(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match[0])


def reference_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def document_links(
    lines: list[MarkdownLine], *, include_definitions: bool = True
) -> Iterator[tuple[int, str]]:
    """Find links across visible lines while retaining source line numbers."""
    definitions: dict[str, str] = {}
    uses: list[tuple[int, str]] = []
    for block in markdown_blocks(lines):
        offsets = [0]
        for _, _, line in block:
            offsets.append(offsets[-1] + len(line) + 1)
        text = "\n".join(line for _, _, line in block)
        # Earlier code spans and definitions take precedence over text within them.
        references = [
            match for match in DOCUMENT_LITERAL.finditer(text) if match["name"]
        ]
        inline_text = DOCUMENT_LITERAL.sub(mask_match, text)
        matches = sorted(
            [*(references if include_definitions else []), *LINK.finditer(inline_text)],
            key=lambda match: match.start(),
        )
        for match in matches:
            number = block[bisect_right(offsets, match.start()) - 1][0]
            yield number, match["angle"] or match["bare"]
        if not include_definitions:
            for match in references:
                definitions.setdefault(
                    reference_label(match["name"]), match["angle"] or match["bare"]
                )
            reference_text = LINK.sub(mask_match, inline_text)
            for match in REFERENCE_USE.finditer(reference_text):
                if not match[1]:
                    label_group = 3 if match[3] else 2
                    number = block[bisect_right(offsets, match.start()) - 1][0]
                    label_start, label_end = match.span(label_group)
                    # Masking preserves offsets; recover the label from source text.
                    uses.append((number, reference_label(text[label_start:label_end])))
    for number, label in uses:
        if label in definitions:
            yield number, definitions[label]


def relative_target(
    source: PurePosixPath, destination: str
) -> tuple[PurePosixPath, str] | None:
    destination = MARKDOWN_ESCAPE.sub(
        lambda match: match[1] or unescape(match[0]), destination
    )
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


def heading_anchors(lines: list[MarkdownLine]) -> set[str]:
    slugs = set()
    custom_anchors = set()
    previous = ""
    previous_number = 0
    previous_container: Container | None = None
    for number, container, line in lines:
        heading = HEADING.match(line)
        text = ""
        if heading:
            text = heading[1]
        elif (
            container == previous_container
            and number == previous_number + 1
            and SETEXT.fullmatch(line)
        ):
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
        previous_container = container
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


def check_indexes(documents: dict[PurePosixPath, list[MarkdownLine]]) -> list[str]:
    errors = []
    index_directories = {
        DESIGN_INDEX: DESIGN_DIRECTORY,
        PRODUCT_INDEX: PRODUCT_INDEX.parent,
    }
    for index, directory in index_directories.items():
        if index not in documents:
            errors.append(f"{index}: missing documentation index")
            continue
        if index == DESIGN_INDEX:
            targets = []
            for number, _, line in documents[index]:
                if "|" not in line:
                    continue
                document, _, rest = line.strip().strip("|").partition("|")
                entries = index_link_destinations(document)
                status = rest.partition("|")[0].strip(" *_\x60").casefold()
                if entries and status not in VERIFICATION_STATUSES:
                    errors.append(
                        f"{index}:{number}: missing or invalid verification status "
                        f"for {entries[0]!r}"
                    )
                targets.extend(entries)
        else:
            targets = [
                target
                for _, target in document_links(
                    documents[index], include_definitions=False
                )
            ]
        indexed = {
            resolved[0]
            for target in targets
            if (resolved := relative_target(index, target))
        }
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
        for number, destination in document_links(lines):
            resolved = relative_target(source, destination)
            if resolved is None:
                continue
            target, fragment = resolved
            location = f"{source.as_posix()!r}:{number}"
            if target not in available and target not in directories:
                errors.append(f"{location}: broken relative link {destination!r}")
            elif fragment and target in anchors and fragment not in anchors[target]:
                errors.append(f"{location}: missing heading anchor in {destination!r}")

    errors.extend(check_indexes(documents))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Documentation checks passed for {len(documents)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
