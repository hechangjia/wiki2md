# wiki2md General Page Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `wiki2md` from person-first conversion into a general Wikipedia conversion tool while keeping `article.md` as a faithful cleaned article artifact and moving semantic interpretation into metadata.

**Architecture:** Keep the existing bundle shape and conversion pipeline, but replace person-only assumptions with a light page-type inference layer and a broader block extractor. Rendering stays simple: `article.md` renders normalized content blocks, while `meta.json` carries `page_type`, warnings, and future support signals.

**Tech Stack:** Python 3.12+, Typer CLI, Pydantic models, BeautifulSoup HTML normalization, pytest, ruff

---

## File Map

### Create

- `src/wiki2md/page_types.py`
  - Minimal page-shape inference helpers used by `service.py` and batch ingestion.
- `tests/fixtures/html/general_article_fragment.html`
  - English non-person fixture with infobox, summary, heading, table, and list content.
- `tests/fixtures/html/list_article_fragment.html`
  - English list-like fixture with a meaningful table/list and template noise.

### Modify

- `src/wiki2md/document.py`
  - Add a reusable `TableBlock` model so list-like and award/institution pages can preserve structured tables.
- `src/wiki2md/normalize.py`
  - Generalize extraction away from biography-first assumptions, preserve informative tables, and continue removing obvious UI/template noise.
- `src/wiki2md/models.py`
  - Remove implicit `person` defaults where they encode semantics instead of carrying explicit metadata.
- `src/wiki2md/service.py`
  - Infer `page_type` when context does not provide one and stop assuming every direct conversion is a person page.
- `src/wiki2md/render_markdown.py`
  - Remove derived `## Profile` rendering and add generic table rendering.
- `src/wiki2md/batch_models.py`
  - Allow `page_type` to be an optional hint instead of a hardcoded `Literal["person"]`.
- `src/wiki2md/batch_manifest.py`
  - Accept generic manifests without forcing `person`.
- `src/wiki2md/batch_planner.py`
  - Keep path stability (`people/<slug>`) while no longer making batch semantics person-only.
- `src/wiki2md/discovery_service.py`
  - Keep discovery person-focused, but treat it as an auxiliary manifest generator rather than shared conversion semantics.
- `README.md`
  - Reposition the project as a general Wikipedia converter and add a non-person conversion example.

### Test

- `tests/test_normalize.py`
  - Add general-page and list-page normalization expectations.
- `tests/test_render_markdown.py`
  - Lock `article.md` purity and table rendering.
- `tests/test_service.py`
  - Verify inferred metadata for non-person direct conversions.
- `tests/test_batch_manifest.py`
  - Verify batch manifests no longer require `page_type: person`.
- `tests/test_batch_planner.py`
  - Verify generic manifests still plan canonical `people/<slug>` output directories.
- `tests/test_cli_smoke.py`
  - Add a CLI smoke case for a non-person article conversion.
- `tests/test_project_docs.py`
  - Lock README wording/examples for the new general-converter positioning.

## Task 1: Generalize Page-Type Semantics

**Files:**
- Create: `src/wiki2md/page_types.py`
- Modify: `src/wiki2md/models.py`
- Modify: `src/wiki2md/service.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_convert_url_infers_article_page_type_for_non_person_pages(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")
    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(
            title="Linux",
            infobox=InfoboxData(
                title="Linux",
                image=None,
                fields=[InfoboxField(label="Developer", text="Community", links=[])],
            ),
            summary=["Linux is a family of Unix-like operating systems."],
        ),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: _download_report(),
    )

    result = service.convert_url("https://en.wikipedia.org/wiki/Linux")

    payload = json.loads(Path(result.meta_path).read_text(encoding="utf-8"))
    assert payload["page_type"] == "article"


def test_convert_url_prefers_explicit_context_page_type(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")
    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(title="MIT", summary=["MIT is a private research university."]),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: _download_report(),
    )

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Massachusetts_Institute_of_Technology",
        context=ConversionContext(relative_output_dir="people/mit", page_type="institution"),
    )

    payload = json.loads(Path(result.meta_path).read_text(encoding="utf-8"))
    assert payload["page_type"] == "institution"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_service.py -k "page_type or non_person" -v`
