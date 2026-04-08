# wiki2md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `wiki2md`, a Python CLI and library that converts English-first, Chinese-supported Wikipedia person article URLs into clean local Markdown artifacts with metadata and downloaded images.

**Architecture:** Use a deterministic pipeline: resolve Wikipedia URLs, fetch article HTML and media metadata from each language site's MediaWiki REST API, normalize the HTML into a stable internal document model, render Markdown, download selected assets locally, and write `article.md`, `meta.json`, and `assets/` atomically. Keep the CLI thin by delegating all work to a reusable `Wiki2MdService`.

**Tech Stack:** Python 3.12, `uv`, `typer`, `httpx`, `beautifulsoup4`, `pydantic`, `PyYAML`, `pytest`, `respx`, `ruff`

---

## File Structure

- `pyproject.toml`: package metadata, dependencies, CLI entry point, pytest and ruff config
- `README.md`: installation, commands, output contract, and examples
- `CHANGELOG.md`: release notes starting at `0.1.0`
- `LICENSE`: MIT license text
- `.github/workflows/ci.yml`: lint, test, and build automation
- `src/wiki2md/__init__.py`: package version and top-level exports
- `src/wiki2md/errors.py`: typed exceptions for invalid input, fetch, parse, and write failures
- `src/wiki2md/models.py`: shared pydantic models for URL resolution, fetched payloads, metadata, and conversion results
- `src/wiki2md/urls.py`: Wikipedia URL parsing, language detection, namespace rejection, and slug generation
- `src/wiki2md/client.py`: MediaWiki REST API client for article metadata, HTML, media links, and file details
- `src/wiki2md/document.py`: internal normalized document model used after HTML cleanup
- `src/wiki2md/normalize.py`: HTML cleanup and conversion into the internal document model
- `src/wiki2md/render_markdown.py`: deterministic Markdown and frontmatter renderer
- `src/wiki2md/assets.py`: image selection, deterministic asset naming, and download logic
- `src/wiki2md/writer.py`: atomic artifact writing for `article.md`, `meta.json`, and `assets/`
- `src/wiki2md/service.py`: orchestration layer for `inspect_url()` and `convert_url()`
- `src/wiki2md/cli.py`: Typer CLI commands `convert`, `inspect`, and `batch`
- `tests/test_cli_smoke.py`: package bootstrapping smoke test
- `tests/test_urls.py`: URL resolution and unsupported page coverage
- `tests/test_client.py`: API fetching tests with local fixtures and mocked HTTP responses
- `tests/test_normalize.py`: HTML normalization tests on representative page fragments
- `tests/test_render_markdown.py`: Markdown rendering tests
- `tests/test_assets.py`: asset selection and image download tests
- `tests/test_writer.py`: artifact writing tests
- `tests/test_service.py`: orchestration tests
- `tests/test_cli.py`: CLI behavior and argument handling tests
- `tests/test_project_docs.py`: docs and examples smoke tests
- `tests/fixtures/responses/andrej_bare.json`: sample `/page/{title}/bare` response
- `tests/fixtures/responses/andrej_media.json`: sample `/page/{title}/links/media` response
- `tests/fixtures/responses/andrej_html.html`: sample `/page/{title}/html` response
- `tests/fixtures/html/person_fragment.html`: reduced article fragment for normalization tests
- `tests/fixtures/html/person_fragment_zh.html`: reduced Chinese article fragment for normalization tests
- `examples/andrej-karpathy/article.md`: sample generated Markdown artifact
- `examples/andrej-karpathy/meta.json`: sample metadata artifact

### Task 1: Bootstrap The Package And CLI Shell

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/wiki2md/__init__.py`
- Create: `src/wiki2md/cli.py`
- Test: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from typer.testing import CliRunner

from wiki2md.cli import app


runner = CliRunner()


def test_cli_help_shows_primary_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "convert" in result.stdout
    assert "inspect" in result.stdout
    assert "batch" in result.stdout
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `uv run pytest tests/test_cli_smoke.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'wiki2md'`

- [ ] **Step 3: Create the package scaffold and minimal Typer app**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "wiki2md"
version = "0.1.0"
description = "Convert Wikipedia articles into clean Markdown artifacts for AI workflows."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [
  { name = "BruceChia" },
]
dependencies = [
  "beautifulsoup4>=4.12",
  "httpx>=0.28",
  "pydantic>=2.11",
  "PyYAML>=6.0",
  "typer>=0.16",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "respx>=0.22",
  "ruff>=0.11",
]

[project.scripts]
wiki2md = "wiki2md.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I"]
```

```markdown
# README.md
# wiki2md

Convert Wikipedia person articles into clean Markdown artifacts with local images and structured metadata.
```

```python
# src/wiki2md/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# src/wiki2md/cli.py
import typer


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Convert Wikipedia articles into clean Markdown artifacts.",
)


@app.command()
def convert(url: str) -> None:
    """Convert a Wikipedia article URL into local Markdown artifacts."""
    typer.echo(f"convert not implemented yet: {url}")
    raise typer.Exit(code=1)


@app.command()
def inspect(url: str) -> None:
    """Inspect a Wikipedia article URL without writing files."""
    typer.echo(f"inspect not implemented yet: {url}")
    raise typer.Exit(code=1)


@app.command()
def batch(file: str) -> None:
    """Process a text file containing one Wikipedia URL per line."""
    typer.echo(f"batch not implemented yet: {file}")
    raise typer.Exit(code=1)
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `uv sync --extra dev && uv run pytest tests/test_cli_smoke.py -v`

Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src/wiki2md/__init__.py src/wiki2md/cli.py tests/test_cli_smoke.py
git commit -m "feat: bootstrap wiki2md package"
```

