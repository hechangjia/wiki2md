# wiki2md Clean Article And References Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove inline Wikipedia citation markers from prose-oriented Markdown output while enriching `references.json` with classified links and a best-effort `primary_url`.

**Architecture:** Keep the existing conversion pipeline intact. Narrow the changes to the document/reference models and the HTML normalizer so `article.md` stays clean-first and `references.json` remains the authoritative structured provenance sidecar. Rendering and writing should continue to be deterministic and rely on model serialization rather than bespoke JSON branching.

**Tech Stack:** Python 3.12+, `uv`, `beautifulsoup4`, `pydantic`, `pytest`, `ruff`

---

## File Structure

- `src/wiki2md/document.py`: extend reference/link models with classification and primary URL support
- `src/wiki2md/normalize.py`: remove inline citation markers from prose and enrich extracted reference links
- `src/wiki2md/writer.py`: continue serializing references sidecar using the richer model shape
- `src/wiki2md/service.py`: pass enriched references through unchanged and keep output contract stable
- `tests/test_normalize.py`: cover prose cleanup plus reference classification/selection
- `tests/test_writer.py`: verify `references.json` contains the richer fields
- `tests/test_service.py`: verify end-to-end conversion writes the richer references payload
- `tests/test_project_docs.py`: keep README/example artifacts aligned with the output contract
- `README.md`: document clean `article.md` behavior and enriched `references.json`
- `examples/andrej-karpathy/references.json`: show the richer sidecar shape

### Task 1: Strip Inline Citation Markers From Prose Blocks

**Files:**
- Modify: `tests/test_normalize.py`
- Modify: `src/wiki2md/normalize.py`

- [ ] **Step 1: Write the failing normalization tests**

```python
def test_normalize_article_strips_inline_citation_markers_from_prose() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>Geoffrey Hinton is a researcher.[8] [9]</p>
              <h2>Career</h2>
              <p>He left Google in 2023.[10]</p>
              <ul>
                <li>Worked at Google.[11]</li>
              </ul>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["Geoffrey Hinton is a researcher."]
    assert document.blocks[1].text == "He left Google in 2023."
    assert document.blocks[2].items == [ListItem(text="Worked at Google.")]


def test_normalize_article_strips_inline_citation_markers_from_chinese_prose() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://zh.wikipedia.org/wiki/%E6%9D%B0%E5%BC%97%E9%87%8C%C2%B7%E8%BE%9B%E9%A1%BF",
            normalized_url="https://zh.wikipedia.org/wiki/%E6%9D%B0%E5%BC%97%E9%87%8C%C2%B7%E8%BE%9B%E9%A1%BF",
            lang="zh",
            title="杰弗里·辛顿",
            slug="杰弗里-辛顿",
        ),
        canonical_title="杰弗里·辛顿",
        html="""
        <html>
          <head><title>杰弗里·辛顿</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>杰弗里·辛顿是计算机科学家。[1] [2]</p>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["杰弗里·辛顿是计算机科学家。"]
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
uv run pytest \
  tests/test_normalize.py::test_normalize_article_strips_inline_citation_markers_from_prose \
  tests/test_normalize.py::test_normalize_article_strips_inline_citation_markers_from_chinese_prose \
  -v
```

Expected: FAIL because the current summary/paragraph/list text still includes citation markers like `[8]` and `[1]`.

- [ ] **Step 3: Implement conservative inline citation cleanup**

```python
# src/wiki2md/normalize.py
_INLINE_CITATION_RUN_RE = re.compile(
    r"(?:\s*\[(?:\d+|note\s+\d+)\])+",
    re.IGNORECASE,
)
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?，。！？；：、])")
_MULTI_SPACE_RE = re.compile(r" {2,}")


def _strip_inline_citation_markers(text: str) -> str:
    cleaned = _INLINE_CITATION_RUN_RE.sub("", text)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def _clean_prose_text(node: Tag) -> str:
    return _strip_inline_citation_markers(_clean_text(node))
```

Apply `_clean_prose_text()` to:

```python
if node.name == "p":
    text = _clean_prose_text(node)
    if text:
        if in_lead:
            document.summary.append(text)
        else:
            document.blocks.append(ParagraphBlock(text=text))
elif node.name in {"ul", "ol"} and "references" not in (node.get("class") or []):
    items = []
    for item in node.find_all("li", recursive=False):
        text = _clean_prose_text(item)
        if not text:
            continue
        items.append(
            ListItem(
                text=text,
                href=_extract_list_item_href(item, article, preserve_list_links),
            )
        )
    if items:
        document.blocks.append(ListBlock(ordered=node.name == "ol", items=items))
```

Do not use `_clean_prose_text()` for reference entries; they should continue to preserve their full textual citation payload.

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:

