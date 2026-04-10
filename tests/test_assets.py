import time
from pathlib import Path

import httpx
import respx

from wiki2md.assets import download_assets, select_assets
from wiki2md.document import Document, ImageBlock, InfoboxData, InfoboxImage
from wiki2md.models import MediaItem


def test_select_assets_prefers_infobox_and_skips_decorative_icons() -> None:
    document = Document(
        title="Andrej Karpathy",
        infobox=InfoboxData(
            title="Andrej Karpathy",
            image=InfoboxImage(
                title="File:Andrej_Karpathy_2024.jpg",
                path=None,
                alt="Portrait",
                caption="Karpathy in 2024",
            ),
            fields=[],
        ),
        blocks=[
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
        infobox=InfoboxData(
            title="Andrej Karpathy",
            image=InfoboxImage(
                title="File:Andrej_Karpathy,_OpenAI.png",
                alt="Portrait",
                caption="Karpathy at Stanford in 2016",
            ),
            fields=[],
        ),
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

    report = download_assets(
        assets,
        tmp_path,
        user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)",
    )

    assert (tmp_path / "001-infobox.jpg").read_bytes() == b"jpg-binary"
    assert [asset.filename for asset in report.downloaded] == ["001-infobox.jpg"]
    assert report.failures == []


@respx.mock
def test_download_assets_retries_429_then_writes_binary_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(time, "sleep", lambda _: None)
    url = "https://upload.wikimedia.org/example/rate-limited.jpg"
    request = httpx.Request("GET", url)
    route = respx.get(url).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}, request=request),
            httpx.Response(200, content=b"jpg-binary"),
        ]
    )

    assets = [
        {
            "title": "File:Rate_Limited.jpg",
            "source_url": url,
            "filename": "001-infobox.jpg",
            "relative_path": "assets/001-infobox.jpg",
        }
    ]

    report = download_assets(
        assets,
        tmp_path,
        user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)",
    )

    assert route.call_count == 2
    assert (tmp_path / "001-infobox.jpg").read_bytes() == b"jpg-binary"
    assert [asset.filename for asset in report.downloaded] == ["001-infobox.jpg"]
    assert report.failures == []


@respx.mock
def test_download_assets_does_not_retry_404_and_records_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(time, "sleep", lambda _: None)
    url = "https://upload.wikimedia.org/example/missing.jpg"
    route = respx.get(url).mock(
        return_value=httpx.Response(404, request=httpx.Request("GET", url))
    )

    assets = [
        {
            "title": "File:Missing.jpg",
            "source_url": url,
            "filename": "001-infobox.jpg",
            "relative_path": "assets/001-infobox.jpg",
        }
    ]

    report = download_assets(
        assets,
        tmp_path,
        user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)",
    )

    assert route.call_count == 1
    assert not (tmp_path / "001-infobox.jpg").exists()
    assert report.downloaded == []
    assert len(report.failures) == 1
    assert report.failures[0].title == "File:Missing.jpg"
    assert "HTTP 404" in report.failures[0].error
