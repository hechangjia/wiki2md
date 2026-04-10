import mimetypes
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from wiki2md.document import Document, ImageBlock
from wiki2md.models import AssetDownloadFailure, AssetDownloadReport, MediaItem, SelectedAsset

IGNORED_TITLES = {"audio.svg", "loudspeaker.svg"}
MAX_DOWNLOAD_ATTEMPTS = 3
BASE_RETRY_DELAY_SECONDS = 1.0
MAX_RETRY_DELAY_SECONDS = 10.0


def _guess_extension(source_url: str, mime_type: str | None) -> str:
    suffix = Path(urlparse(source_url).path).suffix
    if suffix:
        return suffix.lower()

    if mime_type:
        guessed = mimetypes.guess_extension(mime_type)
        if guessed:
            return guessed

    return ".bin"


def _normalize_title(title: str) -> str:
    normalized = unquote(title).strip()
    normalized = normalized.removeprefix("/wiki/").removeprefix("./")
    if normalized.casefold().startswith("file:"):
        normalized = normalized[5:]
    return normalized.replace("_", " ").casefold()


def select_assets(document: Document, media: list[MediaItem]) -> list[SelectedAsset]:
    media_by_title = {_normalize_title(item.title): item for item in media}
    selected: list[SelectedAsset] = []
    seen_titles: set[str] = set()
    counter = 1

    candidates: list[tuple[str, str]] = []
    if document.infobox and document.infobox.image is not None:
        candidates.append((document.infobox.image.title, "infobox"))

    for block in document.blocks:
        if isinstance(block, ImageBlock):
            candidates.append((block.title, "infobox" if block.role == "infobox" else "image"))

    for title, role in candidates:
        key = _normalize_title(title)
        if key in seen_titles:
            continue
        if key in IGNORED_TITLES:
            continue

        media_item = media_by_title.get(key)
        if media_item is None or not media_item.original_url:
            continue

        if (media_item.mime_type or "").startswith("image/svg") and "audio" in key:
            continue

        ext = _guess_extension(media_item.original_url, media_item.mime_type)
        filename = f"{counter:03d}-{role}{ext}"
        selected.append(
            SelectedAsset(
                title=title,
                source_url=media_item.original_url,
                filename=filename,
                relative_path=f"assets/{filename}",
            )
        )
        seen_titles.add(key)
        counter += 1

    return selected


def _is_retriable_status_code(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code < 600


def _parse_retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    try:
        return max(float(stripped), 0.0)
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(stripped)
    except (TypeError, ValueError, IndexError):
        return None

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)

    return max((retry_at - datetime.now(UTC)).total_seconds(), 0.0)


def _retry_delay_seconds(exc: httpx.HTTPError, attempt: int) -> float:
    if isinstance(exc, httpx.HTTPStatusError):
        retry_after = _parse_retry_after_seconds(exc.response.headers.get("Retry-After"))
        if retry_after is not None:
            return min(retry_after, MAX_RETRY_DELAY_SECONDS)

    backoff = BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
    return min(backoff, MAX_RETRY_DELAY_SECONDS)


def _is_retriable_error(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return _is_retriable_status_code(exc.response.status_code)
    return isinstance(exc, httpx.TransportError)


def _format_error(exc: httpx.HTTPError, attempts: int) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code} after {attempts} attempt(s)"
    return f"{type(exc).__name__} after {attempts} attempt(s): {exc}"


def _download_asset_bytes(
    client: httpx.Client,
    source_url: str,
) -> tuple[bytes | None, str | None]:
    last_error: httpx.HTTPError | None = None
    attempts = 0

    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        attempts = attempt
        try:
            response = client.get(source_url)
            response.raise_for_status()
            return response.content, None
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt >= MAX_DOWNLOAD_ATTEMPTS or not _is_retriable_error(exc):
                break
            time.sleep(_retry_delay_seconds(exc, attempt))

    if last_error is None:
        return None, "Unknown asset download failure"
    return None, _format_error(last_error, attempts)


def download_assets(
    assets: list[SelectedAsset] | list[dict],
    destination: Path,
    user_agent: str,
) -> AssetDownloadReport:
    destination.mkdir(parents=True, exist_ok=True)
    report = AssetDownloadReport()

    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": user_agent},
        timeout=20.0,
    ) as client:
        for asset in assets:
            item = asset if isinstance(asset, dict) else asset.model_dump()
            content, error = _download_asset_bytes(client, item["source_url"])
            if content is None:
                report.failures.append(
                    AssetDownloadFailure(
                        title=item["title"],
                        source_url=item["source_url"],
                        filename=item["filename"],
                        relative_path=item["relative_path"],
                        error=error or "Unknown asset download failure",
                    )
                )
                continue

            (destination / item["filename"]).write_bytes(content)
            report.downloaded.append(SelectedAsset(**item))

    return report