Expected: FAIL because `ArticleMetadata` and `ConversionContext` still default to `person`, and `Wiki2MdService.convert_url()` still hardcodes `person`.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/wiki2md/page_types.py
from wiki2md.document import Document

PERSON_LABELS = {
    "en": {"born", "occupation", "spouse", "children"},
    "zh": {"出生", "职业", "配偶", "儿女", "子女"},
}


def infer_page_type(*, title: str, lang: str, document: Document) -> str:
    if document.infobox is not None:
        labels = {field.label.casefold() for field in document.infobox.fields}
        if labels & PERSON_LABELS.get(lang, set()):
            return "person"

    lowered_title = title.casefold()
    if lowered_title.startswith("list of ") or lowered_title.startswith("timeline of "):
        return "list"

    return "article"


# src/wiki2md/models.py
class ConversionContext(BaseModel):
    relative_output_dir: str
    page_type: str | None = None


class ArticleMetadata(BaseModel):
    ...
    page_type: str = "article"


# src/wiki2md/service.py
from wiki2md.page_types import infer_page_type

resolved_page_type = (
    context.page_type
    if context is not None and context.page_type is not None
    else infer_page_type(
        title=article.canonical_title,
        lang=resolution.lang,
        document=document,
    )
)
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_service.py -k "page_type or non_person" -v`
Expected: PASS with inferred `article` for `Linux`-like pages and explicit override still respected.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/page_types.py src/wiki2md/models.py src/wiki2md/service.py tests/test_service.py
git commit -m "feat: infer generic page types for article metadata"
```

## Task 2: Generalize the Document Block Model

**Files:**
- Create: `tests/fixtures/html/general_article_fragment.html`
- Create: `tests/fixtures/html/list_article_fragment.html`
- Modify: `src/wiki2md/document.py`
- Modify: `src/wiki2md/normalize.py`
- Test: `tests/test_normalize.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_normalize_article_preserves_informative_table_for_general_pages() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Linux",
            normalized_url="https://en.wikipedia.org/wiki/Linux",
            lang="en",
            title="Linux",
            slug="linux",
        ),
        canonical_title="Linux",
        html=GENERAL_FIXTURE.read_text(encoding="utf-8"),
        media=[],
    )

    document = normalize_article(article)

    assert document.title == "Linux"
    assert [block.kind for block in document.blocks] == ["heading", "paragraph", "table", "list"]


def test_normalize_article_keeps_meaningful_list_page_blocks_but_drops_navbox_noise() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates",
            normalized_url="https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates",
            lang="en",
            title="List_of_Turing_Award_laureates",
            slug="list-of-turing-award-laureates",
        ),
        canonical_title="List of Turing Award laureates",
        html=LIST_FIXTURE.read_text(encoding="utf-8"),
        media=[],
    )

    document = normalize_article(article)

    assert any(block.kind == "table" for block in document.blocks)
    assert "v" not in "\n".join(
        item.text for block in document.blocks if isinstance(block, ListBlock) for item in block.items
    )
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_normalize.py -k "general_page or list_page or informative_table" -v`
Expected: FAIL because `DocumentBlock` has no `TableBlock`, and `normalize_article()` currently only emits headings, paragraphs, lists, and images.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/wiki2md/document.py
class TableCell(BaseModel):
    text: str


class TableRow(BaseModel):
    cells: list[TableCell] = Field(default_factory=list)
    header: bool = False


class TableBlock(BaseModel):
    kind: Literal["table"] = "table"
    caption: str | None = None
    rows: list[TableRow] = Field(default_factory=list)


DocumentBlock = Annotated[
    ParagraphBlock | HeadingBlock | ListBlock | ImageBlock | TableBlock,
    Field(discriminator="kind"),
]


