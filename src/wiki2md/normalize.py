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

REFERENCE_HEADINGS = {
    "en": {"references"},
    "zh": {"参考文献"},
}

_CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_REFERENCE_MARKER_RE = re.compile(r"\[\d+\]")
_RIGHT_ATTACHED_CHARS = set(",.;:!?)]}，。！？；：、）》」』】")
_LEFT_ATTACHED_CHARS = set("([{（《「『【")


def _is_cjk(char: str) -> bool:
    return bool(_CJK_CHAR_RE.fullmatch(char))


def _needs_space(previous: str, current: str) -> bool:
    prev_char = previous[-1]
    curr_char = current[0]

    if _REFERENCE_MARKER_RE.fullmatch(current):
        return False
    if curr_char in _RIGHT_ATTACHED_CHARS:
        return False
    if prev_char in _LEFT_ATTACHED_CHARS:
        return False
    if curr_char in {"'", "’"}:
        return False
    if _is_cjk(prev_char) or _is_cjk(curr_char):
        return False
    return True


def _is_references_heading(text: str, lang: str) -> bool:
    if lang == "zh":
        return text in REFERENCE_HEADINGS["zh"]
    return text.casefold() in REFERENCE_HEADINGS["en"]


def _clean_text(node: Tag) -> str:
    chunks = [chunk for chunk in node.stripped_strings if chunk]
    if not chunks:
        return ""

    text = chunks[0]
    for chunk in chunks[1:]:
        if _needs_space(text, chunk):
            text += " "
        text += chunk

    return text


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

    in_lead = True
    for node in body.find_all(["h2", "h3", "p", "ul", "ol", "figure"], recursive=True):
        if node.find_parent("table", class_="infobox") is not None:
            continue

        if node.name == "p":
            text = _clean_text(node)
            if text:
                if in_lead:
                    document.summary.append(text)
                else:
                    document.blocks.append(ParagraphBlock(text=text))
        elif node.name in {"h2", "h3"}:
            heading_text = _clean_text(node)
            if _is_references_heading(heading_text, article.resolution.lang):
                continue
            in_lead = False
            document.blocks.append(
                HeadingBlock(level=2 if node.name == "h2" else 3, text=heading_text)
            )
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
