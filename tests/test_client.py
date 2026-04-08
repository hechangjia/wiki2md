import json
from pathlib import Path

import httpx
import pytest
import respx

from wiki2md.client import MediaWikiClient
from wiki2md.errors import FetchError
from wiki2md.models import UrlResolution

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "responses"


def load_text(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def load_json(name: str) -> dict:
    return json.loads(load_text(name))


@respx.mock
def test_fetch_article_collects_bare_html_and_media() -> None:
    resolution = UrlResolution(
        source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        normalized_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        lang="en",
        title="Andrej_Karpathy",
        slug="andrej-karpathy",
    )
    base = "https://en.wikipedia.org/w/rest.php/v1"

    respx.get(f"{base}/page/Andrej_Karpathy/bare").mock(
        return_value=httpx.Response(200, json=load_json("andrej_bare.json"))
    )
    respx.get(f"{base}/page/Andrej_Karpathy/html").mock(
        return_value=httpx.Response(200, text=load_text("andrej_html.html"))
    )
    respx.get(f"{base}/page/Andrej_Karpathy/links/media").mock(
        return_value=httpx.Response(200, json=load_json("andrej_media.json"))
    )

    article = MediaWikiClient(
        user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)"
    ).fetch_article(resolution)

    assert article.canonical_title == "Andrej Karpathy"
    assert article.pageid == 12345
    assert article.revid == 67890
    assert article.media[0].title == "File:Andrej_Karpathy_2024.jpg"
    assert "<h1>Andrej Karpathy</h1>" in article.html


@respx.mock
def test_fetch_file_normalizes_protocol_relative_urls() -> None:
    base = "https://en.wikipedia.org/w/rest.php/v1"
    respx.get(f"{base}/file/File:Andrej_Karpathy_2024.jpg").mock(
        return_value=httpx.Response(
            200,
            json={
                "title": "File:Andrej_Karpathy_2024.jpg",
                "original": {
                    "mimetype": "image/jpeg",
                    "url": "//upload.wikimedia.org/example/andrej-karpathy.jpg",
                },
                "thumbnail": {
                    "mimetype": "image/jpeg",
                    "url": "//upload.wikimedia.org/example/andrej-karpathy-thumb.jpg",
                },
            },
        )
    )

    media = MediaWikiClient(
        user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)"
    ).fetch_file("en", "File:Andrej_Karpathy_2024.jpg")

    assert media.title == "File:Andrej_Karpathy_2024.jpg"
    assert media.original_url == "https://upload.wikimedia.org/example/andrej-karpathy.jpg"
    assert media.thumbnail_url == "https://upload.wikimedia.org/example/andrej-karpathy-thumb.jpg"
    assert media.mime_type == "image/jpeg"


def test_context_manager_closes_owned_http_client() -> None:
    with MediaWikiClient(user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)") as client:
        assert not client._client.is_closed
    assert client._client.is_closed


def test_close_does_not_close_injected_http_client() -> None:
    injected = httpx.Client()
    try:
        client = MediaWikiClient(
            user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)",
            client=injected,
        )
        client.close()
        assert not injected.is_closed
    finally:
        injected.close()


@respx.mock
def test_fetch_article_raises_fetch_error_on_invalid_json() -> None:
    resolution = UrlResolution(
        source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        normalized_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        lang="en",
        title="Andrej_Karpathy",
        slug="andrej-karpathy",
    )
    base = "https://en.wikipedia.org/w/rest.php/v1"

    respx.get(f"{base}/page/Andrej_Karpathy/bare").mock(
        return_value=httpx.Response(200, text="this-is-not-json")
    )

    with pytest.raises(FetchError, match="JSON"):
        MediaWikiClient(user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)").fetch_article(
            resolution
        )
