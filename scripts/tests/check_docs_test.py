"""Regression tests for documentation checker Markdown parsing."""

import unittest
from pathlib import PurePosixPath

from scripts.check_docs import (
    DESIGN_INDEX,
    PRODUCT_INDEX,
    check_indexes,
    document_links,
    heading_anchors,
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

    def test_reference_titles_do_not_create_links(self) -> None:
        markdown = (
            '[first]: real.md "[Example](missing.md)"\n'
            '[second]: another.md\n  "[Example](also-missing.md)"\n\n'
            '[third]: third.md "a \x60 and a soft line\n[Example](ignored.md)"\n'
            "[Valid](with-code.md) \x60literal\x60\n"
            "[Valid](outside.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [
                (1, "real.md"),
                (2, "another.md"),
                (5, "third.md"),
                (7, "with-code.md"),
                (8, "outside.md"),
            ],
        )

    def test_multiline_code_masks_links_within_the_paragraph(self) -> None:
        markdown = (
            "\x60example\n[ignored](missing.md)\x60 [Valid](first.md)\n\n"
            "\x60unclosed\n\n[Valid](second.md)\x60\n\n"
            "\x60unclosed\n# [Heading](heading.md) with \x60code\x60\n\n"
            "\x60example\nliteral <!--\x60 [Valid](third.md)\n[Valid](fourth.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [
                (2, "first.md"),
                (6, "second.md"),
                (9, "heading.md"),
                (12, "third.md"),
                (13, "fourth.md"),
            ],
        )

    def test_multiline_code_protection_respects_other_blocks(self) -> None:
        cases = (
            ("> ~~~\n> \x60unclosed\n> ~~~\n", (5, "valid.md")),
            ("<!--\n\x60unclosed\n-->\n", (5, "valid.md")),
            ("\x60unclosed\n***\n", (4, "valid.md")),
        )
        for prefix, link in cases:
            with self.subTest(prefix=prefix):
                markdown = (
                    prefix
                    + "outside <!-- [Ignored](missing.md) \x60 -->\n"
                    + "[Visible](valid.md) with \x60code\x60\n"
                )
                self.assertEqual(list(document_links(markdown_lines(markdown))), [link])

    def test_escaped_backtick_does_not_open_code_span(self) -> None:
        markdown = "\\\x60literal\n[Visible](missing.md)\x60\n"
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(2, "missing.md")]
        )

    def test_even_backslashes_allow_code_span_openers(self) -> None:
        markdown = "\\\\\x60[Ignored](missing.md)\\\x60 [Visible](real.md)\n"
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(1, "real.md")]
        )

    def test_code_span_stops_at_heading_boundary(self) -> None:
        markdown = "# \x60literal\n[Visible](missing.md)\x60\n"
        for prefix in ("", "> ", "- "):
            with self.subTest(prefix=prefix):
                continuation = "  " if prefix == "- " else prefix
                heading, paragraph = markdown.splitlines()
                content = f"{prefix}{heading}\n{continuation}{paragraph}\n"
                self.assertEqual(
                    list(document_links(markdown_lines(content))), [(2, "missing.md")]
                )

    def test_comment_boundaries_follow_markdown_container(self) -> None:
        markdown = (
            "> <!-- unclosed\n"
            "`example\n"
            "literal <!--` [Visible](real.md)\n"
            "[Visible](next.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [(3, "real.md"), (4, "next.md")],
        )

    def test_reference_labels_are_resolved_from_original_text(self) -> None:
        markdown = (
            "[`Local`] [Label][`Local`] [`Local`][]\n\n"
            "`[\x60\x60Local\x60\x60]`\n\n"
            "[`Local`]: local.md\n[\x60\x60Local\x60\x60]: unused.md\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown), include_definitions=False)),
            [(1, "local.md"), (1, "local.md"), (1, "local.md")],
        )

    def test_fences_inside_html_comments_do_not_hide_later_links(self) -> None:
        markdown = "<!--\n~~~\n[Ignored](missing.md)\n-->\n[Visible](real.md)\n"
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(5, "real.md")]
        )

    def test_list_comment_content_does_not_start_markdown_blocks(self) -> None:
        markdown = (
            "- <!--\n  > [Ignored](missing.md)\n  ~~~\n  -->\n  [Visible](real.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(5, "real.md")]
        )

    def test_inline_comments_do_not_change_heading_anchor_spacing(self) -> None:
        self.assertEqual(heading_anchors(markdown_lines("# A<!--note-->B\n")), {"ab"})

    def test_unclosed_inline_comment_does_not_hide_links(self) -> None:
        markdown = "text <!-- [Visible](real.md)\n"
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(1, "real.md")]
        )

    def test_inline_comments_cannot_cross_thematic_breaks(self) -> None:
        markdown = "text <!-- [Visible](first.md)\n***\n[Visible](second.md) -->\n"
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [(1, "first.md"), (3, "second.md")],
        )

    def test_inline_comment_openers_respect_backslash_parity(self) -> None:
        markdown = (
            "text \\<!-- [Visible](first.md) -->\n"
            "text \\\\<!-- [Ignored](missing.md) --> [Visible](second.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [(1, "first.md"), (2, "second.md")],
        )

    def test_inline_comments_do_not_create_links(self) -> None:
        markdown = (
            "[Example]<!--note-->(first.md)\n"
            "[Example](<!--note-->second.md)\n"
            "[Example](docs/<!--note-->third.md)\n"
            "[Example <!-- [Ignored](missing.md) --> continued](real.md)\n"
            "[Example](<!--note-->)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [(3, "docs/<!--note-->third.md"), (4, "real.md"), (5, "!--note--")],
        )
        self.assertEqual(
            heading_anchors(markdown_lines("# [Example]<!--note-->(first.md)\n")),
            {"examplefirstmd"},
        )

    def test_short_inline_comments_do_not_hide_following_links(self) -> None:
        for comment in ("<!-->", "<!--->"):
            with self.subTest(comment=comment):
                markdown = f"text {comment} [Visible](real.md) <!-- ordinary -->\n"
                self.assertEqual(
                    list(document_links(markdown_lines(markdown))), [(1, "real.md")]
                )

    def test_comment_like_destination_requires_visible_link_label(self) -> None:
        markdown = (
            "\x60[\x60label](<!--[Ignored](missing.md)-->) [Visible](first.md)\n"
            "[Example <!-- ] --> label](docs/<!--note-->second.md)\n"
        )
        self.assertEqual(
            list(document_links(markdown_lines(markdown))),
            [(1, "first.md"), (2, "docs/<!--note-->second.md")],
        )

    def test_code_span_stops_after_setext_heading(self) -> None:
        markdown = "\x60heading\n===\n[Visible](real.md)\x60\n"
        self.assertEqual(
            list(document_links(markdown_lines(markdown))), [(3, "real.md")]
        )
        markdown = "\x60heading\n[Ignored](missing.md)\x60\n===\n"
        self.assertEqual(list(document_links(markdown_lines(markdown))), [])

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
        for reference_link in ("[Local name][local]", "[Local][]", "[Local]"):
            with self.subTest(reference_link=reference_link):
                documents[PRODUCT_INDEX] = markdown_lines(
                    f"- {reference_link}\n\n[local]: local.md\n"
                )
                self.assertEqual(check_indexes(documents), errors)
        for unused_reference in ("", "![Local image][local]\n\n"):
            with self.subTest(unused_reference=unused_reference):
                documents[PRODUCT_INDEX] = markdown_lines(
                    f"{unused_reference}[local]: local.md\n"
                )
                self.assertIn(
                    "docs/product-specs/index.md: missing index entry for "
                    "'docs/product-specs/local.md'",
                    check_indexes(documents),
                )
