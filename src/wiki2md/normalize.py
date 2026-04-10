import re
from typing import Literal
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from wiki2md.document import (
    Document,
    HeadingBlock,
    ImageBlock,
    InfoboxData,
    InfoboxField,
    InfoboxImage,
    InfoboxLink,
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
_RIGHT_ATTACHED_CHARS = set(",.;:!?)]}，。！？；：、）》」』】")
_LEFT_ATTACHED_CHARS = set("([{（《「『【")
_ARCHIVE_HINTS = ("archive.org", "wayback", "webcache")
_IDENTIFIER_HINTS = ("doi", "pmid", "arxiv", "oclc", "isbn", "issn", "hdl", "proquest")
_PORTRAIT_LABELS = {
    "portrait",
    "image",
    "photo",
    "photograph",
    "肖像",
    "照片",
    "图像",
    "圖片",
}

_MONTH_NAMES = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_TEMPLATE_CONTROL_TEXTS = {"v", "t", "e", "vte"}


def _is_cjk(char: str) -> bool:
    return bool(_CJK_CHAR_RE.fullmatch(char))


def _needs_space(previous: str, current: str) -> bool:
    prev_char = previous[-1]
    curr_char = current[0]

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


def _clean_prose_text(node: Tag) -> str:
    clone = BeautifulSoup(str(node), "html.parser").find()
    if clone is None:
        return ""

    for reference in clone.select("sup.reference, sup.mw-ref, [rel~='dc:references']"):
        reference.decompose()

    return _clean_text(clone)


def _looks_like_orphan_date(text: str) -> bool:
    normalized = " ".join(text.split()).casefold()
    if not normalized or "," not in normalized:
        return False
    return any(normalized.startswith(f"{month} ") for month in _MONTH_NAMES)


def _is_template_control_text(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text).casefold()
    return normalized in _TEMPLATE_CONTROL_TEXTS


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
        if _is_reference_anchor_href(href):
            anchor.decompose()

    return _clean_text(clone)


def _extract_reference_links(node: Tag, article: FetchedArticle) -> list[ReferenceLink]:
    links: list[ReferenceLink] = []

    for anchor in node.find_all("a", href=True):
        href = anchor.get("href", "")
        text = _clean_text(anchor)
        if not href or not text or _is_reference_anchor_href(href):
            continue
        normalized_href = _normalize_href(article, href)
        links.append(
            ReferenceLink(
                text=text,
                href=normalized_href,
                kind=_classify_reference_link(text, normalized_href),
            )
        )

    return links


def _is_reference_anchor_href(href: str) -> bool:
    parsed = urlparse(href)
    if href.startswith("#"):
        return True

    is_absolute = bool(parsed.netloc and parsed.scheme in {"http", "https"}) or href.startswith(
        "//"
    )
    if is_absolute:
        return False

    if "cite_ref" in href:
        return True

    fragment = parsed.fragment.casefold()
    if not fragment.startswith("cite_"):
        return False

    return True


def _classify_reference_link(
    text: str,
    href: str,
) -> Literal["external", "wiki", "archive", "identifier", "other"]:
    parsed = urlparse(href)
    host = parsed.netloc.casefold()
    path = parsed.path.casefold()
    combined = f"{text.casefold()} {host} {path} {parsed.query.casefold()}"

    if any(hint in host or hint in path for hint in _ARCHIVE_HINTS):
        return "archive"
    if "wikipedia.org" in host:
        return "wiki"
    if any(hint in combined for hint in _IDENTIFIER_HINTS):
        return "identifier"
    if parsed.scheme in {"http", "https"}:
        return "external"
    return "other"


def _select_primary_url(links: list[ReferenceLink]) -> str | None:
    for preferred in ("external", "archive", "identifier"):
        for link in links:
            if link.kind == preferred:
                return link.href
    return None


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


def _extract_infobox_image_block(infobox: Tag) -> ImageBlock | None:
    for cell in infobox.select("td.infobox-image, td.infobox-full-data"):
        block = _extract_image_block(cell, role="infobox")
        if block is not None:
            return block

    for row in infobox.find_all("tr"):
        if row.find_parent("table") is not infobox:
            continue

        label_node = row.find("th", recursive=False)
        if label_node is None:
            continue

        label = _clean_text(label_node).casefold()
        if label not in _PORTRAIT_LABELS:
            continue

        for cell in row.find_all("td", recursive=False):
            block = _extract_image_block(cell, role="infobox")
            if block is not None:
                return block

    for row in infobox.find_all("tr"):
        if row.find_parent("table") is not infobox:
            continue
        if row.find("th", recursive=False) is not None:
            continue
        for cell in row.find_all("td", recursive=False):
            block = _extract_image_block(cell, role="infobox")
            if block is not None:
                return block

    return _extract_image_block(infobox, role="infobox")


def _extract_infobox_links(node: Tag, article: FetchedArticle) -> list[InfoboxLink]:
    links: list[InfoboxLink] = []

    for anchor in node.find_all("a", href=True):
        text = _clean_text(anchor)
        href = anchor.get("href", "")
        if not text or not href or href.startswith("#"):
            continue
        links.append(InfoboxLink(text=text, href=_normalize_href(article, href)))

    return links


def _build_infobox_image(block: ImageBlock | None, article_title: str) -> InfoboxImage | None:
    if block is None:
        return None

    caption = block.caption or block.alt or article_title
    alt = block.alt or caption or article_title

    return InfoboxImage(title=block.title, path=None, alt=alt, caption=caption)


def _extract_infobox(article: FetchedArticle, infobox: Tag, title: str) -> InfoboxData:
    image = _build_infobox_image(_extract_infobox_image_block(infobox), title)
    fields: list[InfoboxField] = []

    for row in infobox.find_all("tr"):
        if row.find_parent("table") is not infobox:
            continue

        label_node = row.find("th", recursive=False)
        value_node = row.find("td", recursive=False)
        if label_node is None or value_node is None:
            continue
        if _extract_image_block(value_node, role="infobox") is not None:
            continue

        label = _clean_text(label_node)
        text = _clean_prose_text(value_node)
        if not label or not text:
            continue

        fields.append(
            InfoboxField(
                label=label,
                text=text,
                links=_extract_infobox_links(value_node, article),
            )
        )

    return InfoboxData(title=title, image=image, fields=fields)


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
        document.infobox = _extract_infobox(article, infobox, title)

    in_lead = True
    preserve_list_links = False
    for node in body.find_all(["h2", "h3", "p", "ul", "ol", "figure"], recursive=True):
        if node.find_parent("table") is not None:
            continue
        if node.find_parent("ol", class_="references") is not None:
            continue

        if node.name == "p":
            text = _clean_prose_text(node)
            if not text or _looks_like_orphan_date(text):
                continue
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
                if not text or _is_template_control_text(text):
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
            links = _extract_reference_links(item, article)
            document.references.append(
                ReferenceEntry(
                    id=item.get("id"),
                    text=text,
                    primary_url=_select_primary_url(links),
                    links=links,
                )
            )

    if not document.summary:
        document.warnings.append("No lead summary paragraph detected.")

    return document
