from pathlib import Path

from wiki2md.document import Document, HeadingBlock, ImageBlock, ListBlock, ParagraphBlock
from wiki2md.models import FetchedArticle, UrlResolution
from wiki2md.normalize import normalize_article

FIXTURE = Path(__file__).parent / "fixtures" / "html" / "person_fragment.html"
FIXTURE_ZH = Path(__file__).parent / "fixtures" / "html" / "person_fragment_zh.html"


def test_normalize_article_extracts_summary_blocks_images_and_references() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
            normalized_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
            lang="en",
            title="Andrej_Karpathy",
            slug="andrej-karpathy",
        ),
        canonical_title="Andrej Karpathy",
        pageid=12345,
        revid=67890,
        html=FIXTURE.read_text(encoding="utf-8"),
        media=[],
    )

    document = normalize_article(article)

    assert isinstance(document, Document)
    assert document.title == "Andrej Karpathy"
    assert document.summary == ["Andrej Karpathy is a Slovak-Canadian computer scientist.[1]"]
    assert document.references == ["Reference number one."]
    assert any(isinstance(block, ImageBlock) and block.role == "infobox" for block in document.blocks)
    assert any(isinstance(block, HeadingBlock) and block.text == "Career" for block in document.blocks)
    assert any(isinstance(block, ParagraphBlock) and "Tesla" in block.text for block in document.blocks)
    assert any(isinstance(block, ListBlock) and block.items == ["OpenAI", "Tesla"] for block in document.blocks)


def test_normalize_article_preserves_chinese_text() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://zh.wikipedia.org/wiki/%E8%89%BE%E4%BC%A6%C2%B7%E5%9B%BE%E7%81%B5",
            normalized_url="https://zh.wikipedia.org/wiki/%E8%89%BE%E4%BC%A6%C2%B7%E5%9B%BE%E7%81%B5",
            lang="zh",
            title="艾伦·图灵",
            slug="艾伦-图灵",
        ),
        canonical_title="艾伦·图灵",
        pageid=22345,
        revid=77890,
        html=FIXTURE_ZH.read_text(encoding="utf-8"),
        media=[],
    )

    document = normalize_article(article)

    assert document.title == "艾伦·图灵"
    assert document.summary == ["艾伦·图灵 是英国数学家、计算机科学先驱。"]
    assert any(isinstance(block, HeadingBlock) and block.text == "生平" for block in document.blocks)
    assert any(isinstance(block, ParagraphBlock) and "密码分析" in block.text for block in document.blocks)
