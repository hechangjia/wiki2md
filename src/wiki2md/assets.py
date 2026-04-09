import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from wiki2md.document import Document, ImageBlock
from wiki2md.errors import FetchError
from wiki2md.models import MediaItem, SelectedAsset

IGNORED_TITLES = {"audio.svg", "loudspeaker.svg"}


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


def download_assets(
    assets: list[SelectedAsset] | list[dict],
    destination: Path,
    user_agent: str,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": user_agent},
        timeout=20.0,
    ) as client:
        for asset in assets:
            item = asset if isinstance(asset, dict) else asset.model_dump()

            try:
                response = client.get(item["source_url"])
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise FetchError(f"Failed to download asset: {item['source_url']}") from exc

            (destination / item["filename"]).write_bytes(response.content)
