import re
from urllib.parse import quote, unquote, urlparse

from wiki2md.errors import InvalidWikipediaUrlError, UnsupportedPageError
from wiki2md.models import UrlResolution

SUPPORTED_HOSTS = {
    "en.wikipedia.org": "en",
    "zh.wikipedia.org": "zh",
}

UNSUPPORTED_NAMESPACES = (
    "Category:",
    "分类:",
    "分類:",
    "Help:",
    "Portal:",
    "Special:",
    "Talk:",
    "Template:",
    "Wikipedia:",
)

UNSUPPORTED_TITLE_PREFIXES = (
    "List_of_",
    "Timeline_of_",
)

DISAMBIGUATION_SUFFIX = "_(disambiguation)"
ZH_DISAMBIGUATION_SUFFIX = "_(消歧义)"
ZH_TRADITIONAL_DISAMBIGUATION_SUFFIX = "_(消歧義)"


def slugify_title(title: str) -> str:
    normalized = title.replace("_", " ").replace("·", "-")
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"[\s_]+", "-", normalized.strip(), flags=re.UNICODE)
    return normalized.casefold() or "article"


def resolve_wikipedia_url(url: str) -> UrlResolution:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise InvalidWikipediaUrlError(f"Unsupported URL scheme: {parsed.scheme!r}")

    lang = SUPPORTED_HOSTS.get(parsed.netloc)
    if lang is None:
        raise InvalidWikipediaUrlError(f"Unsupported Wikipedia host: {parsed.netloc!r}")

    if not parsed.path.startswith("/wiki/"):
        raise InvalidWikipediaUrlError(f"Unsupported Wikipedia path: {parsed.path!r}")

    title = unquote(parsed.path.removeprefix("/wiki/"))
    if not title:
        raise InvalidWikipediaUrlError("Article title is missing from the URL.")

    if title.startswith(UNSUPPORTED_NAMESPACES):
        raise UnsupportedPageError(f"Unsupported namespace: {title}")

    if title.startswith(UNSUPPORTED_TITLE_PREFIXES) or title.endswith(
        (
            DISAMBIGUATION_SUFFIX,
            ZH_DISAMBIGUATION_SUFFIX,
            ZH_TRADITIONAL_DISAMBIGUATION_SUFFIX,
        )
    ):
        raise UnsupportedPageError(f"Unsupported page type: {title}")

    normalized_title = title.replace(" ", "_")
    normalized_url = f"https://{parsed.netloc}/wiki/{quote(normalized_title, safe=':_()')}"

    return UrlResolution(
        source_url=url,
        normalized_url=normalized_url,
        lang=lang,
        title=normalized_title,
        slug=slugify_title(title),
    )
