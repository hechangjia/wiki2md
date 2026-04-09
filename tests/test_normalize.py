from pathlib import Path

from wiki2md.document import (
    Document,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ListItem,
    ParagraphBlock,
    ReferenceEntry,
    ReferenceLink,
)
from wiki2md.models import FetchedArticle, UrlResolution
from wiki2md.normalize import _select_primary_url, normalize_article

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
        "Andrej Karpathy is a Slovak-Canadian computer scientist.",
        "He cofounded Eureka Labs and writes about neural networks.",
    ]
    assert [reference.text for reference in document.references] == [
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
    assert list_block.items == [ListItem(text="OpenAI"), ListItem(text="Tesla")]
    assert document.references == [
        ReferenceEntry(text="Reference number one."),
        ReferenceEntry(text="Reference number two in paragraph form."),
    ]
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
    assert document.summary == ["艾伦·图灵是英国数学家、计算机科学先驱。"]
    assert document.references == [ReferenceEntry(text="图灵传记资料。")]
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


def test_normalize_article_strips_inline_citation_markers_from_prose() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>
                Geoffrey Hinton is a researcher.
                <sup class="mw-ref reference"><a href="#cite_note-8">[8]</a></sup>
                <sup class="reference"><a href="#cite_note-9">[9]</a></sup>
              </p>
              <h2>Career</h2>
              <p>He left Google in 2023.<sup class="reference">[10]</sup></p>
              <ul>
                <li>Worked at Google.<sup class="reference">[11]</sup></li>
              </ul>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["Geoffrey Hinton is a researcher."]
    assert document.blocks[1].text == "He left Google in 2023."
    assert document.blocks[2].items == [ListItem(text="Worked at Google.")]


def test_normalize_article_strips_inline_citation_markers_from_chinese_prose() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://zh.wikipedia.org/wiki/%E6%9D%B0%E5%BC%97%E9%87%8C%C2%B7%E8%BE%9B%E9%A1%BF",
            normalized_url="https://zh.wikipedia.org/wiki/%E6%9D%B0%E5%BC%97%E9%87%8C%C2%B7%E8%BE%9B%E9%A1%BF",
            lang="zh",
            title="杰弗里·辛顿",
            slug="杰弗里-辛顿",
        ),
        canonical_title="杰弗里·辛顿",
        html="""
        <html>
          <head><title>杰弗里·辛顿</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>
                杰弗里·辛顿是计算机科学家。
                <sup class="reference">[1]</sup>
                <sup class="reference">[2]</sup>
              </p>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["杰弗里·辛顿是计算机科学家。"]


def test_normalize_article_preserves_genuine_bracketed_content() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Activation",
            normalized_url="https://en.wikipedia.org/wiki/Activation",
            lang="en",
            title="Activation",
            slug="activation",
        ),
        canonical_title="Activation",
        html="""
        <html>
          <head><title>Activation</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>The activation stays in [0, 1].</p>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["The activation stays in [0, 1]."]


def test_normalize_article_preserves_bracketed_numbers_without_reference_nodes() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Layer",
            normalized_url="https://en.wikipedia.org/wiki/Layer",
            lang="en",
            title="Layer",
            slug="layer",
        ),
        canonical_title="Layer",
        html="""
        <html>
          <head><title>Layer</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>The model uses layer [1] for initialization.</p>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["The model uses layer [1] for initialization."]


def test_normalize_article_preserves_bracketed_numbers_in_inline_nodes() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Layer",
            normalized_url="https://en.wikipedia.org/wiki/Layer",
            lang="en",
            title="Layer",
            slug="layer",
        ),
        canonical_title="Layer",
        html="""
        <html>
          <head><title>Layer</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>The model uses layer <i>[1]</i> for initialization.</p>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["The model uses layer [1] for initialization."]


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


def test_normalize_article_preserves_external_links_in_list_sections() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        pageid=12345,
        revid=67890,
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>Geoffrey Hinton is a computer scientist.</p>
              <h2>External links</h2>
              <ul>
                <li>
                  <a
                    class="external text"
                    href="https://inspirehep.net/author/profile/Geoffrey.E.Hinton.1"
                    rel="mw:ExtLink nofollow"
                  >Geoffrey Hinton</a>
                  <span> on </span>
                  <a href="./INSPIRE-HEP" rel="mw:WikiLink">INSPIRE-HEP</a>
                </li>
              </ul>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert [block.kind for block in document.blocks] == ["heading", "list"]
    list_block = document.blocks[1]
    assert isinstance(list_block, ListBlock)
    assert list_block.items == [
        ListItem(
            text="Geoffrey Hinton on INSPIRE-HEP",
            href="https://inspirehep.net/author/profile/Geoffrey.E.Hinton.1",
        )
    ]


