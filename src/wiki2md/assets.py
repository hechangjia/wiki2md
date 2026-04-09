import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import httpx

from wiki2md.document import Document, ImageBlock
from wiki2md.errors import FetchError
from wiki2md.models import MediaItem, SelectedAsset

IGNORED_TITLES = {"file:audio.svg", "file:loudspeaker.svg"}


def _guess_extension(source_url: str, mime_type: str | None) -> str:
    suffix = Path(urlparse(source_url).path).suffix
    if suffix:
        return suffix.lower()

    if mime_type:
        guessed = mimetypes.guess_extension(mime_type)
        if guessed:
            return guessed

    return ".bin"


def select_assets(document: Document, media: list[MediaItem]) -> list[SelectedAsset]:
    media_by_title = {item.title: item for item in media}
    selected: list[SelectedAsset] = []
    counter = 1

    for block in document.blocks:
        if not isinstance(block, ImageBlock):
            continue

        key = block.title.casefold()
        if key in IGNORED_TITLES:
            continue

        media_item = media_by_title.get(block.title)
        if media_item is None or not media_item.original_url:
            continue

        if (media_item.mime_type or "").startswith("image/svg") and "audio" in key:
            continue

        role = "infobox" if block.role == "infobox" else "image"
        ext = _guess_extension(media_item.original_url, media_item.mime_type)
        filename = f"{counter:03d}-{role}{ext}"
        selected.append(
            SelectedAsset(
                title=block.title,
                source_url=media_item.original_url,
                filename=filename,
                relative_path=f"assets/{filename}",
            )
        )
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
