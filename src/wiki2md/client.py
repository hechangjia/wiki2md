import time
from collections.abc import Mapping
from types import TracebackType
from typing import Any
from urllib.parse import quote, unquote, urlparse

import httpx

from wiki2md.errors import FetchError
from wiki2md.models import FetchedArticle, MediaItem, UrlResolution
from wiki2md.urls import SUPPORTED_HOSTS

HTML_FETCH_MAX_ATTEMPTS = 3
HTML_FETCH_BASE_RETRY_DELAY_SECONDS = 1.0


def _normalize_media_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    return url


class MediaWikiClient:
    def __init__(
        self,
        user_agent: str,
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.user_agent = user_agent
        self._owns_client = client is None
        self._closed = False
        self._client = client or httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )

    def __enter__(self) -> "MediaWikiClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        if self._owns_client:
            self._client.close()
        self._closed = True

    def _base_url(self, lang: str) -> str:
        return f"https://{lang}.wikipedia.org/w/rest.php/v1"

    def _get_json(self, url: str, context: str) -> dict[str, Any]:
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"Failed to fetch {context} from {url}: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise FetchError(f"Invalid JSON for {context} from {url}") from exc
        if not isinstance(payload, dict):
            payload_type = type(payload).__name__
            raise FetchError(
                "Invalid payload type for "
                f"{context} from {url}: expected object, got {payload_type}"
            )
        return payload

    def _get_text(self, url: str, context: str) -> str:
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"Failed to fetch {context} from {url}: {exc}") from exc
        return response.text

    def _require_string(self, payload: Mapping[str, Any], field: str, context: str) -> str:
        value = payload.get(field)
        if isinstance(value, str):
            return value
        raise FetchError(f"Missing required string field '{field}' in {context}")

    def _optional_section(
        self,
        payload: Mapping[str, Any],
        field: str,
        context: str,
    ) -> dict[str, Any]:
        value = payload.get(field)
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        raise FetchError(f"Invalid section '{field}' in {context}: expected object")

    def _optional_string(self, payload: Mapping[str, Any], field: str, context: str) -> str | None:
        value = payload.get(field)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise FetchError(f"Invalid field '{field}' in {context}: expected string")

    def fetch_article(self, resolution: UrlResolution) -> FetchedArticle:
        title = quote(resolution.title, safe=":_()")
        base_url = self._base_url(resolution.lang)
        bare_url = f"{base_url}/page/{title}/bare"
        html_url = f"{base_url}/page/{title}/html"
        media_url = f"{base_url}/page/{title}/links/media"

        bare_payload = self._get_json(bare_url, "page bare metadata")
        html = self._get_text(html_url, "article HTML")
        media_payload = self._get_json(media_url, "media links")

        if "files" not in media_payload:
            raise FetchError(f"Missing required field 'files' in media links from {media_url}")
        files = media_payload["files"]
        if not isinstance(files, list):
            raise FetchError(
                f"Invalid section 'files' in media links from {media_url}: expected list"
            )

        media_items = []
        for index, item in enumerate(files):
            if not isinstance(item, dict):
                raise FetchError(
                    f"Invalid media item at index {index} from {media_url}: expected object"
                )
            item_context = f"media links from {media_url} at files[{index}]"
            original = self._optional_section(item, "original", item_context)
            thumbnail = self._optional_section(item, "thumbnail", item_context)
            original_url = self._optional_string(original, "url", f"{item_context}.original")
            thumbnail_url = self._optional_string(thumbnail, "url", f"{item_context}.thumbnail")
            mime_type = original.get("mimetype") or thumbnail.get("mimetype")
            media_items.append(
                MediaItem(
                    title=self._require_string(item, "title", item_context),
                    original_url=_normalize_media_url(original_url),
                    thumbnail_url=_normalize_media_url(thumbnail_url),
                    mime_type=mime_type if isinstance(mime_type, str) else None,
                )
            )

        latest = self._optional_section(
            bare_payload,
            "latest",
            f"page bare metadata from {bare_url}",
        )
        pageid = bare_payload.get("id")
        revid = latest.get("id")
        if pageid is not None and not isinstance(pageid, int):
            raise FetchError(
                f"Invalid field 'id' in page bare metadata from {bare_url}: expected int"
            )
        if revid is not None and not isinstance(revid, int):
            raise FetchError(
                f"Invalid field 'latest.id' in page bare metadata from {bare_url}: expected int"
            )

        return FetchedArticle(
            resolution=resolution,
            canonical_title=self._require_string(
                bare_payload,
                "title",
                f"page bare metadata from {bare_url}",
            ),
            pageid=pageid,
            revid=revid,
            html=html,
            media=media_items,
        )

    def fetch_file(self, lang: str, title: str) -> MediaItem:
        file_url = f"{self._base_url(lang)}/file/{quote(title, safe=':_()')}"
        payload = self._get_json(file_url, "file metadata")
        original = self._optional_section(payload, "original", f"file metadata from {file_url}")
        thumbnail = self._optional_section(payload, "thumbnail", f"file metadata from {file_url}")
        original_url = self._optional_string(
            original, "url", f"file metadata from {file_url}.original"
        )
        thumbnail_url = self._optional_string(
            thumbnail, "url", f"file metadata from {file_url}.thumbnail"
        )
        mime_type = original.get("mimetype") or thumbnail.get("mimetype")

        return MediaItem(
            title=self._require_string(payload, "title", f"file metadata from {file_url}"),
            original_url=_normalize_media_url(original_url),
            thumbnail_url=_normalize_media_url(thumbnail_url),
            mime_type=mime_type if isinstance(mime_type, str) else None,
        )

    def fetch_html_url(self, url: str) -> str:
        fetch_url = _page_html_endpoint_for_url(url)
        last_error: httpx.HTTPError | None = None

        for attempt in range(1, HTML_FETCH_MAX_ATTEMPTS + 1):
            try:
                response = self._client.get(fetch_url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= HTML_FETCH_MAX_ATTEMPTS or not _is_retriable_html_error(exc):
                    break
                time.sleep(HTML_FETCH_BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)))

        assert last_error is not None
        raise FetchError(
            f"Failed to fetch page HTML from {fetch_url}: {last_error}"
        ) from last_error

    def fetch_page_summary(self, url: str) -> dict[str, Any]:
        summary_url = _page_summary_endpoint_for_url(url)
        last_error: httpx.HTTPError | None = None

        for attempt in range(1, HTML_FETCH_MAX_ATTEMPTS + 1):
            try:
                response = self._client.get(summary_url)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise FetchError(
                        "Invalid payload type for page summary from "
                        f"{summary_url}: expected object"
                    )
                return payload
            except ValueError as exc:
                raise FetchError(f"Invalid JSON for page summary from {summary_url}") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= HTML_FETCH_MAX_ATTEMPTS or not _is_retriable_html_error(exc):
                    break
                time.sleep(HTML_FETCH_BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)))

        assert last_error is not None
        raise FetchError(
            f"Failed to fetch page summary from {summary_url}: {last_error}"
        ) from last_error


def _is_retriable_html_error(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or 500 <= exc.response.status_code < 600
    return isinstance(exc, httpx.TransportError)


def _page_html_endpoint_for_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc in SUPPORTED_HOSTS and parsed.path.startswith("/wiki/"):
        title = unquote(parsed.path.removeprefix("/wiki/")).replace(" ", "_")
        return f"https://{parsed.netloc}/w/rest.php/v1/page/{quote(title, safe=':_()')}/html"
    return url


def _page_summary_endpoint_for_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc in SUPPORTED_HOSTS and parsed.path.startswith("/wiki/"):
        title = unquote(parsed.path.removeprefix("/wiki/")).replace(" ", "_")
        return f"https://{parsed.netloc}/api/rest_v1/page/summary/{quote(title, safe=':_()')}"
    return url