def test_normalize_article_classifies_reference_links_and_selects_primary_url() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>Geoffrey Hinton is a researcher.</p>
              <h2>References</h2>
              <ol class="references">
                <li id="cite_note-example-1">
                  <span class="mw-cite-backlink">
                    <a href="./Geoffrey_Hinton#cite_ref-example-1">↑</a>
                  </span>
                  <cite>
                    Example article.
                    <a href="https://example.com/source">Example source</a>
                    <a href="https://archive.org/details/example-source">Archived copy</a>
                    <a href="./DOI_(identifier)">DOI</a>
                    <a href="https://doi.org/10.1000/example">10.1000/example</a>
                  </cite>
                </li>
              </ol>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert [reference.model_dump(mode="json") for reference in document.references] == [
        {
            "id": "cite_note-example-1",
            "text": "Example article. Example source Archived copy DOI 10.1000/example",
            "primary_url": "https://example.com/source",
            "links": [
                {
                    "text": "Example source",
                    "href": "https://example.com/source",
                    "kind": "external",
                },
                {
                    "text": "Archived copy",
                    "href": "https://archive.org/details/example-source",
                    "kind": "archive",
                },
                {
                    "text": "DOI",
                    "href": "https://en.wikipedia.org/wiki/DOI_(identifier)",
                    "kind": "wiki",
                },
                {
                    "text": "10.1000/example",
                    "href": "https://doi.org/10.1000/example",
                    "kind": "identifier",
                },
            ],
        }
    ]


def test_normalize_article_excludes_fragment_only_reference_links() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <h2>References</h2>
              <ol class="references">
                <li id="cite_note-example-1">
                  <cite>
                    <a href="#cite_note-example-1">self anchor</a>
                    <a href="./Geoffrey_Hinton#cite_note-example-2">note anchor</a>
                    <a href="https://example.com/source">Example source</a>
                  </cite>
                </li>
              </ol>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert [reference.model_dump(mode="json") for reference in document.references] == [
        {
            "id": "cite_note-example-1",
            "text": "Example source",
            "primary_url": "https://example.com/source",
            "links": [
                {
                    "text": "Example source",
                    "href": "https://example.com/source",
                    "kind": "external",
                }
            ],
        }
    ]


def test_normalize_article_preserves_external_urls_with_cite_fragments() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <h2>References</h2>
              <ol class="references">
                <li id="cite_note-example-1">
                  <cite>
                    <a href="https://example.com/page#cite_note-1">External citation anchor</a>
                    <a href="./Geoffrey_Hinton#cite_note-example-2">Local note anchor</a>
                  </cite>
                </li>
              </ol>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert [reference.model_dump(mode="json") for reference in document.references] == [
        {
            "id": "cite_note-example-1",
            "text": "External citation anchor",
            "primary_url": "https://example.com/page#cite_note-1",
            "links": [
                {
                    "text": "External citation anchor",
                    "href": "https://example.com/page#cite_note-1",
                    "kind": "external",
                }
            ],
        }
    ]


def test_normalize_article_preserves_external_urls_with_cite_ref_substrings() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <h2>References</h2>
              <ol class="references">
                <li id="cite_note-example-1">
                  <cite>
                    <a href="https://example.com/cite_ref-guide">External cite_ref path</a>
                    <a href="./Geoffrey_Hinton#cite_ref-example-2">Local cite_ref anchor</a>
                  </cite>
                </li>
              </ol>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert [reference.model_dump(mode="json") for reference in document.references] == [
        {
            "id": "cite_note-example-1",
            "text": "External cite_ref path",
            "primary_url": "https://example.com/cite_ref-guide",
            "links": [
                {
                    "text": "External cite_ref path",
                    "href": "https://example.com/cite_ref-guide",
                    "kind": "external",
                }
            ],
        }
    ]


def test_select_primary_url_prefers_archive_when_external_missing() -> None:
    links = [
        ReferenceLink(
            text="Archived copy",
            href="https://archive.org/details/example-source",
            kind="archive",
        ),
        ReferenceLink(
            text="10.1000/example",
            href="https://doi.org/10.1000/example",
            kind="identifier",
        ),
    ]

    assert _select_primary_url(links) == "https://archive.org/details/example-source"


def test_select_primary_url_uses_identifier_when_best_available() -> None:
    links = [
        ReferenceLink(
            text="10.1000/example",
            href="https://doi.org/10.1000/example",
            kind="identifier",
        ),
        ReferenceLink(
            text="Wikipedia entry",
            href="https://en.wikipedia.org/wiki/DOI",
            kind="wiki",
        ),
    ]

    assert _select_primary_url(links) == "https://doi.org/10.1000/example"