```bash
uv run pytest \
  tests/test_normalize.py::test_normalize_article_strips_inline_citation_markers_from_prose \
  tests/test_normalize.py::test_normalize_article_strips_inline_citation_markers_from_chinese_prose \
  -v
```

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/normalize.py tests/test_normalize.py
git commit -m "fix: strip inline wikipedia citation markers"
```

### Task 2: Enrich References With Link Kinds And Primary URLs

**Files:**
- Modify: `src/wiki2md/document.py`
- Modify: `src/wiki2md/normalize.py`
- Modify: `tests/test_normalize.py`
- Modify: `tests/test_writer.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write the failing reference-structure tests**

```python
def test_normalize_article_classifies_reference_links_and_selects_primary_url() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            normalized_url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
            lang="en",
            title="Geoffrey_Hinton",
            slug="geoffrey-hinton",
        ),
        canonical_title="Geoffrey Hinton",
        html="""
        <html>
          <head><title>Geoffrey Hinton</title></head>
          <body>
            <section data-mw-section-id="0">
              <p>Geoffrey Hinton is a researcher.</p>
              <h2>References</h2>
              <ol class="references">
                <li id="cite_note-example-1">
                  <span class="mw-cite-backlink"><a href="./Geoffrey_Hinton#cite_ref-example-1">↑</a></span>
                  <cite>
                    Example article.
                    <a href="https://example.com/source">Example source</a>
                    <a href="https://archive.org/details/example-source">Archived copy</a>
                    <a href="./DOI_(identifier)">DOI</a>
                    <a href="https://doi.org/10.1000/example">10.1000/example</a>
                  </cite>
                </li>
              </ol>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.references == [
        ReferenceEntry(
            id="cite_note-example-1",
            text="Example article. Example source Archived copy DOI 10.1000/example",
            primary_url="https://example.com/source",
            links=[
                ReferenceLink(
                    text="Example source",
                    href="https://example.com/source",
                    kind="external",
                ),
                ReferenceLink(
                    text="Archived copy",
                    href="https://archive.org/details/example-source",
                    kind="archive",
                ),
                ReferenceLink(
                    text="DOI",
                    href="https://en.wikipedia.org/wiki/DOI_(identifier)",
                    kind="wiki",
                ),
                ReferenceLink(
                    text="10.1000/example",
                    href="https://doi.org/10.1000/example",
                    kind="identifier",
                ),
            ],
        )
    ]
```

```python
def test_write_bundle_serializes_reference_primary_urls(tmp_path: Path) -> None:
    staging_assets = tmp_path / "staging-assets"
    staging_assets.mkdir()
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
        retrieved_at=datetime(2026, 4, 9, tzinfo=UTC),
    )
    result = write_bundle(
        output_root=tmp_path / "output",
        resolution=resolution,
        markdown="# Andrej Karpathy\n",
        metadata=metadata,
        references=[
            ReferenceEntry(
                id="cite_note-example-1",
                text="Example article.",
                primary_url="https://example.com/source",
                links=[
                    ReferenceLink(
                        text="Example source",
                        href="https://example.com/source",
                        kind="external",
                    )
                ],
            )
        ],
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    payload = json.loads(Path(result.references_path).read_text(encoding="utf-8"))
    assert payload == [
        {
            "id": "cite_note-example-1",
            "text": "Example article.",
            "primary_url": "https://example.com/source",
            "links": [
                {
                    "text": "Example source",
                    "href": "https://example.com/source",
                    "kind": "external",
                }
            ],
        }
    ]
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
uv run pytest \
  tests/test_normalize.py::test_normalize_article_classifies_reference_links_and_selects_primary_url \
  tests/test_writer.py::test_write_bundle_serializes_reference_primary_urls \
  tests/test_service.py::test_convert_url_orchestrates_pipeline \
  -v
```

Expected: FAIL because `ReferenceLink` lacks `kind`, `ReferenceEntry` lacks `primary_url`, and `references.json` does not yet include the richer fields.

- [ ] **Step 3: Implement classified reference links and primary URL selection**

```python
# src/wiki2md/document.py
class ReferenceLink(BaseModel):
    text: str
    href: str
    kind: Literal["external", "wiki", "archive", "identifier", "other"]


class ReferenceEntry(BaseModel):
    id: str | None = None
    text: str
    primary_url: str | None = None
    links: list[ReferenceLink] = Field(default_factory=list)
```