# src/wiki2md/normalize.py
def _extract_table_block(node: Tag) -> TableBlock | None:
    if "navbox" in node.get("class", []) or "sidebar" in node.get("class", []):
        return None
    rows: list[TableRow] = []
    for tr in node.find_all("tr", recursive=False):
        cells = [TableCell(text=_clean_prose_text(cell)) for cell in tr.find_all(["th", "td"], recursive=False)]
        cells = [cell for cell in cells if cell.text]
        if not cells:
            continue
        rows.append(
            TableRow(
                cells=cells,
                header=all(cell.name == "th" for cell in tr.find_all(["th", "td"], recursive=False)),
            )
        )
    if not rows:
        return None
    caption = _clean_text(node.caption) if getattr(node, "caption", None) else None
    return TableBlock(caption=caption, rows=rows)
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_normalize.py -k "general_page or list_page or informative_table" -v`
Expected: PASS with informative tables preserved and navigation-only tables still removed.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/document.py src/wiki2md/normalize.py tests/fixtures/html/general_article_fragment.html tests/fixtures/html/list_article_fragment.html tests/test_normalize.py
git commit -m "feat: generalize normalizer with reusable table blocks"
```

## Task 3: Keep `article.md` Pure

**Files:**
- Modify: `src/wiki2md/render_markdown.py`
- Test: `tests/test_render_markdown.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_render_markdown_does_not_emit_profile_section_for_person_pages() -> None:
    document = Document(
        title="Andrej Karpathy",
        infobox=InfoboxData(
            title="Andrej Karpathy",
            image=None,
            fields=[InfoboxField(label="Occupation", text="Computer scientist", links=[])],
        ),
        summary=["Andrej Karpathy is a computer scientist."],
    )

    markdown = render_markdown(document, build_metadata(), {})

    assert "## Profile" not in markdown
    assert "- Occupation: Computer scientist" not in markdown


def test_render_markdown_renders_table_blocks() -> None:
    document = Document(
        title="Linux",
        summary=["Linux is a family of Unix-like operating systems."],
        blocks=[
            TableBlock(
                caption="Supported platforms",
                rows=[
                    TableRow(header=True, cells=[TableCell(text="Architecture"), TableCell(text="Status")]),
                    TableRow(header=False, cells=[TableCell(text="x86-64"), TableCell(text="Supported")]),
                ],
            )
        ],
    )

    markdown = render_markdown(
        document,
        build_metadata().model_copy(update={"title": "Linux", "source_url": "https://en.wikipedia.org/wiki/Linux", "page_type": "article"}),
        {},
    )

    assert "## Profile" not in markdown
    assert "| Architecture | Status |" in markdown
    assert "| x86-64 | Supported |" in markdown
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_render_markdown.py -k "profile or table" -v`
Expected: FAIL because the renderer still emits `## Profile` for person pages and has no `TableBlock` branch.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/wiki2md/render_markdown.py
from wiki2md.document import TableBlock


def _render_table(block: TableBlock) -> list[str]:
    if not block.rows:
        return []
    header_row = block.rows[0]
    if header_row.header:
        header = [cell.text for cell in header_row.cells]
        body_rows = block.rows[1:]
    else:
        header = [f"Column {index}" for index, _ in enumerate(header_row.cells, start=1)]
        body_rows = block.rows
    lines = []
    if block.caption:
        lines.append(f"*{block.caption}*")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in body_rows:
        lines.append("| " + " | ".join(cell.text for cell in row.cells) + " |")
    return lines


def render_markdown(...):
    lines = [_render_frontmatter(metadata), "", f"# {document.title}", ""]
    ...
    # remove _render_profile(document, metadata)
    ...
    elif isinstance(block, TableBlock):
        lines.extend(_render_table(block))
        lines.append("")
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_render_markdown.py -k "profile or table" -v`
Expected: PASS with no derived profile section and stable Markdown table output.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/render_markdown.py tests/test_render_markdown.py
git commit -m "feat: render pure article markdown for general pages"
```

## Task 4: Align Batch and Discovery with General Conversion

