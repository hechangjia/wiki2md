import re
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from wiki2md.discovery_models import DiscoveryCandidate
from wiki2md.normalize import NOISE_SELECTORS, _is_template_control_text
from wiki2md.urls import SUPPORTED_HOSTS, slugify_title

_PERSON_BLOCKS = ("p", "li", "td", "th")
_CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_DISALLOWED_NAMESPACES = (
    "Category:",
    "Help:",
    "Portal:",
    "Special:",
    "Talk:",
    "Template:",
    "Wikipedia:",
    "File:",
)
_DISALLOWED_TITLES = {"Main_Page"}
_NON_PERSON_HINTS = (
    "award",
    "medal",
    "prize",
    "mathematics",
    "physics",
    "chemistry",
    "computer_science",
    "institute",
    "university",
    "laboratory",
    "laboratories",
    "labs",
    "company",
    "corp",
    "corporation",
    "list_of",
    "history_of",
    "identifier",
)
_EXPANSION_HINTS = (
    "list_of",
    "laureate",
    "laureates",
    "recipient",
    "recipients",
    "winner",
    "winners",
    "medalist",
    "medalists",
    "by_year",
)
_LANGUAGE_SWITCH_TEXTS = {"中文", "简体", "簡體", "繁體", "english", "日本語"}


def _clean_html(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for selector in [*NOISE_SELECTORS, ".sidebar", ".navbox", ".vertical-navbox"]:
        for node in soup.select(selector):
            node.decompose()
    return soup


def _iter_article_anchors(container: Tag):
    for anchor in container.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("#"):
            continue
        yield anchor


def _normalize_wiki_article_url(source_url: str, href: str) -> tuple[str, str] | None:
    normalized_url = urljoin(source_url, href)
    parsed = urlparse(normalized_url)
    source_parsed = urlparse(source_url)
    lang = SUPPORTED_HOSTS.get(parsed.netloc)
    if (
        lang is None
        or not parsed.path.startswith("/wiki/")
        or parsed.netloc != source_parsed.netloc
    ):
        return None

    title = unquote(parsed.path.removeprefix("/wiki/"))
    if not title or title.startswith(_DISALLOWED_NAMESPACES) or title in _DISALLOWED_TITLES:
        return None
    if parsed.fragment:
        return None

    canonical = f"https://{parsed.netloc}/wiki/{title.replace(' ', '_')}"
    return canonical, title


def _looks_like_person(title: str, anchor_text: str) -> bool:
    cleaned_anchor = " ".join(anchor_text.split())
    if not cleaned_anchor or _is_template_control_text(cleaned_anchor):
        return False
    if cleaned_anchor.casefold() in {text.casefold() for text in _LANGUAGE_SWITCH_TEXTS}:
        return False

    title_lower = title.casefold()
    anchor_lower = cleaned_anchor.casefold().replace(" ", "_")

    if any(title.startswith(prefix) for prefix in _DISALLOWED_NAMESPACES):
        return False
    if any(hint in title_lower for hint in _NON_PERSON_HINTS):
        return False
    if any(hint in anchor_lower for hint in _NON_PERSON_HINTS):
        return False

    if _CJK_RE.search(cleaned_anchor):
        return True

    return any(char.isupper() for char in cleaned_anchor)


def _looks_like_expansion_page(title: str, anchor_text: str) -> bool:
    cleaned_anchor = " ".join(anchor_text.split())
    if not cleaned_anchor or _is_template_control_text(cleaned_anchor):
        return False
    title_lower = title.casefold()
    anchor_lower = cleaned_anchor.casefold().replace(" ", "_")
    return any(hint in title_lower or hint in anchor_lower for hint in _EXPANSION_HINTS)


def extract_person_candidates(
    html: str,
    *,
    source_url: str,
    depth: int,
) -> list[DiscoveryCandidate]:
    soup = _clean_html(html)
    candidates: list[DiscoveryCandidate] = []
    seen: set[str] = set()

    for container in soup.find_all(_PERSON_BLOCKS):
        for anchor in _iter_article_anchors(container):
            normalized = _normalize_wiki_article_url(source_url, anchor["href"])
            if normalized is None:
                continue
            normalized_url, title = normalized
            anchor_text = anchor.get_text(" ", strip=True)
            if not _looks_like_person(title, anchor_text):
                continue
            if normalized_url in seen:
                continue
            seen.add(normalized_url)
            candidates.append(
                DiscoveryCandidate(
                    url=normalized_url,
                    title=title.replace("_", " "),
                    slug=slugify_title(title),
                    anchor_text=anchor_text,
                    source_page=source_url,
                    depth=depth,
                    frequency=1,
                )
            )

    return candidates


def extract_expansion_links(
    html: str,
    *,
    source_url: str,
) -> list[str]:
    soup = _clean_html(html)
    links: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        normalized = _normalize_wiki_article_url(source_url, anchor["href"])
        if normalized is None:
            continue
        normalized_url, title = normalized
        anchor_text = anchor.get_text(" ", strip=True)
        if not _looks_like_expansion_page(title, anchor_text):
            continue
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        links.append(normalized_url)

    return links
