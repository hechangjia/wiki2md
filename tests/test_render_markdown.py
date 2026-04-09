from datetime import UTC, datetime

from wiki2md.document import (
    Document,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ListItem,
    ParagraphBlock,
    ReferenceEntry,
)
from wiki2md.models import ArticleMetadata
from wiki2md.render_markdown import render_markdown


def build_metadata() -> ArticleMetadata:
    return ArticleMetadata(
        title="Andrej Karpathy",
        source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        source_lang="en",
        retrieved_at=datetime(2026, 4, 8, tzinfo=UTC),
        pageid=12345,
        revid=67890,
    )


def test_render_markdown_outputs_frontmatter_body_and_references() -> None:
    document = Document(
        title="Andrej Karpathy",
        summary=["Andrej Karpathy is a computer scientist.[1]"],
        blocks=[
            ImageBlock(
                title="File:Andrej_Karpathy_2024.jpg",
                alt="Andrej Karpathy portrait",
                caption="Karpathy in 2024",
                role="infobox",
            ),
            HeadingBlock(level=2, text="Career"),
            ParagraphBlock(text="Karpathy worked at OpenAI and Tesla."),
            ListBlock(
                ordered=False,
                items=[ListItem(text="OpenAI"), ListItem(text="Tesla")],
            ),
        ],
        references=[ReferenceEntry(text="Reference number one.")],
    )

    markdown = render_markdown(
        document,
        build_metadata(),
        {"File:Andrej_Karpathy_2024.jpg": "assets/001-infobox.jpg"},
    )

    expected_markdown = "\n".join(
        [
            "---",
            "title: Andrej Karpathy",
            "source_url: https://en.wikipedia.org/wiki/Andrej_Karpathy",
            "source_lang: en",
            "source_type: wikipedia",
            "retrieved_at: '2026-04-08T00:00:00+00:00'",
            "page_type: person",
            "pageid: 12345",
            "revid: 67890",
            "---",
            "",
            "# Andrej Karpathy",
            "",
            "Andrej Karpathy is a computer scientist.[1]",
            "",
            "![Andrej Karpathy portrait](./assets/001-infobox.jpg)",
            "*Karpathy in 2024*",
            "",
            "## Career",
            "",
            "Karpathy worked at OpenAI and Tesla.",
            "",
            "- OpenAI",
            "- Tesla",
            "",
            "## References",
            "",
            "1. Reference number one.",
        ]
    )

    assert markdown == f"{expected_markdown}\n"


def test_render_markdown_compresses_long_reference_lists() -> None:
    document = Document(
        title="Andrej Karpathy",
        summary=["Andrej Karpathy is a computer scientist."],
        references=[ReferenceEntry(text=f"Reference {index}") for index in range(1, 8)],
    )

    markdown = render_markdown(document, build_metadata(), {})

    assert "1. Reference 1" in markdown
    assert "5. Reference 5" in markdown
    assert "Reference 6" not in markdown
    assert "Reference 7" not in markdown
    assert "5. Reference 5\n\n_2 additional reference(s) omitted for brevity._" in markdown
    assert markdown.endswith("\n")


def test_render_markdown_renders_markdown_links_for_link_aware_lists() -> None:
    document = Document(
        title="Geoffrey Hinton",
        summary=["Geoffrey Hinton is a computer scientist."],
        blocks=[
            HeadingBlock(level=2, text="External links"),
            ListBlock(
                ordered=False,
                items=[
                    ListItem(
                        text="Geoffrey Hinton on INSPIRE-HEP",
                        href="https://inspirehep.net/author/profile/Geoffrey.E.Hinton.1",
                    )
                ],
            ),
        ],
    )

    markdown = render_markdown(document, build_metadata(), {})

    expected = (
        "- [Geoffrey Hinton on INSPIRE-HEP]"
        "(https://inspirehep.net/author/profile/Geoffrey.E.Hinton.1)"
    )
    assert expected in markdown
