from pathlib import Path

import httpx
import respx

from wiki2md.assets import download_assets, select_assets
from wiki2md.document import Document, ImageBlock
from wiki2md.models import MediaItem


def test_select_assets_prefers_infobox_and_skips_decorative_icons() -> None:
    document = Document(
        title="Andrej Karpathy",
        blocks=[
            ImageBlock(
                title="File:Andrej_Karpathy_2024.jpg",
                alt="Portrait",
                caption="Karpathy in 2024",
                role="infobox",
            ),
            ImageBlock(
                title="File:Audio.svg",
                alt="Audio icon",
                caption=None,
                role="body",
            ),
        ],
    )
    media = [
        MediaItem(
            title="File:Andrej_Karpathy_2024.jpg",
            original_url="https://upload.wikimedia.org/example/andrej-karpathy.jpg",
            mime_type="image/jpeg",
        ),
        MediaItem(
            title="File:Audio.svg",
            original_url="https://upload.wikimedia.org/example/audio.svg",
            mime_type="image/svg+xml",
        ),
    ]

    selected = select_assets(document, media)

    assert [asset.filename for asset in selected] == ["001-infobox.jpg"]
    assert selected[0].relative_path == "assets/001-infobox.jpg"


def test_select_assets_matches_parsoid_file_links_to_media_titles() -> None:
    document = Document(
        title="Andrej Karpathy",
        blocks=[
            ImageBlock(
                title="File:Andrej_Karpathy,_OpenAI.png",
                alt="Portrait",
                caption="Karpathy at Stanford in 2016",
                role="infobox",
            )
        ],
    )
    media = [
        MediaItem(
            title="Andrej Karpathy, OpenAI.png",
            original_url="https://upload.wikimedia.org/example/andrej-karpathy.png",
            mime_type="image/png",
        )
    ]

    selected = select_assets(document, media)

    assert [asset.filename for asset in selected] == ["001-infobox.png"]


@respx.mock
def test_download_assets_writes_binary_files(tmp_path: Path) -> None:
    respx.get("https://upload.wikimedia.org/example/andrej-karpathy.jpg").mock(
        return_value=httpx.Response(200, content=b"jpg-binary")
    )

    assets = [
        {
            "title": "File:Andrej_Karpathy_2024.jpg",
            "source_url": "https://upload.wikimedia.org/example/andrej-karpathy.jpg",
            "filename": "001-infobox.jpg",
            "relative_path": "assets/001-infobox.jpg",
        }
    ]

    download_assets(assets, tmp_path, user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)")

    assert (tmp_path / "001-infobox.jpg").read_bytes() == b"jpg-binary"
