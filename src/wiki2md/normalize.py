import re
from typing import Literal
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

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
from wiki2md.errors import ParseError
from wiki2md.models import FetchedArticle

NOISE_SELECTORS = [
    ".mw-editsection",
    ".navbox",
    ".metadata",
    ".noprint",
    ".mw-empty-elt",
]
FILE_LINK_PREFIXES = ("/wiki/File:", "./File:")

REFERENCE_HEADINGS = {
    "en": {"references"},
    "zh": {"参考文献"},
}
LINK_PRESERVING_HEADINGS = {
    "en": {"external links", "further reading"},
    "zh": {"外部链接", "外部連結", "延伸阅读", "延伸閱讀", "进一步阅读", "進一步閱讀"},
}

_CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_REFERENCE_MARKER_RE = re.compile(r"\[[^\[\]]+\]")
_INLINE_CITATION_RUN_RE = re.compile(r"(?:\s*\[(?:\d+|note\s+\d+)\])+", re.IGNORECASE)
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?，。！？；：、])")
_MULTI_SPACE_RE = re.compile(r" {2,}")
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


def _preserve_links_for_heading(text: str, lang: str) -> bool:
    if lang == "zh":
        return text in LINK_PRESERVING_HEADINGS["zh"]
    return text.casefold() in LINK_PRESERVING_HEADINGS["en"]


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


def _strip_inline_citation_markers(text: str) -> str:
    cleaned = _INLINE_CITATION_RUN_RE.sub("", text)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def _clean_prose_text(node: Tag) -> str:
    return _strip_inline_citation_markers(_clean_text(node))


def _normalize_href(article: FetchedArticle, href: str) -> str:
    if href.startswith("//"):
        return f"https:{href}"
    return urljoin(article.resolution.normalized_url, href)


def _extract_reference_text(node: Tag) -> str:
    clone = BeautifulSoup(str(node), "html.parser").find()
    if clone is None:
        return ""

    for backlink in clone.select(".mw-cite-backlink"):
        backlink.decompose()
    for anchor in clone.find_all("a", href=True):
        href = anchor.get("href", "")
        if "cite_ref" in href:
            anchor.decompose()

    return _clean_text(clone)


def _extract_reference_links(node: Tag, article: FetchedArticle) -> list[ReferenceLink]:
    links: list[ReferenceLink] = []

    for anchor in node.find_all("a", href=True):
        href = anchor.get("href", "")
        text = _clean_text(anchor)
        if not href or not text or "cite_ref" in href:
            continue
        links.append(ReferenceLink(text=text, href=_normalize_href(article, href)))

    return links


def _extract_list_item_href(
    item: Tag,
    article: FetchedArticle,
    preserve_links: bool,
) -> str | None:
    if not preserve_links:
        return None

    for anchor in item.find_all("a", href=True):
        href = anchor.get("href", "")
        text = _clean_text(anchor)
        if not href or not text or text == "Edit this at Wikidata":
            continue
        rel = anchor.get("rel") or []
        if "mw:ExtLink" in rel or href.startswith(("https://", "http://", "//")):
            return _normalize_href(article, href)

    return None


def _extract_image_block(node: Tag, role: Literal["infobox", "body"]) -> ImageBlock | None:
    anchor = node.select_one("a.mw-file-description[href]")
    image = node.select_one("img")
    if anchor is None or image is None:
        return None

    href = anchor.get("href", "")
    if not any(href.startswith(prefix) for prefix in FILE_LINK_PREFIXES):
        return None

    title = href.removeprefix("/wiki/").removeprefix("./")
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
    title = _clean_text(title_node) if title_node is not None else article.canonical_title.strip()
    if not title:
        raise ParseError("Expected a title in the article HTML or fetched article metadata.")

    document = Document(title=title)

    infobox = body.select_one("table.infobox")
    if infobox is not None:
        image_block = _extract_image_block(infobox, role="infobox")
        if image_block is not None:
            document.blocks.append(image_block)

    in_lead = True
    preserve_list_links = False
    for node in body.find_all(["h2", "h3", "p", "ul", "ol", "figure"], recursive=True):
        if node.find_parent("table", class_="infobox") is not None:
            continue
        if node.find_parent("ol", class_="references") is not None:
            continue

        if node.name == "p":
            text = _clean_prose_text(node)
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
            preserve_list_links = _preserve_links_for_heading(heading_text, article.resolution.lang)
            document.blocks.append(
                HeadingBlock(level=2 if node.name == "h2" else 3, text=heading_text)
            )
        elif node.name in {"ul", "ol"} and "references" not in (node.get("class") or []):
            items = []
            for item in node.find_all("li", recursive=False):
                text = _clean_prose_text(item)
                if not text:
                    continue
                items.append(
                    ListItem(
                        text=text,
                        href=_extract_list_item_href(item, article, preserve_list_links),
                    )
                )
            if items:
                document.blocks.append(ListBlock(ordered=node.name == "ol", items=items))
        elif node.name == "figure":
            image_block = _extract_image_block(node, role="body")
            if image_block is not None:
                document.blocks.append(image_block)

    for item in body.select("ol.references > li"):
        text = _extract_reference_text(item)
        if text:
            document.references.append(
                ReferenceEntry(
                    id=item.get("id"),
                    text=text,
                    links=_extract_reference_links(item, article),
                )
            )

    if not document.summary:
        document.warnings.append("No lead summary paragraph detected.")

    return document