```python
# src/wiki2md/normalize.py
from urllib.parse import urljoin, urlparse

ARCHIVE_HINTS = ("archive.org", "wayback", "webcache")
IDENTIFIER_HINTS = ("doi", "pmid", "arxiv", "oclc", "isbn", "issn", "hdl", "proquest")


def _classify_reference_link(text: str, href: str) -> str:
    parsed = urlparse(href)
    host = parsed.netloc.casefold()
    path = parsed.path.casefold()
    combined = f"{text.casefold()} {host} {path}"

    if any(hint in host for hint in ARCHIVE_HINTS):
        return "archive"
    if "wikipedia.org" in host:
        return "wiki"
    if any(hint in combined for hint in IDENTIFIER_HINTS):
        return "identifier"
    if parsed.scheme in {"http", "https"}:
        return "external"
    return "other"


def _select_primary_url(links: list[ReferenceLink]) -> str | None:
    for preferred in ("external", "archive", "identifier"):
        for link in links:
            if link.kind == preferred:
                return link.href
    return None


def _extract_reference_links(node: Tag, article: FetchedArticle) -> list[ReferenceLink]:
    links: list[ReferenceLink] = []

    for anchor in node.find_all("a", href=True):
        href = anchor.get("href", "")
        text = _clean_text(anchor)
        if not href or not text or "cite_ref" in href:
            continue

        normalized_href = _normalize_href(article, href)
        links.append(
            ReferenceLink(
                text=text,
                href=normalized_href,
                kind=_classify_reference_link(text, normalized_href),
            )
        )

    return links
```

When building each `ReferenceEntry`, set `primary_url=_select_primary_url(links)`.

No new branching is needed in `writer.py`; keep serializing `reference.model_dump(mode="json")`.

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:

```bash
uv run pytest \
  tests/test_normalize.py::test_normalize_article_classifies_reference_links_and_selects_primary_url \
  tests/test_writer.py::test_write_bundle_serializes_reference_primary_urls \
  tests/test_service.py::test_convert_url_orchestrates_pipeline \
  -v
```

Expected: PASS with `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/document.py src/wiki2md/normalize.py tests/test_normalize.py tests/test_writer.py tests/test_service.py
git commit -m "feat: classify reference links and select primary urls"
```

### Task 3: Update Docs, Examples, And Run Live Smoke Verification

**Files:**
- Modify: `README.md`
- Modify: `examples/andrej-karpathy/references.json`
- Modify: `tests/test_project_docs.py`

- [ ] **Step 1: Write the failing docs smoke tests**

```python
def test_readme_mentions_references_json_sidecar() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "references.json" in readme
    assert "primary_url" in readme


def test_example_references_sidecar_shows_primary_url_and_kinds() -> None:
    payload = json.loads(
        Path("examples/andrej-karpathy/references.json").read_text(encoding="utf-8")
    )

    assert payload[0]["primary_url"] == "https://example.com/karpathy-profile"
    assert payload[0]["links"][0]["kind"] == "external"
```

- [ ] **Step 2: Run the docs tests to verify they fail**

Run:

```bash
uv run pytest tests/test_project_docs.py -v
```

Expected: FAIL because the README and example sidecar do not yet describe the richer reference schema.

- [ ] **Step 3: Update docs and example artifacts**

```markdown
# README.md
- Local `article.md`, `meta.json`, `references.json`, and `assets/` output
- `article.md` is optimized for clean reading and AI ingestion
- `references.json` preserves structured provenance with `primary_url` and classified links
```

```json
// examples/andrej-karpathy/references.json
[
  {
    "id": "cite_note-karpathy-profile-1",
    "text": "Sample reference entry for Andrej Karpathy.",
    "primary_url": "https://example.com/karpathy-profile",
    "links": [
      {
        "text": "Example source",
        "href": "https://example.com/karpathy-profile",
        "kind": "external"
      },
      {
        "text": "Archived copy",
        "href": "https://archive.org/details/karpathy-profile",
        "kind": "archive"
      }
    ]
  }
]
```

- [ ] **Step 4: Run full verification and live smoke checks**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv build
uv run wiki2md convert "https://en.wikipedia.org/wiki/Geoffrey_Hinton" --output-dir /tmp/wiki2md-clean-smoke --overwrite
uv run wiki2md convert "https://zh.wikipedia.org/wiki/%E6%9D%B0%E5%BC%97%E9%87%8C%C2%B7%E8%BE%9B%E9%A1%BF" --output-dir /tmp/wiki2md-clean-smoke-zh --overwrite
```

Inspect the output briefly:

```bash
sed -n '1,40p' /tmp/wiki2md-clean-smoke/people/geoffrey-hinton/article.md
sed -n '1,80p' /tmp/wiki2md-clean-smoke/people/geoffrey-hinton/references.json
sed -n '1,30p' /tmp/wiki2md-clean-smoke-zh/people/杰弗里-辛顿/article.md
```

Expected:

- full test suite passes
- linter passes
- build succeeds
- generated `article.md` no longer contains inline markers like `[8]`
- generated `references.json` contains `primary_url` and per-link `kind`

- [ ] **Step 5: Commit**

```bash
git add README.md examples/andrej-karpathy/references.json tests/test_project_docs.py
git commit -m "docs: describe clean articles and richer references"
```