### Task 2: Implement URL Resolution, Slugging, And Typed Errors

**Files:**
- Create: `src/wiki2md/errors.py`
- Create: `src/wiki2md/models.py`
- Create: `src/wiki2md/urls.py`
- Test: `tests/test_urls.py`

- [ ] **Step 1: Write failing URL resolution tests**

```python
import pytest

from wiki2md.errors import InvalidWikipediaUrlError, UnsupportedPageError
from wiki2md.urls import resolve_wikipedia_url


def test_resolve_english_article_url() -> None:
    result = resolve_wikipedia_url("https://en.wikipedia.org/wiki/Andrej_Karpathy")

    assert result.lang == "en"
    assert result.title == "Andrej_Karpathy"
    assert result.slug == "andrej-karpathy"
    assert result.normalized_url.endswith("/wiki/Andrej_Karpathy")


def test_resolve_chinese_article_url() -> None:
    result = resolve_wikipedia_url(
        "https://zh.wikipedia.org/wiki/%E8%89%BE%E4%BC%A6%C2%B7%E5%9B%BE%E7%81%B5"
    )

    assert result.lang == "zh"
    assert result.title == "艾伦·图灵"
    assert result.slug == "艾伦-图灵"


def test_reject_non_wikipedia_host() -> None:
    with pytest.raises(InvalidWikipediaUrlError):
        resolve_wikipedia_url("https://example.com/wiki/Andrej_Karpathy")


def test_reject_unsupported_namespace() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://en.wikipedia.org/wiki/Category:Machine_learning")


def test_reject_list_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://en.wikipedia.org/wiki/List_of_computer_scientists")


def test_reject_disambiguation_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://en.wikipedia.org/wiki/Mercury_(disambiguation)")
```

- [ ] **Step 2: Run the URL tests to verify they fail**

Run: `uv run pytest tests/test_urls.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wiki2md.errors` or `wiki2md.urls`

- [ ] **Step 3: Implement URL parsing, shared models, and typed errors**

```python
# src/wiki2md/errors.py
class Wiki2MdError(Exception):
    """Base exception for all project-specific failures."""


class InvalidWikipediaUrlError(Wiki2MdError):
    """Raised when a URL is not a supported Wikipedia article URL."""


class UnsupportedPageError(Wiki2MdError):
    """Raised when a URL points to a page type outside the v1 scope."""


class FetchError(Wiki2MdError):
    """Raised when Wikipedia data cannot be fetched successfully."""


class ParseError(Wiki2MdError):
    """Raised when article HTML cannot be normalized safely."""


class WriteError(Wiki2MdError):
    """Raised when output artifacts cannot be written safely."""
```

```python
# src/wiki2md/models.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SupportedLang = Literal["en", "zh"]


class UrlResolution(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_url: str
    normalized_url: str
    lang: SupportedLang
    title: str
    slug: str


class MediaItem(BaseModel):
    title: str
    original_url: str | None = None
    thumbnail_url: str | None = None
    mime_type: str | None = None


class FetchedArticle(BaseModel):
    resolution: UrlResolution
    canonical_title: str
    pageid: int | None = None
    revid: int | None = None
    html: str
    media: list[MediaItem] = Field(default_factory=list)


class SelectedAsset(BaseModel):
    title: str
    source_url: str
    filename: str
    relative_path: str


class ArticleMetadata(BaseModel):
    title: str
    source_url: str
    source_lang: SupportedLang
    source_type: Literal["wikipedia"] = "wikipedia"
    retrieved_at: datetime
    page_type: Literal["person"] = "person"
    pageid: int | None = None
    revid: int | None = None
    image_manifest: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    cleanup_stats: dict[str, int] = Field(default_factory=dict)


class InspectionResult(BaseModel):
    resolution: UrlResolution
    pageid: int | None = None
    revid: int | None = None
    media_count: int = 0


class ConversionResult(BaseModel):
    output_dir: str
    article_path: str
    meta_path: str
    asset_count: int
    warnings: list[str] = Field(default_factory=list)
```

```python
# src/wiki2md/urls.py
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

    if title.startswith(UNSUPPORTED_TITLE_PREFIXES) or title.endswith(DISAMBIGUATION_SUFFIX):
        raise UnsupportedPageError(f"Unsupported page type: {title}")

    normalized_title = title.replace(" ", "_")
    normalized_url = f"https://{parsed.netloc}/wiki/{quote(normalized_title, safe=':_()')}"

    return UrlResolution(
        source_url=url,
        normalized_url=normalized_url,
        lang=lang,
        title=normalized_title if lang == "en" else title,
        slug=slugify_title(title),
    )
```

- [ ] **Step 4: Run the URL tests to verify they pass**

Run: `uv run pytest tests/test_urls.py -v`

Expected: PASS with `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/errors.py src/wiki2md/models.py src/wiki2md/urls.py tests/test_urls.py
git commit -m "feat: resolve supported wikipedia article urls"
```

### Task 3: Add The MediaWiki REST Client With Fixture-Backed Tests

