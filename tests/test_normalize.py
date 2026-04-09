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
    assert document.summary == [
        "Andrej Karpathy is a Slovak-Canadian computer scientist.[note 1]",
        "He cofounded Eureka Labs and writes about neural networks.",
    ]
    assert document.references == [
        "Reference number one.",
        "Reference number two in paragraph form.",
    ]
    assert [block.kind for block in document.blocks] == ["image", "heading", "paragraph", "list"]

    image_block = document.blocks[0]
    assert isinstance(image_block, ImageBlock)
    assert image_block.title == "File:Andrej_Karpathy_2024.jpg"
    assert image_block.alt == "Andrej Karpathy portrait"
    assert image_block.caption == "Karpathy in 2024"
    assert image_block.role == "infobox"

    heading_block = document.blocks[1]
    assert isinstance(heading_block, HeadingBlock)
    assert heading_block.level == 2
    assert heading_block.text == "Career"

    paragraph_block = document.blocks[2]
    assert isinstance(paragraph_block, ParagraphBlock)
    assert paragraph_block.text == "Karpathy worked at OpenAI and Tesla."

    list_block = document.blocks[3]
    assert isinstance(list_block, ListBlock)
    assert list_block.ordered is False
    assert list_block.items == ["OpenAI", "Tesla"]
    assert all(
        not (isinstance(block, HeadingBlock) and block.text == "References")
        for block in document.blocks
    )
    assert "Reference number two in paragraph form." not in " ".join(document.summary)
    assert all(
        not (
            isinstance(block, ParagraphBlock)
            and block.text == "Reference number two in paragraph form."
        )
        for block in document.blocks
    )


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
    assert document.summary == ["艾伦·图灵是英国数学家、计算机科学先驱。[1]"]
    assert document.references == ["图灵传记资料。"]
    assert [block.kind for block in document.blocks] == ["heading", "paragraph"]

    heading_block = document.blocks[0]
    assert isinstance(heading_block, HeadingBlock)
    assert heading_block.text == "生平"

    paragraph_block = document.blocks[1]
    assert isinstance(paragraph_block, ParagraphBlock)
    assert paragraph_block.text == "图灵在第二次世界大战期间参与密码分析工作。"
    assert all(
        not (isinstance(block, HeadingBlock) and block.text == "参考文献")
        for block in document.blocks
    )


def test_normalize_article_uses_canonical_title_when_parsoid_html_has_no_h1() -> None:
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
        html="""
        <html>
          <head><title>Andrej Karpathy</title></head>
          <body>
            <section data-mw-section-id="0">
              <table class="infobox">
                <tr>
                  <td class="infobox-image">
                    <a class="mw-file-description" href="./File:Andrej_Karpathy,_OpenAI.png">
                      <img src="//upload.wikimedia.org/example/andrej-karpathy.png" />
                    </a>
                    <div class="infobox-caption">Karpathy at Stanford in 2016</div>
                  </td>
                </tr>
              </table>
              <p>Andrej Karpathy is a computer scientist.</p>
              <h2>Career</h2>
              <p>Karpathy worked at OpenAI and Tesla.</p>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.title == "Andrej Karpathy"
    assert document.summary == ["Andrej Karpathy is a computer scientist."]
    assert [block.kind for block in document.blocks] == ["image", "heading", "paragraph"]

    image_block = document.blocks[0]
    assert isinstance(image_block, ImageBlock)
    assert image_block.title == "File:Andrej_Karpathy,_OpenAI.png"
    assert image_block.caption == "Karpathy at Stanford in 2016"
