import re
from typing import Literal

from bs4 import BeautifulSoup, Tag

from wiki2md.document import Document, HeadingBlock, ImageBlock, ListBlock, ParagraphBlock
from wiki2md.errors import ParseError
from wiki2md.models import FetchedArticle

NOISE_SELECTORS = [
    ".mw-editsection",
    ".navbox",
    ".metadata",
    ".noprint",
    ".mw-empty-elt",
]


def _clean_text(node: Tag) -> str:
    text = " ".join(node.get_text(" ", strip=True).split())
    return re.sub(r"\s+(\[\d+\])", r"\1", text)


def _extract_image_block(node: Tag, role: Literal["infobox", "body"]) -> ImageBlock | None:
    anchor = node.select_one("a.mw-file-description[href^='/wiki/File:']")
    image = node.select_one("img")
    if anchor is None or image is None:
        return None

    title = anchor["href"].removeprefix("/wiki/")
    caption_node = node.select_one(".infobox-caption, figcaption")
    caption = _clean_text(caption_node) if caption_node else None

    return ImageBlock(
        title=title,
        alt=image.get("alt", "").strip(),
        caption=caption,
        role=role,
    )


def normalize_article(article: FetchedArticle) -> Document:
    soup = BeautifulSoup(article.html, "html.parser")

    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    body = soup.body or soup
    title_node = body.find("h1")
    if title_node is None:
        raise ParseError("Expected an <h1> title in the article HTML.")

    document = Document(title=_clean_text(title_node))

    infobox = body.select_one("table.infobox")
    if infobox is not None:
        image_block = _extract_image_block(infobox, role="infobox")
        if image_block is not None:
            document.blocks.append(image_block)

    for node in body.find_all(["h2", "h3", "p", "ul", "ol", "figure"], recursive=True):
        if node.find_parent("table", class_="infobox") is not None:
            continue

        if node.name == "p":
            text = _clean_text(node)
            if text:
                if not document.summary:
                    document.summary.append(text)
                else:
                    document.blocks.append(ParagraphBlock(text=text))
        elif node.name in {"h2", "h3"}:
            heading_text = _clean_text(node)
            if heading_text.lower() == "references":
                continue
            document.blocks.append(HeadingBlock(level=2 if node.name == "h2" else 3, text=heading_text))
        elif node.name in {"ul", "ol"} and "references" not in (node.get("class") or []):
            items = [_clean_text(item) for item in node.find_all("li", recursive=False)]
            if items:
                document.blocks.append(ListBlock(ordered=node.name == "ol", items=items))
        elif node.name == "figure":
            image_block = _extract_image_block(node, role="body")
            if image_block is not None:
                document.blocks.append(image_block)

    for item in body.select("ol.references > li"):
        text = _clean_text(item)
        if text:
            document.references.append(text)

    if not document.summary:
        document.warnings.append("No lead summary paragraph detected.")

    return document