**Files:**
- Create: `src/wiki2md/client.py`
- Create: `tests/fixtures/responses/andrej_bare.json`
- Create: `tests/fixtures/responses/andrej_media.json`
- Create: `tests/fixtures/responses/andrej_html.html`
- Test: `tests/test_client.py`

- [ ] **Step 1: Write the failing client test and fixture files**

```json
// tests/fixtures/responses/andrej_bare.json
{
  "id": 12345,
  "key": "Andrej_Karpathy",
  "title": "Andrej Karpathy",
  "latest": {
    "id": 67890,
    "timestamp": "2026-04-08T00:00:00Z"
  },
  "html_url": "https://en.wikipedia.org/w/rest.php/v1/page/Andrej_Karpathy/html"
}
```

```json
// tests/fixtures/responses/andrej_media.json
{
  "files": [
    {
      "title": "File:Andrej_Karpathy_2024.jpg",
      "original": {
        "mimetype": "image/jpeg",
        "url": "https://upload.wikimedia.org/example/andrej-karpathy.jpg"
      },
      "thumbnail": {
        "mimetype": "image/jpeg",
        "url": "https://upload.wikimedia.org/example/andrej-karpathy-thumb.jpg"
      }
    },
    {
      "title": "File:Audio.svg",
      "original": {
        "mimetype": "image/svg+xml",
        "url": "https://upload.wikimedia.org/example/audio.svg"
      }
    }
  ]
}
```

```html
<!-- tests/fixtures/responses/andrej_html.html -->
<html>
  <body>
    <h1>Andrej Karpathy</h1>
    <p><b>Andrej Karpathy</b> is a computer scientist.</p>
    <h2>Career</h2>
    <p>He worked at OpenAI and Tesla.</p>
  </body>
</html>
```

```python
import json
from pathlib import Path

import httpx
import respx

from wiki2md.client import MediaWikiClient
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
```

- [ ] **Step 2: Run the client test to verify it fails**

Run: `uv run pytest tests/test_client.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'wiki2md.client'`

- [ ] **Step 3: Implement the MediaWiki REST client**

```python
# src/wiki2md/client.py
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
```

- [ ] **Step 4: Run the client test to verify it passes**

Run: `uv run pytest tests/test_client.py -v`

Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/client.py tests/fixtures/responses/andrej_bare.json tests/fixtures/responses/andrej_media.json tests/fixtures/responses/andrej_html.html tests/test_client.py
git commit -m "feat: fetch wikipedia article payloads"
```

### Task 4: Normalize Rendered HTML Into A Stable Document Model

**Files:**
- Create: `src/wiki2md/document.py`
- Create: `src/wiki2md/normalize.py`
- Create: `tests/fixtures/html/person_fragment.html`
- Create: `tests/fixtures/html/person_fragment_zh.html`
- Test: `tests/test_normalize.py`

- [ ] **Step 1: Write the failing normalizer test and HTML fixture**

```html
<!-- tests/fixtures/html/person_fragment.html -->
<html>
  <body>
    <h1>Andrej Karpathy</h1>
    <table class="infobox">
      <tr>
        <td>
          <a class="mw-file-description" href="/wiki/File:Andrej_Karpathy_2024.jpg">
            <img alt="Andrej Karpathy portrait" src="//upload.wikimedia.org/example/portrait.jpg" />
          </a>
          <div class="infobox-caption">Karpathy in 2024</div>
        </td>
      </tr>
    </table>
    <p><b>Andrej Karpathy</b> is a Slovak-Canadian computer scientist.<sup class="reference">[1]</sup></p>
    <div class="mw-editsection">edit</div>
    <h2>Career</h2>
    <p>Karpathy worked at OpenAI and Tesla.</p>
    <ul>
      <li>OpenAI</li>
      <li>Tesla</li>
    </ul>
    <div class="navbox">This is noise.</div>
    <h2>References</h2>
    <ol class="references">
      <li>Reference number one.</li>
    </ol>
  </body>
</html>
```

```html
<!-- tests/fixtures/html/person_fragment_zh.html -->
<html>
  <body>
    <h1>艾伦·图灵</h1>
    <p><b>艾伦·图灵</b>是英国数学家、计算机科学先驱。</p>
    <h2>生平</h2>
    <p>图灵在第二次世界大战期间参与密码分析工作。</p>
  </body>
</html>
```

```python
from pathlib import Path

from wiki2md.document import Document, HeadingBlock, ImageBlock, ListBlock, ParagraphBlock
from wiki2md.models import FetchedArticle, UrlResolution
from wiki2md.normalize import normalize_article


FIXTURE = Path(__file__).parent / "fixtures" / "html" / "person_fragment.html"
FIXTURE_ZH = Path(__file__).parent / "fixtures" / "html" / "person_fragment_zh.html"


def test_normalize_article_extracts_summary_blocks_images_and_references() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
            normalized_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
            lang="en",
            title="Andrej_Karpathy",
            slug="andrej-karpathy",
        ),
        canonical_title="Andrej Karpathy",
        pageid=12345,
        revid=67890,
        html=FIXTURE.read_text(encoding="utf-8"),
        media=[],
    )

    document = normalize_article(article)

    assert isinstance(document, Document)
    assert document.title == "Andrej Karpathy"
    assert document.summary == ["Andrej Karpathy is a Slovak-Canadian computer scientist.[1]"]
    assert document.references == ["Reference number one."]
    assert any(isinstance(block, ImageBlock) and block.role == "infobox" for block in document.blocks)
    assert any(isinstance(block, HeadingBlock) and block.text == "Career" for block in document.blocks)
    assert any(isinstance(block, ParagraphBlock) and "Tesla" in block.text for block in document.blocks)
    assert any(isinstance(block, ListBlock) and block.items == ["OpenAI", "Tesla"] for block in document.blocks)


