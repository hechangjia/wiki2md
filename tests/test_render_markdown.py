from datetime import UTC, datetime

from wiki2md.document import Document, HeadingBlock, ImageBlock, ListBlock, ParagraphBlock
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
            ListBlock(ordered=False, items=["OpenAI", "Tesla"]),
        ],
        references=["Reference number one."],
    )

    markdown = render_markdown(
        document,
        build_metadata(),
        {"File:Andrej_Karpathy_2024.jpg": "assets/001-infobox.jpg"},
    )

    assert markdown.startswith("---\n")
    assert "source_url: https://en.wikipedia.org/wiki/Andrej_Karpathy" in markdown
    assert "# Andrej Karpathy" in markdown
    assert "![Andrej Karpathy portrait](./assets/001-infobox.jpg)" in markdown
    assert "Karpathy in 2024" in markdown
    assert "## Career" in markdown
    assert "- OpenAI" in markdown
    assert "## References" in markdown
    assert "1. Reference number one." in markdown


def test_render_markdown_compresses_long_reference_lists() -> None:
    document = Document(
        title="Andrej Karpathy",
        summary=["Andrej Karpathy is a computer scientist."],
        references=[f"Reference {index}" for index in range(1, 8)],
    )

    markdown = render_markdown(document, build_metadata(), {})

    assert "1. Reference 1" in markdown
    assert "5. Reference 5" in markdown
    assert "_2 additional reference(s) omitted for brevity._" in markdown
