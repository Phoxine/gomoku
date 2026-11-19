"""Regression tests for documentation checker Markdown parsing."""

import unittest
from pathlib import PurePosixPath

from scripts.check_docs import (
    DESIGN_INDEX,
    PRODUCT_INDEX,
    check_indexes,
    document_links,
    markdown_lines,
    relative_target,
)


class MarkdownLinksTest(unittest.TestCase):
    def test_indented_code_does_not_open_or_close_a_fence(self) -> None:
        markdown = (
            "    \x60\x60\x60\n    [ignored](code.md)\n\n"
            "~~~~\n    ~~~~\n~~~\n\x60\x60\x60\x60\n[ignored](fence.md)\n~~~~\n"
            "[checked](real.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(10, "real.md")]
        )

    def test_quoted_fences_skip_examples_and_end_with_their_quote(self) -> None:
        markdown = (
            "> > ~~~\n> > [ignored](code.md)\n> > ~~~\n"
            "> [checked](quoted.md)\n"
            "> ~~~\n> [ignored](unclosed.md)\n"
            "[checked](outside.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [(4, "quoted.md"), (7, "outside.md")],
        )

    def test_list_fences_use_the_item_indentation(self) -> None:
        markdown = (
            "- Example\n    ~~~\n    [ignored](code.md)\n    ~~~\n"
            "- [checked](real.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(5, "real.md")]
        )

    def test_quote_markers_inside_list_fences_are_literal(self) -> None:
        markdown = (
            "- Example\n  ~~~\n  > [ignored](code.md)\n  ~~~\n  [checked](real.md)\n"
        )
        for prefix in ("", "> "):
            with self.subTest(prefix=prefix):
                content = "\n".join(prefix + line for line in markdown.splitlines())
                self.assertEqual(
                    list(document_links(markdown_lines(content))), [(5, "real.md")]
                )

    def test_destinations_decode_markdown_escapes_and_entities(self) -> None:
        source = PurePosixPath("docs/index.md")
        cases = {
            r"guide\(v2\).md": "docs/guide(v2).md",
            "some%20guide&amp;notes.md": "docs/some guide&notes.md",
            r"guide\version.md": r"docs/guide\version.md",
            r"guide\&amp;.md": "docs/guide&amp;.md",
        }
        for destination, path in cases.items():
            with self.subTest(destination=destination):
                self.assertEqual(
                    relative_target(source, destination), (PurePosixPath(path), "")
                )

    def test_multiline_destinations_preserve_starting_lines(self) -> None:
        markdown = (
            "# Guide\n\n[rules]:\n    missing.md\n\n"
            '[An inline\nlink](\n    another.md\n    "Title (with parentheses)"\n)\n\n'
            "[A separate paragraph](\n\nnot-a-link.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [(3, "missing.md"), (6, "another.md")],
        )

    def test_multiline_destinations_do_not_cross_quote_boundaries(self) -> None:
        markdown = "[Not a link](\n> quote.md)\n\n> [Check](\n> valid.md)\n"
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(4, "valid.md")]
        )

    def test_index_checks_count_multiline_entries_and_report_omissions(self) -> None:
        product = PRODUCT_INDEX.parent / "local.md"
        design = PurePosixPath("docs/domains/game/design.md")
        documents = {
            DESIGN_INDEX: markdown_lines(
                "| [Design](/docs/domains/game/design.md) ||\n"
            ),
            PRODUCT_INDEX: markdown_lines("- [Local](\n    local.md\n  )\n"),
            product: markdown_lines("# Local"),
            design: markdown_lines("# Design"),
        }
        errors = check_indexes(documents)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing or invalid verification status", errors[0])
        documents[PRODUCT_INDEX] = markdown_lines("[local]: local.md\n")
        self.assertIn(
            "docs/product-specs/index.md: missing index entry for "
            "'docs/product-specs/local.md'",
            check_indexes(documents),
        )