def test_normalize_article_preserves_chinese_text() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://zh.wikipedia.org/wiki/%E8%89%BE%E4%BC%A6%C2%B7%E5%9B%BE%E7%81%B5",
            normalized_url="https://zh.wikipedia.org/wiki/%E8%89%BE%E4%BC%A6%C2%B7%E5%9B%BE%E7%81%B5",
            lang="zh",
            title="艾伦·图灵",
            slug="艾伦-图灵",
        ),
        canonical_title="艾伦·图灵",
        pageid=22345,
        revid=77890,
        html=FIXTURE_ZH.read_text(encoding="utf-8"),
        media=[],
    )

    document = normalize_article(article)

    assert document.title == "艾伦·图灵"
    assert document.summary == ["艾伦·图灵 是英国数学家、计算机科学先驱。"]
    assert any(isinstance(block, HeadingBlock) and block.text == "生平" for block in document.blocks)
    assert any(isinstance(block, ParagraphBlock) and "密码分析" in block.text for block in document.blocks)
```

- [ ] **Step 2: Run the normalizer test to verify it fails**

Run: `uv run pytest tests/test_normalize.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wiki2md.document` or `wiki2md.normalize`

- [ ] **Step 3: Implement the document model and HTML normalizer**

```python
# src/wiki2md/document.py
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ParagraphBlock(BaseModel):
    kind: Literal["paragraph"] = "paragraph"
    text: str


class HeadingBlock(BaseModel):
    kind: Literal["heading"] = "heading"
    level: int
    text: str


class ListBlock(BaseModel):
    kind: Literal["list"] = "list"
    ordered: bool
    items: list[str]


class ImageBlock(BaseModel):
    kind: Literal["image"] = "image"
    title: str
    alt: str
    caption: str | None = None
    role: Literal["infobox", "body"] = "body"


DocumentBlock = Annotated[
    ParagraphBlock | HeadingBlock | ListBlock | ImageBlock,
    Field(discriminator="kind"),
]


class Document(BaseModel):
    title: str
    summary: list[str] = Field(default_factory=list)
    blocks: list[DocumentBlock] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

```python
# src/wiki2md/normalize.py
from bs4 import BeautifulSoup, Tag

from wiki2md.document import Document, HeadingBlock, ImageBlock, ListBlock, ParagraphBlock
from wiki2md.errors import ParseError
from wiki2md.models import FetchedArticle


NOISE_SELECTORS = [
    ".mw-editsection",
    ".navbox",
    ".metadata",
    ".noprint",
    ".mw-empty-elt",
]


def _clean_text(node: Tag) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _extract_image_block(node: Tag, role: str) -> ImageBlock | None:
    anchor = node.select_one("a.mw-file-description[href^='/wiki/File:']")
    image = node.select_one("img")
    if anchor is None or image is None:
        return None

    title = anchor["href"].removeprefix("/wiki/")
    caption_node = node.select_one(".infobox-caption, figcaption")
    caption = _clean_text(caption_node) if caption_node else None

    return ImageBlock(
        title=title,
        alt=image.get("alt", "").strip(),
        caption=caption,
        role=role,  # type: ignore[arg-type]
    )


def normalize_article(article: FetchedArticle) -> Document:
    soup = BeautifulSoup(article.html, "html.parser")

    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    body = soup.body or soup
    title_node = body.find("h1")
    if title_node is None:
        raise ParseError("Expected an <h1> title in the article HTML.")

    document = Document(title=_clean_text(title_node))

    infobox = body.select_one("table.infobox")
    if infobox is not None:
        image_block = _extract_image_block(infobox, role="infobox")
        if image_block is not None:
            document.blocks.append(image_block)

    for node in body.find_all(["h2", "h3", "p", "ul", "ol", "figure"], recursive=True):
        if node.find_parent(["table"]) is not None and node.find_parent("table", class_="infobox") is not None:
            continue

        if node.name == "p":
            text = _clean_text(node)
            if text:
                if not document.summary:
                    document.summary.append(text)
                else:
                    document.blocks.append(ParagraphBlock(text=text))
        elif node.name in {"h2", "h3"}:
            heading_text = _clean_text(node)
            if heading_text.lower() == "references":
                continue
            document.blocks.append(HeadingBlock(level=2 if node.name == "h2" else 3, text=heading_text))
        elif node.name in {"ul", "ol"} and "references" not in (node.get("class") or []):
            items = [_clean_text(item) for item in node.find_all("li", recursive=False)]
            if items:
                document.blocks.append(ListBlock(ordered=node.name == "ol", items=items))
        elif node.name == "figure":
            image_block = _extract_image_block(node, role="body")
            if image_block is not None:
                document.blocks.append(image_block)

    for item in body.select("ol.references > li"):
        text = _clean_text(item)
        if text:
            document.references.append(text)

    if not document.summary:
        document.warnings.append("No lead summary paragraph detected.")

    return document
```

