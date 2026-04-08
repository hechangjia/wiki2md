from urllib.parse import quote

import httpx

from wiki2md.errors import FetchError
from wiki2md.models import FetchedArticle, MediaItem, UrlResolution


def _normalize_media_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    return url


class MediaWikiClient:
    def __init__(self, user_agent: str, timeout: float = 15.0) -> None:
        self.user_agent = user_agent
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )

    def _base_url(self, lang: str) -> str:
        return f"https://{lang}.wikipedia.org/w/rest.php/v1"

    def _get_json(self, url: str) -> dict:
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"Failed to fetch JSON from {url}") from exc
        return response.json()

    def _get_text(self, url: str) -> str:
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"Failed to fetch text from {url}") from exc
        return response.text

    def fetch_article(self, resolution: UrlResolution) -> FetchedArticle:
        title = quote(resolution.title, safe=":_()")
        base_url = self._base_url(resolution.lang)

        bare_payload = self._get_json(f"{base_url}/page/{title}/bare")
        html = self._get_text(f"{base_url}/page/{title}/html")
        media_payload = self._get_json(f"{base_url}/page/{title}/links/media")

        media_items = [
            MediaItem(
                title=item["title"],
                original_url=_normalize_media_url((item.get("original") or {}).get("url")),
                thumbnail_url=_normalize_media_url((item.get("thumbnail") or {}).get("url")),
                mime_type=(item.get("original") or {}).get("mimetype")
                or (item.get("thumbnail") or {}).get("mimetype"),
            )
            for item in media_payload.get("files", [])
        ]

        return FetchedArticle(
            resolution=resolution,
            canonical_title=bare_payload["title"],
            pageid=bare_payload.get("id"),
            revid=(bare_payload.get("latest") or {}).get("id"),
            html=html,
            media=media_items,
        )

    def fetch_file(self, lang: str, title: str) -> MediaItem:
        payload = self._get_json(f"{self._base_url(lang)}/file/{quote(title, safe=':_()')}")
        original = payload.get("original") or {}
        thumbnail = payload.get("thumbnail") or {}

        return MediaItem(
            title=payload["title"],
            original_url=_normalize_media_url(original.get("url")),
            thumbnail_url=_normalize_media_url(thumbnail.get("url")),
            mime_type=original.get("mimetype") or thumbnail.get("mimetype"),
        )