**Files:**
- Modify: `src/wiki2md/batch_models.py`
- Modify: `src/wiki2md/batch_manifest.py`
- Modify: `src/wiki2md/batch_planner.py`
- Modify: `src/wiki2md/discovery_service.py`
- Test: `tests/test_batch_manifest.py`
- Test: `tests/test_batch_planner.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_manifest_entries_from_txt_defaults_without_person_semantics(tmp_path: Path) -> None:
    manifest = tmp_path / "articles.txt"
    manifest.write_text("https://en.wikipedia.org/wiki/Linux\n", encoding="utf-8")

    entries, invalid_rows = load_manifest_entries(manifest, skip_invalid=False)

    assert invalid_rows == []
    assert entries[0].page_type is None
    assert entries[0].output_group == "default"


def test_plan_batch_tasks_keeps_people_output_root_for_generic_entries(tmp_path: Path) -> None:
    entries = [BatchManifestEntry(url="https://en.wikipedia.org/wiki/Linux", page_type=None)]

    tasks, duplicates = plan_batch_tasks(entries, tmp_path / "output")

    assert duplicates == []
    assert tasks[0].relative_output_dir == "people/linux"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_batch_manifest.py tests/test_batch_planner.py -k "without_person_semantics or generic_entries" -v`
Expected: FAIL because `BatchManifestEntry.page_type` is still `Literal["person"]`.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/wiki2md/batch_models.py
class BatchManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    page_type: str | None = None
    slug: str | None = None
    tags: list[str] = Field(default_factory=list)
    output_group: str = "default"


# src/wiki2md/discovery_service.py
manifest_rows.append(
    BatchManifestEntry(
        url=candidate.url,
        page_type="person",
        slug=candidate.slug,
        tags=tags,
        output_group=output_group,
    )
)
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_batch_manifest.py tests/test_batch_planner.py -k "without_person_semantics or generic_entries" -v`
Expected: PASS, with direct batch ingestion now generic by default while discovery still emits person-focused manifests.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/batch_models.py src/wiki2md/batch_manifest.py src/wiki2md/batch_planner.py src/wiki2md/discovery_service.py tests/test_batch_manifest.py tests/test_batch_planner.py
git commit -m "feat: align batch manifests with general page conversion"
```

## Task 5: Update CLI/Docs Contract and Run Full Verification

**Files:**
- Modify: `README.md`
- Test: `tests/test_cli_smoke.py`
- Test: `tests/test_project_docs.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_readme_describes_general_wikipedia_conversion(readme_text: str) -> None:
    assert "Wikipedia -> clean Markdown converter" in readme_text
    assert "not limited to people pages" in readme_text
    assert "wiki2md batch discover" in readme_text


def test_cli_smoke_converts_non_person_articles(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["convert", "https://en.wikipedia.org/wiki/Linux", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_project_docs.py tests/test_cli_smoke.py -k "general or non_person" -v`
Expected: FAIL because README still describes the project in person-heavy terms and CLI smoke tests do not lock a non-person path.

- [ ] **Step 3: Write the minimal implementation**

```markdown
# README.md
- reposition the opening description around general Wikipedia conversion
- add a direct `Linux` or `Massachusetts Institute of Technology` conversion example
- explain that `page_type` lives in `meta.json`
- keep `batch discover` documented as an auxiliary workflow for people discovery
```

```python
# tests/test_cli_smoke.py
def test_convert_command_smoke_for_non_person_article(monkeypatch, tmp_path: Path) -> None:
    ...
    assert payload["page_type"] == "article"
```

- [ ] **Step 4: Run full verification**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv build
```

Expected:

- `pytest` passes
- `ruff check` passes
- `uv build` produces both sdist and wheel

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_cli_smoke.py tests/test_project_docs.py
git commit -m "docs: position wiki2md as a general wikipedia converter"
```

## Implementation Notes

- Keep the bundle directory under `people/<slug>` in this phase for compatibility. Path generalization can happen later if it becomes necessary.
- Do not remove sidecars such as `infobox.json`, `references.json`, `section_evidence.json`, or `sources.md`.
- Do not expand discovery scope in this phase beyond preserving its auxiliary role and keeping its manifests person-focused.
- Prefer broad block extraction with narrow cleanup rules over page-type-specific parsing branches.
- When a page is noisy but still convertible, preserve the bundle and record warnings in `meta.json`.

## Final Verification Checklist

- `Linux` converts without `page_type: person` in `meta.json`
- `Linux` no longer renders `## Profile` in `article.md`
- person pages still convert successfully with `infobox.json` intact
- list-like pages preserve informative tables/lists while dropping obvious nav noise
- batch manifests can omit `page_type`
- discovery still generates person manifests
- README now reflects the general-converter product direction