- [ ] **Step 4: Run the normalizer test to verify it passes**

Run: `uv run pytest tests/test_normalize.py -v`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/document.py src/wiki2md/normalize.py tests/fixtures/html/person_fragment.html tests/fixtures/html/person_fragment_zh.html tests/test_normalize.py
git commit -m "feat: normalize wikipedia html into document blocks"
```

### Task 5: Render Deterministic Markdown With Frontmatter And Compressed References

**Files:**
- Create: `src/wiki2md/render_markdown.py`
- Test: `tests/test_render_markdown.py`

- [ ] **Step 1: Write the failing Markdown renderer test**

```python
from datetime import UTC, datetime

from wiki2md.document import Document, HeadingBlock, ImageBlock, ListBlock, ParagraphBlock
from wiki2md.models import ArticleMetadata
from wiki2md.render_markdown import render_markdown


def build_metadata() -> ArticleMetadata:
    return ArticleMetadata(
        title="Andrej Karpathy",
        source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        source_lang="en",
        retrieved_at=datetime(2026, 4, 8, tzinfo=UTC),
        pageid=12345,
        revid=67890,
    )


def test_render_markdown_outputs_frontmatter_body_and_references() -> None:
    document = Document(
        title="Andrej Karpathy",
        summary=["Andrej Karpathy is a computer scientist.[1]"],
        blocks=[
            ImageBlock(
                title="File:Andrej_Karpathy_2024.jpg",
                alt="Andrej Karpathy portrait",
                caption="Karpathy in 2024",
                role="infobox",
            ),
            HeadingBlock(level=2, text="Career"),
            ParagraphBlock(text="Karpathy worked at OpenAI and Tesla."),
            ListBlock(ordered=False, items=["OpenAI", "Tesla"]),
        ],
        references=["Reference number one."],
    )

    markdown = render_markdown(
        document,
        build_metadata(),
        {"File:Andrej_Karpathy_2024.jpg": "assets/001-infobox.jpg"},
    )

    assert markdown.startswith("---\n")
    assert "source_url: https://en.wikipedia.org/wiki/Andrej_Karpathy" in markdown
    assert "# Andrej Karpathy" in markdown
    assert "![Andrej Karpathy portrait](./assets/001-infobox.jpg)" in markdown
    assert "Karpathy in 2024" in markdown
    assert "## Career" in markdown
    assert "- OpenAI" in markdown
    assert "## References" in markdown
    assert "1. Reference number one." in markdown


def test_render_markdown_compresses_long_reference_lists() -> None:
    document = Document(
        title="Andrej Karpathy",
        summary=["Andrej Karpathy is a computer scientist."],
        references=[f"Reference {index}" for index in range(1, 8)],
    )

    markdown = render_markdown(document, build_metadata(), {})

    assert "1. Reference 1" in markdown
    assert "5. Reference 5" in markdown
    assert "_2 additional reference(s) omitted for brevity._" in markdown
```

- [ ] **Step 2: Run the renderer test to verify it fails**

Run: `uv run pytest tests/test_render_markdown.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'wiki2md.render_markdown'`

- [ ] **Step 3: Implement the Markdown renderer**

```python
# src/wiki2md/render_markdown.py
from typing import Iterable

import yaml

from wiki2md.document import Document, HeadingBlock, ImageBlock, ListBlock, ParagraphBlock
from wiki2md.models import ArticleMetadata

MAX_REFERENCES = 5


def _render_frontmatter(metadata: ArticleMetadata) -> str:
    payload = {
        "title": metadata.title,
        "source_url": metadata.source_url,
        "source_lang": metadata.source_lang,
        "source_type": metadata.source_type,
        "retrieved_at": metadata.retrieved_at.isoformat(),
        "page_type": metadata.page_type,
        "pageid": metadata.pageid,
        "revid": metadata.revid,
    }
    return f"---\n{yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()}\n---"


def _render_list(items: Iterable[str], ordered: bool) -> list[str]:
    lines = []
    for index, item in enumerate(items, start=1):
        prefix = f"{index}." if ordered else "-"
        lines.append(f"{prefix} {item}")
    return lines


def render_markdown(
    document: Document,
    metadata: ArticleMetadata,
    asset_map: dict[str, str],
) -> str:
    lines: list[str] = [_render_frontmatter(metadata), "", f"# {document.title}", ""]

    for paragraph in document.summary:
        lines.append(paragraph)
        lines.append("")

    for block in document.blocks:
        if isinstance(block, HeadingBlock):
            lines.append(f"{'#' * block.level} {block.text}")
            lines.append("")
        elif isinstance(block, ParagraphBlock):
            lines.append(block.text)
            lines.append("")
        elif isinstance(block, ListBlock):
            lines.extend(_render_list(block.items, ordered=block.ordered))
            lines.append("")
        elif isinstance(block, ImageBlock):
            relative_path = asset_map.get(block.title)
            if relative_path:
                lines.append(f"![{block.alt}](./{relative_path})")
                if block.caption:
                    lines.append(f"*{block.caption}*")
                lines.append("")

    if document.references:
        lines.append("## References")
        lines.append("")
        kept_references = document.references[:MAX_REFERENCES]
        lines.extend(_render_list(kept_references, ordered=True))
        omitted = len(document.references) - len(kept_references)
        if omitted > 0:
            lines.append(f"_{omitted} additional reference(s) omitted for brevity._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run the renderer test to verify it passes**

Run: `uv run pytest tests/test_render_markdown.py -v`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/render_markdown.py tests/test_render_markdown.py
git commit -m "feat: render normalized documents as markdown"
```

### Task 6: Select Meaningful Images And Download Them Locally

**Files:**
- Create: `src/wiki2md/assets.py`
- Test: `tests/test_assets.py`

- [ ] **Step 1: Write failing asset selection and download tests**

```python
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
```

- [ ] **Step 2: Run the asset tests to verify they fail**

Run: `uv run pytest tests/test_assets.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'wiki2md.assets'`

- [ ] **Step 3: Implement asset selection and local downloads**

```python
# src/wiki2md/assets.py
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
```

- [ ] **Step 4: Run the asset tests to verify they pass**

Run: `uv run pytest tests/test_assets.py -v`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/assets.py tests/test_assets.py
git commit -m "feat: download selected wikipedia assets locally"
```

### Task 7: Write Artifacts Atomically And Add The Conversion Service

**Files:**
- Create: `src/wiki2md/writer.py`
- Create: `src/wiki2md/service.py`
- Test: `tests/test_writer.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Write failing writer and orchestration tests**

```python
import json
from datetime import UTC, datetime
from pathlib import Path

from wiki2md.models import ArticleMetadata, UrlResolution
from wiki2md.writer import write_bundle


def test_write_bundle_creates_expected_artifacts(tmp_path: Path) -> None:
    staging_assets = tmp_path / "staging-assets"
    staging_assets.mkdir()
    (staging_assets / "001-infobox.jpg").write_bytes(b"image-binary")

    resolution = UrlResolution(
        source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        normalized_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        lang="en",
        title="Andrej_Karpathy",
        slug="andrej-karpathy",
    )
    metadata = ArticleMetadata(
        title="Andrej Karpathy",
        source_url=resolution.source_url,
        source_lang="en",
        retrieved_at=datetime(2026, 4, 8, tzinfo=UTC),
        pageid=12345,
        revid=67890,
        image_manifest=[{"title": "File:Andrej_Karpathy_2024.jpg", "path": "assets/001-infobox.jpg"}],
        cleanup_stats={"blocks": 3, "references": 1, "images_selected": 1},
    )

    result = write_bundle(
        output_root=tmp_path / "output",
        resolution=resolution,
        markdown="# Andrej Karpathy\n",
        metadata=metadata,
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    article_path = Path(result.article_path)
    meta_path = Path(result.meta_path)

    assert article_path.exists()
    assert meta_path.exists()
    assert (Path(result.output_dir) / "assets" / "001-infobox.jpg").exists()
    assert json.loads(meta_path.read_text(encoding="utf-8"))["source_lang"] == "en"
```

```python
from pathlib import Path

from wiki2md.document import Document, ParagraphBlock
from wiki2md.models import ConversionResult
from wiki2md.service import Wiki2MdService


class FakeClient:
    user_agent = "wiki2md-test-bot/0.1 (2136414704@qq.com)"

    def fetch_article(self, resolution):
        from wiki2md.models import FetchedArticle

        return FetchedArticle(
            resolution=resolution,
            canonical_title="Andrej Karpathy",
            pageid=12345,
            revid=67890,
            html="<html></html>",
            media=[],
        )


def test_convert_url_orchestrates_pipeline(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")

    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(
            title="Andrej Karpathy",
            summary=["Andrej Karpathy is a computer scientist."],
            blocks=[ParagraphBlock(text="Karpathy worked at OpenAI.")],
            references=[],
        ),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr("wiki2md.service.download_assets", lambda assets, destination, user_agent: None)
    monkeypatch.setattr(
        "wiki2md.service.render_markdown",
        lambda document, metadata, asset_map: "# Andrej Karpathy\n",
    )

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Andrej_Karpathy",
        overwrite=False,
    )

    assert isinstance(result, ConversionResult)
    assert Path(result.article_path).exists()
    assert result.asset_count == 0
```

- [ ] **Step 2: Run the writer and service tests to verify they fail**

Run: `uv run pytest tests/test_writer.py tests/test_service.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wiki2md.writer` or `wiki2md.service`

- [ ] **Step 3: Implement atomic writing and the orchestration service**

```python
# src/wiki2md/writer.py
import json
import shutil
from pathlib import Path

from wiki2md.errors import WriteError
from wiki2md.models import ArticleMetadata, ConversionResult, UrlResolution


def write_bundle(
    output_root: Path,
    resolution: UrlResolution,
    markdown: str,
    metadata: ArticleMetadata,
    staging_assets_dir: Path,
    overwrite: bool,
) -> ConversionResult:
    final_dir = output_root / "people" / resolution.slug
    temp_dir = output_root / ".tmp" / resolution.slug

    temp_dir.parent.mkdir(parents=True, exist_ok=True)
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    if final_dir.exists():
        if not overwrite:
            raise WriteError(f"Output already exists: {final_dir}")
        shutil.rmtree(final_dir)

    article_path = temp_dir / "article.md"
    meta_path = temp_dir / "meta.json"
    assets_path = temp_dir / "assets"

    article_path.write_text(markdown, encoding="utf-8")
    meta_path.write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if staging_assets_dir.exists():
        shutil.copytree(staging_assets_dir, assets_path)
    else:
        assets_path.mkdir()

    final_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.replace(final_dir)

    return ConversionResult(
        output_dir=str(final_dir),
        article_path=str(final_dir / "article.md"),
        meta_path=str(final_dir / "meta.json"),
        asset_count=len(list((final_dir / "assets").iterdir())),
        warnings=metadata.warnings,
    )
```

```python
# src/wiki2md/service.py
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from wiki2md.assets import download_assets, select_assets
from wiki2md.client import MediaWikiClient
from wiki2md.models import ArticleMetadata, InspectionResult
from wiki2md.normalize import normalize_article
from wiki2md.render_markdown import render_markdown
from wiki2md.urls import resolve_wikipedia_url
from wiki2md.writer import write_bundle


class Wiki2MdService:
    def __init__(self, client: MediaWikiClient, output_root: Path) -> None:
        self.client = client
        self.output_root = output_root

    def inspect_url(self, url: str) -> InspectionResult:
        resolution = resolve_wikipedia_url(url)
        article = self.client.fetch_article(resolution)
        return InspectionResult(
            resolution=resolution,
            pageid=article.pageid,
            revid=article.revid,
            media_count=len(article.media),
        )

    def convert_url(self, url: str, overwrite: bool = False):
        resolution = resolve_wikipedia_url(url)
        article = self.client.fetch_article(resolution)
        document = normalize_article(article)
        selected_assets = select_assets(document, article.media)

        staging_root = Path(tempfile.mkdtemp(prefix="wiki2md-"))
        staging_assets_dir = staging_root / "assets"

        try:
            download_assets(selected_assets, staging_assets_dir, user_agent=self.client.user_agent)

            metadata = ArticleMetadata(
                title=article.canonical_title,
                source_url=resolution.normalized_url,
                source_lang=resolution.lang,
                retrieved_at=datetime.now(UTC),
                pageid=article.pageid,
                revid=article.revid,
                image_manifest=[
                    {"title": asset.title, "path": asset.relative_path} for asset in selected_assets
                ],
                warnings=document.warnings,
                cleanup_stats={
                    "blocks": len(document.blocks),
                    "references": len(document.references),
                    "images_selected": len(selected_assets),
                },
            )
            markdown = render_markdown(
                document,
                metadata,
                {asset.title: asset.relative_path for asset in selected_assets},
            )

            return write_bundle(
                output_root=self.output_root,
                resolution=resolution,
                markdown=markdown,
                metadata=metadata,
                staging_assets_dir=staging_assets_dir,
                overwrite=overwrite,
            )
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
```

- [ ] **Step 4: Run the writer and service tests to verify they pass**

Run: `uv run pytest tests/test_writer.py tests/test_service.py -v`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/writer.py src/wiki2md/service.py tests/test_writer.py tests/test_service.py
git commit -m "feat: write wiki2md artifacts atomically"
```

### Task 8: Replace The Stub CLI With Real `convert`, `inspect`, And `batch` Commands

**Files:**
- Modify: `src/wiki2md/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI behavior tests**

```python
import json
from pathlib import Path

from typer.testing import CliRunner

from wiki2md.cli import app
from wiki2md.models import ConversionResult, InspectionResult, UrlResolution


runner = CliRunner()


class FakeService:
    def __init__(self, output_root):
        self.output_root = output_root

    def convert_url(self, url: str, overwrite: bool = False) -> ConversionResult:
        output_dir = Path(self.output_root) / "people" / "andrej-karpathy"
        output_dir.mkdir(parents=True, exist_ok=True)
        article_path = output_dir / "article.md"
        meta_path = output_dir / "meta.json"
        article_path.write_text("# Andrej Karpathy\n", encoding="utf-8")
        meta_path.write_text("{}", encoding="utf-8")
        return ConversionResult(
            output_dir=str(output_dir),
            article_path=str(article_path),
            meta_path=str(meta_path),
            asset_count=0,
        )

    def inspect_url(self, url: str) -> InspectionResult:
        return InspectionResult(
            resolution=UrlResolution(
                source_url=url,
                normalized_url=url,
                lang="en",
                title="Andrej_Karpathy",
                slug="andrej-karpathy",
            ),
            pageid=12345,
            revid=67890,
            media_count=2,
        )


def test_convert_command_prints_output_location(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))

    result = runner.invoke(
        app,
        [
            "convert",
            "https://en.wikipedia.org/wiki/Andrej_Karpathy",
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    assert "article.md" in result.stdout


def test_inspect_command_prints_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))

    result = runner.invoke(
        app,
        [
            "inspect",
            "https://en.wikipedia.org/wiki/Andrej_Karpathy",
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["media_count"] == 2


def test_batch_command_processes_non_empty_lines(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(
        "# comment\nhttps://en.wikipedia.org/wiki/Andrej_Karpathy\n\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "batch",
            str(batch_file),
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    assert "Processed 1 URL(s)." in result.stdout
```

- [ ] **Step 2: Run the CLI tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`

Expected: FAIL because the stub commands print placeholder text instead of real output

- [ ] **Step 3: Implement the real CLI commands**

```python
# src/wiki2md/cli.py
import json
from pathlib import Path

import typer

from wiki2md.client import MediaWikiClient
from wiki2md.service import Wiki2MdService


DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_USER_AGENT = "wiki2md-bot/0.1 (2136414704@qq.com)"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Convert Wikipedia articles into clean Markdown artifacts.",
)


def build_service(output_dir: Path) -> Wiki2MdService:
    client = MediaWikiClient(user_agent=DEFAULT_USER_AGENT)
    return Wiki2MdService(client=client, output_root=output_dir)


@app.command()
def convert(
    url: str,
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Convert a Wikipedia article URL into local Markdown artifacts."""
    result = build_service(output_dir).convert_url(url, overwrite=overwrite)
    typer.echo(result.article_path)


@app.command()
def inspect(
    url: str,
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
) -> None:
    """Inspect a Wikipedia article URL without writing files."""
    result = build_service(output_dir).inspect_url(url)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


@app.command()
def batch(
    file: Path,
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Process a text file containing one Wikipedia URL per line."""
    service = build_service(output_dir)
    processed = 0

    for raw_line in file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        service.convert_url(line, overwrite=overwrite)
        processed += 1

    typer.echo(f"Processed {processed} URL(s).")
```

- [ ] **Step 4: Run the CLI tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`

Expected: PASS with `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/cli.py tests/test_cli.py
git commit -m "feat: add wiki2md convert inspect and batch commands"
```

### Task 9: Add Open-Source Docs, Examples, And CI Automation

**Files:**
- Modify: `README.md`
- Create: `CHANGELOG.md`
- Create: `LICENSE`
- Create: `.github/workflows/ci.yml`
- Create: `examples/andrej-karpathy/article.md`
- Create: `examples/andrej-karpathy/meta.json`
- Test: `tests/test_project_docs.py`

- [ ] **Step 1: Write failing docs smoke tests**

```python
from pathlib import Path


def test_readme_mentions_primary_cli_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "wiki2md convert <url>" in readme
    assert "wiki2md inspect <url>" in readme
    assert "wiki2md batch <file>" in readme


def test_example_article_has_frontmatter() -> None:
    article = Path("examples/andrej-karpathy/article.md").read_text(encoding="utf-8")

    assert article.startswith("---\n")
    assert "source_url:" in article
```

- [ ] **Step 2: Run the docs smoke tests to verify they fail**

Run: `uv run pytest tests/test_project_docs.py -v`

Expected: FAIL because `README.md` is too minimal and the example artifacts do not exist yet

- [ ] **Step 3: Add the README, examples, changelog, license, and CI workflow**

````markdown
# README.md
# wiki2md

Convert Wikipedia person pages into clean Markdown artifacts with local images and structured metadata.

## Why

`wiki2md` turns noisy Wikipedia article pages into deterministic local files that are easier for people, embeddings pipelines, and retrieval systems to consume.

## Install

```bash
uv sync --extra dev
```

## Commands

```bash
wiki2md convert <url>
wiki2md inspect <url>
wiki2md batch <file>
```

## Example

```bash
wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
```

Output layout:

```text
output/
  people/
    andrej-karpathy/
      article.md
      meta.json
      assets/
```

See `examples/andrej-karpathy/` for a sample artifact layout.
````

```markdown
# CHANGELOG.md
# Changelog

## 0.1.0

- Bootstrap `wiki2md` as a Python package and CLI
- Support English-first, Chinese-supported Wikipedia URL resolution
- Fetch article HTML and media metadata from MediaWiki REST APIs
- Normalize person-page HTML into deterministic Markdown artifacts
- Download selected assets locally and write `article.md` plus `meta.json`
```

```text
# LICENSE
MIT License

Copyright (c) 2026 BruceChia

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

```yaml
# .github/workflows/ci.yml
name: ci

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Setup uv
        uses: astral-sh/setup-uv@v5

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check .

      - name: Test
        run: uv run pytest -q

      - name: Build
        run: uv build
```

```markdown
<!-- examples/andrej-karpathy/article.md -->
---
title: Andrej Karpathy
source_url: https://en.wikipedia.org/wiki/Andrej_Karpathy
source_lang: en
source_type: wikipedia
retrieved_at: 2026-04-08T00:00:00+00:00
page_type: person
pageid: 12345
revid: 67890
---

# Andrej Karpathy

Andrej Karpathy is a computer scientist.

## Career

Karpathy worked at OpenAI and Tesla.
```

```json
// examples/andrej-karpathy/meta.json
{
  "title": "Andrej Karpathy",
  "source_url": "https://en.wikipedia.org/wiki/Andrej_Karpathy",
  "source_lang": "en",
  "source_type": "wikipedia",
  "retrieved_at": "2026-04-08T00:00:00+00:00",
  "page_type": "person",
  "pageid": 12345,
  "revid": 67890,
  "image_manifest": [
    {
      "title": "File:Andrej_Karpathy_2024.jpg",
      "path": "assets/001-infobox.jpg"
    }
  ],
  "warnings": [],
  "cleanup_stats": {
    "blocks": 3,
    "references": 1,
    "images_selected": 1
  }
}
```

- [ ] **Step 4: Run the project-wide verification**

Run: `uv run pytest -q && uv run ruff check . && uv build`

Expected: PASS with all tests green, no lint errors, and a built source distribution plus wheel in `dist/`

- [ ] **Step 5: Commit**

```bash
git add README.md CHANGELOG.md LICENSE .github/workflows/ci.yml examples/andrej-karpathy/article.md examples/andrej-karpathy/meta.json tests/test_project_docs.py
git commit -m "docs: add usage guides examples and ci"
```
