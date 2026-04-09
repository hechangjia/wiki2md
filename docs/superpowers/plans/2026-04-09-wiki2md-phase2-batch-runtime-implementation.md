# wiki2md Phase 2 Batch Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a resumable batch runtime that can process `txt` and `jsonl` manifests with skip-existing, continue-on-error, retry reporting, and batch metadata threaded into saved artifacts.

**Architecture:** Keep `Wiki2MdService.convert_url()` as the canonical single-page conversion unit, but introduce a dedicated batch subsystem around it: manifest loading, planning, state/report persistence, and small-concurrency execution. Preserve the public `wiki2md batch FILE` CLI, while keeping batch policy and resume logic out of `cli.py`.

**Tech Stack:** Python 3.12, `typer`, `pydantic`, `concurrent.futures`, `pathlib`, `json`, `hashlib`, `pytest`, `ruff`

---

## File Structure

- `src/wiki2md/models.py`: extend artifact metadata and add conversion context types used by both single and batch runs
- `src/wiki2md/render_markdown.py`: thread batch-aware metadata into frontmatter
- `src/wiki2md/writer.py`: support caller-controlled output directories rather than hardcoding `people/<slug>`
- `src/wiki2md/service.py`: accept optional batch conversion context, populate batch metadata, and pass custom output directories into the writer
- `src/wiki2md/errors.py`: add manifest-validation errors for strict batch mode
- `src/wiki2md/batch_models.py`: typed models for manifest entries, planned tasks, state rows, config, and batch results
- `src/wiki2md/batch_manifest.py`: load `txt`/`jsonl`, validate entries, fill defaults, and emit invalid-row details
- `src/wiki2md/batch_planner.py`: resolve URLs, apply manifest slug overrides, build output directories, and detect duplicates
- `src/wiki2md/batch_state.py`: deterministic batch-id generation, state-path helpers, state load/save, and report artifact writing
- `src/wiki2md/batch_runtime.py`: small-concurrency execution, transient retries, skip-existing, auto/explicit resume, and terminal/report summaries
- `src/wiki2md/cli.py`: wire `wiki2md batch FILE` to the batch runtime with new flags
- `tests/test_writer.py`: verify custom output directory writing
- `tests/test_service.py`: verify batch metadata threading into metadata and sidecars
- `tests/test_render_markdown.py`: verify batch metadata frontmatter fields
- `tests/test_batch_manifest.py`: manifest loading, defaults, strict validation, and skip-invalid behavior
- `tests/test_batch_planner.py`: slug priority, duplicate detection, and output directory planning
- `tests/test_batch_state.py`: deterministic batch-id, state load/save, and report artifact writing
- `tests/test_batch_runtime.py`: continue-on-error, skip-existing, retries, resume, and report generation
- `tests/test_cli.py`: CLI batch flag handling and summary output
- `tests/test_project_docs.py`: docs/example contract for batch manifests and retry artifacts
- `README.md`: batch manifest examples, resume behavior, and retry guidance
- `examples/batch/person-manifest.jsonl`: minimal structured manifest example

### Task 1: Thread Batch Metadata And Output Paths Through The Single Conversion Pipeline

**Files:**
- Modify: `src/wiki2md/models.py`
- Modify: `src/wiki2md/render_markdown.py`
- Modify: `src/wiki2md/writer.py`
- Modify: `src/wiki2md/service.py`
- Modify: `tests/test_writer.py`
- Modify: `tests/test_service.py`
- Modify: `tests/test_render_markdown.py`

- [ ] **Step 1: Write the failing writer, service, and renderer tests**

Add a writer test that expects a caller-supplied relative output directory instead of the legacy hardcoded `people/<slug>` path:

```python
def test_write_bundle_uses_custom_relative_output_dir(tmp_path: Path) -> None:
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
        page_type="person",
        output_group="people-ai",
        manifest_slug="karpathy-manifest",
        resolved_slug="karpathy-final",
        tags=["ai", "person"],
        batch_id="batch-123",
    )

    result = write_bundle(
        output_root=tmp_path / "output",
        relative_output_dir=Path("person/people-ai/karpathy-final"),
        resolution=resolution,
        markdown="# Andrej Karpathy\n",
        metadata=metadata,
        references=[],
        infobox=None,
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    assert Path(result.output_dir) == tmp_path / "output" / "person" / "people-ai" / "karpathy-final"
```

Add a renderer test that expects batch-aware frontmatter fields:

```python
def test_render_markdown_includes_batch_frontmatter_fields() -> None:
    metadata = build_metadata().model_copy(
        update={
            "output_group": "people-ai",
            "manifest_slug": "karpathy-manifest",
            "resolved_slug": "karpathy-final",
            "tags": ["ai", "person"],
            "batch_id": "batch-123",
        }
    )
    markdown = render_markdown(
        Document(title="Andrej Karpathy", summary=["Example summary."]),
        metadata,
        {},
    )

    assert "output_group: people-ai" in markdown
    assert "manifest_slug: karpathy-manifest" in markdown
    assert "resolved_slug: karpathy-final" in markdown
    assert "tags:" in markdown
    assert "- ai" in markdown
    assert "batch_id: batch-123" in markdown
```

Add a service test that expects manifest metadata to survive into `meta.json`:

```python
def test_convert_url_threads_batch_context_into_metadata(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")
    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(title="Andrej Karpathy", summary=["Example summary."]),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr("wiki2md.service.download_assets", lambda assets, destination, user_agent: None)
    monkeypatch.setattr("wiki2md.service.render_markdown", lambda document, metadata, asset_map: "# Andrej Karpathy\n")

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Andrej_Karpathy",
        context=ConversionContext(
            relative_output_dir="person/people-ai/karpathy-final",
            page_type="person",
            output_group="people-ai",
            manifest_slug="karpathy-manifest",
            resolved_slug="karpathy-final",
            tags=["ai", "person"],
            batch_id="batch-123",
        ),
    )

    payload = json.loads(Path(result.meta_path).read_text(encoding="utf-8"))
    assert payload["page_type"] == "person"
    assert payload["output_group"] == "people-ai"
    assert payload["manifest_slug"] == "karpathy-manifest"
    assert payload["resolved_slug"] == "karpathy-final"
    assert payload["tags"] == ["ai", "person"]
    assert payload["batch_id"] == "batch-123"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
uv run pytest \
  tests/test_writer.py::test_write_bundle_uses_custom_relative_output_dir \
  tests/test_render_markdown.py::test_render_markdown_includes_batch_frontmatter_fields \
  tests/test_service.py::test_convert_url_threads_batch_context_into_metadata \
  -q
```

Expected: FAIL because `ConversionContext` does not exist, `write_bundle()` has no `relative_output_dir`, and `ArticleMetadata` has no batch fields.

- [ ] **Step 3: Implement batch-aware metadata and custom output directories**

Add typed batch context fields in `src/wiki2md/models.py`:

```python
class ConversionContext(BaseModel):
    relative_output_dir: str
    page_type: str = "person"
    output_group: str | None = None
    manifest_slug: str | None = None
    resolved_slug: str | None = None
    tags: list[str] = Field(default_factory=list)
    batch_id: str | None = None


class ArticleMetadata(BaseModel):
    title: str
    source_url: str
    source_lang: SupportedLang
    source_type: Literal["wikipedia"] = "wikipedia"
    retrieved_at: datetime
    page_type: str = "person"
    pageid: int | None = None
    revid: int | None = None
    image_manifest: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    cleanup_stats: dict[str, int | bool] = Field(default_factory=dict)
    output_group: str | None = None
    manifest_slug: str | None = None
    resolved_slug: str | None = None
    tags: list[str] = Field(default_factory=list)
    batch_id: str | None = None
```

Render the new frontmatter keys in `src/wiki2md/render_markdown.py`:

```python
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
        "output_group": metadata.output_group,
        "manifest_slug": metadata.manifest_slug,
        "resolved_slug": metadata.resolved_slug,
        "tags": metadata.tags,
        "batch_id": metadata.batch_id,
    }
    return f"---\\n{yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()}\\n---"
```

Parameterize output directories in `src/wiki2md/writer.py`:

```python
def write_bundle(
    output_root: Path,
    relative_output_dir: Path,
    resolution: UrlResolution,
    markdown: str,
    metadata: ArticleMetadata,
    references: list[ReferenceEntry],
    infobox: InfoboxData | None,
    staging_assets_dir: Path,
    overwrite: bool,
) -> ConversionResult:
    final_dir = output_root / relative_output_dir
    temp_dir = output_root / ".tmp" / relative_output_dir
    ...
```

Thread conversion context in `src/wiki2md/service.py`:

```python
def convert_url(
    self,
    url: str,
    overwrite: bool = False,
    context: ConversionContext | None = None,
) -> ConversionResult:
    ...
    relative_output_dir = (
        Path(context.relative_output_dir)
        if context is not None
        else Path("people") / resolution.slug
    )
    metadata = ArticleMetadata(
        ...,
        page_type=context.page_type if context else "person",
        output_group=context.output_group if context else None,
        manifest_slug=context.manifest_slug if context else None,
        resolved_slug=context.resolved_slug if context else resolution.slug,
        tags=list(context.tags) if context else [],
        batch_id=context.batch_id if context else None,
    )
    return write_bundle(
        output_root=self.output_root,
        relative_output_dir=relative_output_dir,
        resolution=resolution,
        ...
    )
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:

```bash
uv run pytest \
  tests/test_writer.py::test_write_bundle_uses_custom_relative_output_dir \
  tests/test_render_markdown.py::test_render_markdown_includes_batch_frontmatter_fields \
  tests/test_service.py::test_convert_url_threads_batch_context_into_metadata \
  -q
```

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/models.py src/wiki2md/render_markdown.py src/wiki2md/writer.py src/wiki2md/service.py tests/test_writer.py tests/test_render_markdown.py tests/test_service.py
git commit -m "feat: thread batch metadata through artifact writing"
```

### Task 2: Add Manifest Loading, Validation, And Planning

**Files:**
- Create: `src/wiki2md/batch_models.py`
- Create: `src/wiki2md/batch_manifest.py`
- Create: `src/wiki2md/batch_planner.py`
- Modify: `src/wiki2md/errors.py`
- Test: `tests/test_batch_manifest.py`
- Test: `tests/test_batch_planner.py`

- [ ] **Step 1: Write the failing manifest and planner tests**

Create `tests/test_batch_manifest.py` with both strict and relaxed validation coverage:

```python
import json
from pathlib import Path

import pytest

from wiki2md.batch_manifest import load_manifest_entries
from wiki2md.errors import BatchManifestValidationError


def test_load_manifest_entries_from_txt_defaults_metadata(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text("https://en.wikipedia.org/wiki/Andrej_Karpathy\\n", encoding="utf-8")

    entries, invalid_rows = load_manifest_entries(manifest, skip_invalid=False)

    assert invalid_rows == []
    assert len(entries) == 1
    assert entries[0].url.endswith("/wiki/Andrej_Karpathy")
    assert entries[0].page_type == "person"
    assert entries[0].output_group == "default"
    assert entries[0].tags == []


def test_load_manifest_entries_rejects_invalid_rows_in_strict_mode(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text(
        json.dumps({"url": "https://en.wikipedia.org/wiki/Andrej_Karpathy", "tags": "ai"}) + "\\n",
        encoding="utf-8",
    )

    with pytest.raises(BatchManifestValidationError):
        load_manifest_entries(manifest, skip_invalid=False)


def test_load_manifest_entries_skips_invalid_rows_when_requested(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text(
        "\\n".join(
            [
                json.dumps({"url": "https://en.wikipedia.org/wiki/Andrej_Karpathy", "output_group": "people-ai"}),
                json.dumps({"url": "https://en.wikipedia.org/wiki/Fei-Fei_Li", "tags": "ai"}),
            ]
        ),
        encoding="utf-8",
    )

    entries, invalid_rows = load_manifest_entries(manifest, skip_invalid=True)

    assert [entry.output_group for entry in entries] == ["people-ai"]
    assert len(invalid_rows) == 1
    assert invalid_rows[0].line_number == 2
```

Create `tests/test_batch_planner.py`:

```python
from pathlib import Path

from wiki2md.batch_models import BatchManifestEntry
from wiki2md.batch_planner import plan_batch_tasks


def test_plan_batch_tasks_prefers_manifest_slug_and_builds_output_dir() -> None:
    tasks, duplicates = plan_batch_tasks(
        [
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                slug="karpathy-manifest",
                output_group="people-ai",
                tags=["ai"],
            )
        ],
        output_root=Path("output"),
    )

    assert duplicates == []
    assert tasks[0].resolved_slug == "karpathy-manifest"
    assert tasks[0].relative_output_dir == "person/people-ai/karpathy-manifest"


def test_plan_batch_tasks_skips_duplicate_urls_and_duplicate_output_dirs() -> None:
    tasks, duplicates = plan_batch_tasks(
        [
            BatchManifestEntry(url="https://en.wikipedia.org/wiki/Andrej_Karpathy"),
            BatchManifestEntry(url="https://en.wikipedia.org/wiki/Andrej_Karpathy"),
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Andrej_Karpathy_(researcher)",
                slug="andrej-karpathy",
            ),
        ],
        output_root=Path("output"),
    )

    assert len(tasks) == 1
    assert len(duplicates) == 2
    assert {item.reason for item in duplicates} == {"duplicate_url", "duplicate_output_dir"}
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
uv run pytest tests/test_batch_manifest.py tests/test_batch_planner.py -q
```

Expected: FAIL with `ModuleNotFoundError` for the new batch modules and missing `BatchManifestValidationError`.

- [ ] **Step 3: Implement manifest models, loader, validation, and planning**

Add manifest-specific types in `src/wiki2md/batch_models.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field

from wiki2md.models import UrlResolution


class BatchManifestEntry(BaseModel):
    url: str
    page_type: Literal["person"] = "person"
    slug: str | None = None
    tags: list[str] = Field(default_factory=list)
    output_group: str = "default"


class InvalidManifestRow(BaseModel):
    line_number: int
    raw_text: str
    error: str


class PlannedBatchTask(BaseModel):
    entry: BatchManifestEntry
    resolution: UrlResolution
    resolved_slug: str
    relative_output_dir: str
    entry_key: str


class DuplicateBatchEntry(BaseModel):
    entry: BatchManifestEntry
    reason: Literal["duplicate_url", "duplicate_output_dir"]
```

Add strict validation error in `src/wiki2md/errors.py`:

```python
class BatchManifestValidationError(Wiki2MdError):
    """Raised when a batch manifest contains invalid rows in strict mode."""

    def __init__(self, invalid_rows: list[object]) -> None:
        super().__init__("Batch manifest validation failed.")
        self.invalid_rows = invalid_rows
```

Implement `src/wiki2md/batch_manifest.py`:

```python
import json
from pathlib import Path

from pydantic import ValidationError

from wiki2md.batch_models import BatchManifestEntry, InvalidManifestRow
from wiki2md.errors import BatchManifestValidationError


def load_manifest_entries(
    manifest_path: Path,
    skip_invalid: bool,
) -> tuple[list[BatchManifestEntry], list[InvalidManifestRow]]:
    entries: list[BatchManifestEntry] = []
    invalid_rows: list[InvalidManifestRow] = []
    lines = manifest_path.read_text(encoding="utf-8").splitlines()

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            payload = {"url": line} if manifest_path.suffix != ".jsonl" else json.loads(line)
            entry = BatchManifestEntry.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            invalid_rows.append(
                InvalidManifestRow(
                    line_number=line_number,
                    raw_text=raw_line,
                    error=str(exc),
                )
            )
            continue
        entries.append(entry)

    if invalid_rows and not skip_invalid:
        raise BatchManifestValidationError(invalid_rows)

    return entries, invalid_rows
```

Implement `src/wiki2md/batch_planner.py`:

```python
from pathlib import Path

from wiki2md.batch_models import BatchManifestEntry, DuplicateBatchEntry, PlannedBatchTask
from wiki2md.urls import resolve_wikipedia_url


def plan_batch_tasks(
    entries: list[BatchManifestEntry],
    output_root: Path,
) -> tuple[list[PlannedBatchTask], list[DuplicateBatchEntry]]:
    del output_root
    tasks: list[PlannedBatchTask] = []
    duplicates: list[DuplicateBatchEntry] = []
    seen_urls: set[str] = set()
    seen_output_dirs: set[str] = set()

    for entry in entries:
        resolution = resolve_wikipedia_url(entry.url)
        if resolution.normalized_url in seen_urls:
            duplicates.append(DuplicateBatchEntry(entry=entry, reason="duplicate_url"))
            continue

        resolved_slug = entry.slug or resolution.slug
        relative_output_dir = f"{entry.page_type}/{entry.output_group}/{resolved_slug}"
        if relative_output_dir in seen_output_dirs:
            duplicates.append(DuplicateBatchEntry(entry=entry, reason="duplicate_output_dir"))
            continue

        seen_urls.add(resolution.normalized_url)
        seen_output_dirs.add(relative_output_dir)
        tasks.append(
            PlannedBatchTask(
                entry=entry,
                resolution=resolution,
                resolved_slug=resolved_slug,
                relative_output_dir=relative_output_dir,
                entry_key=f"{resolution.normalized_url}|{relative_output_dir}",
            )
        )

    return tasks, duplicates
```

- [ ] **Step 4: Run the manifest and planner tests to verify they pass**

Run:

```bash
uv run pytest tests/test_batch_manifest.py tests/test_batch_planner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/batch_models.py src/wiki2md/batch_manifest.py src/wiki2md/batch_planner.py src/wiki2md/errors.py tests/test_batch_manifest.py tests/test_batch_planner.py
git commit -m "feat: add batch manifest planning"
```

### Task 3: Add Deterministic Batch State And Report Artifact Writing

**Files:**
- Create: `src/wiki2md/batch_state.py`
- Modify: `src/wiki2md/batch_models.py`
- Test: `tests/test_batch_state.py`

- [ ] **Step 1: Write the failing state and report tests**

Create `tests/test_batch_state.py`:

```python
import json
from pathlib import Path

from wiki2md.batch_models import (
    BatchManifestEntry,
    BatchRunConfig,
    BatchRunResult,
    BatchStateEntry,
    InvalidManifestRow,
)
from wiki2md.batch_state import (
    build_batch_id,
    default_state_path,
    load_batch_state,
    save_batch_state,
    write_batch_reports,
)


def test_default_state_path_uses_output_hidden_batch_directory(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text("", encoding="utf-8")

    state_path = default_state_path(tmp_path / "output", manifest)

    assert state_path.parent.parent.parent == tmp_path / "output" / ".wiki2md"
    assert state_path.name == "state.json"


def test_save_and_load_batch_state_roundtrip(tmp_path: Path) -> None:
    state_path = tmp_path / "output" / ".wiki2md" / "batches" / "batch-123" / "state.json"
    result = BatchRunResult(
        batch_id="batch-123",
        manifest_path="people.jsonl",
        output_root=str(tmp_path / "output"),
        config=BatchRunConfig(concurrency=4, overwrite=False, skip_invalid=False, max_retries=2),
        totals={"success": 1},
        entries=[
            BatchStateEntry(
                entry_key="entry-1",
                url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                status="success",
                relative_output_dir="person/default/andrej-karpathy",
                output_dir=str(tmp_path / "output" / "person" / "default" / "andrej-karpathy"),
            )
        ],
    )

    save_batch_state(state_path, result)
    loaded = load_batch_state(state_path)

    assert loaded.batch_id == "batch-123"
    assert loaded.entries[0].status == "success"


def test_write_batch_reports_writes_failed_and_invalid_artifacts(tmp_path: Path) -> None:
    batch_dir = tmp_path / "output" / ".wiki2md" / "batches" / "batch-123"
    result = BatchRunResult(
        batch_id="batch-123",
        manifest_path="people.jsonl",
        output_root=str(tmp_path / "output"),
        config=BatchRunConfig(concurrency=4, overwrite=False, skip_invalid=True, max_retries=2),
        totals={"failed": 1, "invalid": 1},
        entries=[
            BatchStateEntry(
                entry_key="failed-1",
                url="https://en.wikipedia.org/wiki/Bad_Page",
                status="failed",
                manifest_entry=BatchManifestEntry(
                    url="https://en.wikipedia.org/wiki/Bad_Page",
                    output_group="people-ai",
                ),
                error="Fetch failed",
            )
        ],
        invalid_rows=[
            InvalidManifestRow(line_number=2, raw_text='{\"tags\": \"bad\"}', error="Input should be a valid list"),
        ],
    )

    write_batch_reports(batch_dir, result)

    assert json.loads((batch_dir / "batch-report.json").read_text(encoding="utf-8"))["batch_id"] == "batch-123"
    assert (batch_dir / "failed.txt").read_text(encoding="utf-8").strip() == "https://en.wikipedia.org/wiki/Bad_Page"
    assert "people-ai" in (batch_dir / "failed.jsonl").read_text(encoding="utf-8")
    assert "tags" in (batch_dir / "invalid.jsonl").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the state tests to verify they fail**

Run:

```bash
uv run pytest tests/test_batch_state.py -q
```

Expected: FAIL because `BatchRunConfig`, `BatchRunResult`, `BatchStateEntry`, and `batch_state.py` do not exist yet.

- [ ] **Step 3: Implement deterministic state helpers and report writing**

Extend `src/wiki2md/batch_models.py`:

```python
class BatchRunConfig(BaseModel):
    concurrency: int = 4
    overwrite: bool = False
    skip_invalid: bool = False
    max_retries: int = 2


class BatchStateEntry(BaseModel):
    entry_key: str
    url: str
    status: Literal["pending", "success", "failed", "skipped_existing", "invalid", "duplicate"]
    relative_output_dir: str | None = None
    output_dir: str | None = None
    manifest_entry: BatchManifestEntry | None = None
    error: str | None = None


class BatchRunResult(BaseModel):
    batch_id: str
    manifest_path: str
    output_root: str
    config: BatchRunConfig
    totals: dict[str, int]
    entries: list[BatchStateEntry] = Field(default_factory=list)
    invalid_rows: list[InvalidManifestRow] = Field(default_factory=list)
```

Implement `src/wiki2md/batch_state.py`:

```python
import hashlib
import json
from pathlib import Path

from wiki2md.batch_models import BatchRunResult


def build_batch_id(manifest_path: Path) -> str:
    digest = hashlib.sha1(str(manifest_path.resolve()).encode("utf-8")).hexdigest()
    return digest[:12]


def default_state_path(output_root: Path, manifest_path: Path) -> Path:
    batch_id = build_batch_id(manifest_path)
    return output_root / ".wiki2md" / "batches" / batch_id / "state.json"


def save_batch_state(state_path: Path, result: BatchRunResult) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_batch_state(state_path: Path) -> BatchRunResult:
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return BatchRunResult.model_validate(payload)


def write_batch_reports(batch_dir: Path, result: BatchRunResult) -> None:
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "batch-report.json").write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    failed_entries = [entry for entry in result.entries if entry.status == "failed"]
    (batch_dir / "failed.txt").write_text(
        "\n".join(entry.url for entry in failed_entries) + ("\n" if failed_entries else ""),
        encoding="utf-8",
    )
    (batch_dir / "failed.jsonl").write_text(
        "".join(
            json.dumps(entry.manifest_entry.model_dump(mode="json"), ensure_ascii=False) + "\n"
            for entry in failed_entries
            if entry.manifest_entry is not None
        ),
        encoding="utf-8",
    )
    if result.invalid_rows:
        (batch_dir / "invalid.jsonl").write_text(
            "".join(
                json.dumps(row.model_dump(mode="json"), ensure_ascii=False) + "\n"
                for row in result.invalid_rows
            ),
            encoding="utf-8",
        )
```

- [ ] **Step 4: Run the state tests to verify they pass**

Run:

```bash
uv run pytest tests/test_batch_state.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/batch_models.py src/wiki2md/batch_state.py tests/test_batch_state.py
git commit -m "feat: add batch state and reporting"
```

### Task 4: Implement The Batch Runner With Resume, Retries, And Skip-Existing

**Files:**
- Create: `src/wiki2md/batch_runtime.py`
- Modify: `src/wiki2md/batch_models.py`
- Modify: `src/wiki2md/errors.py`
- Test: `tests/test_batch_runtime.py`

- [ ] **Step 1: Write the failing batch runtime tests**

Create `tests/test_batch_runtime.py`:

```python
from pathlib import Path

from wiki2md.batch_models import BatchRunConfig
from wiki2md.batch_runtime import run_batch
from wiki2md.errors import FetchError
from wiki2md.models import ConversionResult


class FakeService:
    def __init__(self, output_root: Path, failures: dict[str, int] | None = None) -> None:
        self.output_root = output_root
        self.failures = failures or {}

    def convert_url(self, url: str, overwrite: bool = False, context=None) -> ConversionResult:
        remaining = self.failures.get(url, 0)
        if remaining > 0:
            self.failures[url] = remaining - 1
            raise FetchError(f"temporary failure for {url}")
        output_dir = self.output_root / context.relative_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        article_path = output_dir / "article.md"
        meta_path = output_dir / "meta.json"
        references_path = output_dir / "references.json"
        article_path.write_text("# Example\n", encoding="utf-8")
        meta_path.write_text("{}", encoding="utf-8")
        references_path.write_text("[]", encoding="utf-8")
        return ConversionResult(
            output_dir=str(output_dir),
            article_path=str(article_path),
            meta_path=str(meta_path),
            references_path=str(references_path),
            asset_count=0,
        )


def test_run_batch_continues_on_failure_and_skips_existing(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text(
        "\\n".join(
            [
                "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                "https://en.wikipedia.org/wiki/Fei-Fei_Li",
            ]
        ),
        encoding="utf-8",
    )
    existing_dir = tmp_path / "output" / "person" / "default" / "fei-fei-li"
    existing_dir.mkdir(parents=True)

    result = run_batch(
        manifest_path=manifest,
        output_root=tmp_path / "output",
        service_factory=lambda: FakeService(tmp_path / "output"),
        config=BatchRunConfig(concurrency=2, overwrite=False, skip_invalid=False, max_retries=2),
    )

    statuses = {entry.url: entry.status for entry in result.entries}
    assert statuses["https://en.wikipedia.org/wiki/Andrej_Karpathy"] == "success"
    assert statuses["https://en.wikipedia.org/wiki/Fei-Fei_Li"] == "skipped_existing"


def test_run_batch_retries_fetch_errors(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text("https://en.wikipedia.org/wiki/Andrej_Karpathy\n", encoding="utf-8")
    failures = {"https://en.wikipedia.org/wiki/Andrej_Karpathy": 2}

    result = run_batch(
        manifest_path=manifest,
        output_root=tmp_path / "output",
        service_factory=lambda: FakeService(tmp_path / "output", failures),
        config=BatchRunConfig(concurrency=1, overwrite=False, skip_invalid=False, max_retries=2),
    )

    assert result.entries[0].status == "success"
```

- [ ] **Step 2: Run the runtime tests to verify they fail**

Run:

```bash
uv run pytest tests/test_batch_runtime.py -q
```

Expected: FAIL because `run_batch()` does not exist yet.

- [ ] **Step 3: Implement small-concurrency batch execution and retries**

Implement `src/wiki2md/batch_runtime.py`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from wiki2md.batch_manifest import load_manifest_entries
from wiki2md.batch_models import BatchRunConfig, BatchRunResult, BatchStateEntry
from wiki2md.batch_planner import plan_batch_tasks
from wiki2md.batch_state import default_state_path, load_batch_state, save_batch_state, write_batch_reports
from wiki2md.errors import FetchError
from wiki2md.models import ConversionContext


def run_batch(
    manifest_path: Path,
    output_root: Path,
    service_factory,
    config: BatchRunConfig,
    resume_path: Path | None = None,
) -> BatchRunResult:
    entries, invalid_rows = load_manifest_entries(manifest_path, skip_invalid=config.skip_invalid)
    tasks, duplicates = plan_batch_tasks(entries, output_root=output_root)
    state_path = resume_path or default_state_path(output_root, manifest_path)
    if state_path.exists():
        result = load_batch_state(state_path)
        state_by_key = {entry.entry_key: entry for entry in result.entries}
    else:
        batch_id = state_path.parent.name
        result = BatchRunResult(
            batch_id=batch_id,
            manifest_path=str(manifest_path),
            output_root=str(output_root),
            config=config,
            totals={},
            entries=[],
            invalid_rows=invalid_rows,
        )
        state_by_key = {}

    for invalid_row in invalid_rows:
        result.entries.append(
            BatchStateEntry(
                entry_key=f"invalid:{invalid_row.line_number}",
                url="",
                status="invalid",
                error=invalid_row.error,
            )
        )

    for duplicate in duplicates:
        result.entries.append(
            BatchStateEntry(
                entry_key=f"duplicate:{duplicate.entry.url}",
                url=duplicate.entry.url,
                status="duplicate",
                manifest_entry=duplicate.entry,
                error=duplicate.reason,
            )
        )

    def _run_task(task):
        target_dir = output_root / task.relative_output_dir
        if target_dir.exists() and not config.overwrite:
            return BatchStateEntry(
                entry_key=task.entry_key,
                url=task.entry.url,
                status="skipped_existing",
                relative_output_dir=task.relative_output_dir,
                output_dir=str(target_dir),
                manifest_entry=task.entry,
            )
        attempt = 0
        while True:
            try:
                service = service_factory()
                try:
                    conversion = service.convert_url(
                        task.entry.url,
                        overwrite=config.overwrite,
                        context=ConversionContext(
                            relative_output_dir=task.relative_output_dir,
                            page_type=task.entry.page_type,
                            output_group=task.entry.output_group,
                            manifest_slug=task.entry.slug,
                            resolved_slug=task.resolved_slug,
                            tags=task.entry.tags,
                            batch_id=result.batch_id,
                        ),
                    )
                finally:
                    client = getattr(service, "client", None)
                    close = getattr(client, "close", None)
                    if callable(close):
                        close()
                return BatchStateEntry(
                    entry_key=task.entry_key,
                    url=task.entry.url,
                    status="success",
                    relative_output_dir=task.relative_output_dir,
                    output_dir=conversion.output_dir,
                    manifest_entry=task.entry,
                )
            except FetchError as exc:
                if attempt >= config.max_retries:
                    return BatchStateEntry(
                        entry_key=task.entry_key,
                        url=task.entry.url,
                        status="failed",
                        relative_output_dir=task.relative_output_dir,
                        manifest_entry=task.entry,
                        error=str(exc),
                    )
                attempt += 1

    pending_tasks = [task for task in tasks if state_by_key.get(task.entry_key, BatchStateEntry(entry_key="", url="", status="pending")).status not in {"success", "skipped_existing"}]
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = {executor.submit(_run_task, task): task for task in pending_tasks}
        for future in as_completed(futures):
            entry = future.result()
            state_by_key[entry.entry_key] = entry
            save_batch_state(
                state_path,
                result.model_copy(
                    update={"entries": list(state_by_key.values())},
                ),
            )

    result = result.model_copy(update={"entries": list(state_by_key.values()) + [entry for entry in result.entries if entry.status in {"invalid", "duplicate"}]})
    totals: dict[str, int] = {}
    for entry in result.entries:
        totals[entry.status] = totals.get(entry.status, 0) + 1
    result = result.model_copy(update={"totals": totals})
    save_batch_state(state_path, result)
    write_batch_reports(state_path.parent, result)
    return result
```

- [ ] **Step 4: Run the runtime tests to verify they pass**

Run:

```bash
uv run pytest tests/test_batch_runtime.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/batch_runtime.py src/wiki2md/batch_models.py src/wiki2md/errors.py tests/test_batch_runtime.py
git commit -m "feat: implement resumable batch runtime"
```

### Task 5: Wire The CLI Batch Command To The Runtime

**Files:**
- Modify: `src/wiki2md/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI tests for new batch flags and summary output**

Update `tests/test_cli.py`:

```python
from wiki2md.batch_models import BatchRunConfig, BatchRunResult, BatchStateEntry


def test_batch_command_invokes_runtime_with_new_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_batch(manifest_path, output_root, service_factory, config, resume_path=None):
        captured["manifest_path"] = manifest_path
        captured["output_root"] = output_root
        captured["config"] = config
        captured["resume_path"] = resume_path
        return BatchRunResult(
            batch_id="batch-123",
            manifest_path=str(manifest_path),
            output_root=str(output_root),
            config=config,
            totals={"success": 1, "failed": 0},
            entries=[
                BatchStateEntry(
                    entry_key="entry-1",
                    url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                    status="success",
                )
            ],
        )

    monkeypatch.setattr("wiki2md.cli.run_batch", fake_run_batch)
    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))

    manifest = tmp_path / "people.jsonl"
    manifest.write_text("{}", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "batch",
            str(manifest),
            "--output-dir",
            str(tmp_path / "output"),
            "--concurrency",
            "5",
            "--resume",
            str(tmp_path / "state.json"),
            "--skip-invalid",
        ],
    )

    assert result.exit_code == 0
    assert "SUCCESS" in result.stdout
    assert "Summary:" in result.stdout
    assert captured["resume_path"] == tmp_path / "state.json"
    assert captured["config"].concurrency == 5
    assert captured["config"].skip_invalid is True
```

- [ ] **Step 2: Run the CLI tests to verify they fail**

Run:

```bash
uv run pytest tests/test_cli.py::test_batch_command_invokes_runtime_with_new_flags -q
```

Expected: FAIL because `run_batch` is not imported in the CLI and the new options do not exist.

- [ ] **Step 3: Implement the CLI wiring**

Modify `src/wiki2md/cli.py`:

```python
from wiki2md.batch_models import BatchRunConfig
from wiki2md.batch_runtime import run_batch


@app.command()
def batch(
    file: Path,
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    concurrency: int = typer.Option(4, "--concurrency"),
    resume: Path | None = typer.Option(None, "--resume"),
    skip_invalid: bool = typer.Option(False, "--skip-invalid"),
) -> None:
    """Process a text or jsonl batch manifest of Wikipedia URLs."""
    config = BatchRunConfig(
        concurrency=concurrency,
        overwrite=overwrite,
        skip_invalid=skip_invalid,
        max_retries=2,
    )
    result = run_batch(
        manifest_path=file,
        output_root=output_dir,
        service_factory=lambda: build_service(output_dir),
        config=config,
        resume_path=resume,
    )

    for entry in result.entries:
        if entry.status in {"success", "failed", "skipped_existing", "invalid", "duplicate"}:
            label = entry.status.upper()
            subject = entry.url or entry.entry_key
            typer.echo(f"{label} {subject}")

    typer.echo(f"Summary: {json.dumps(result.totals, ensure_ascii=False, sort_keys=True)}")
```

- [ ] **Step 4: Run the CLI tests to verify they pass**

Run:

```bash
uv run pytest tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wiki2md/cli.py tests/test_cli.py
git commit -m "feat: wire batch runtime into cli"
```

### Task 6: Update Docs, Examples, And Full Verification

**Files:**
- Modify: `README.md`
- Create: `examples/batch/person-manifest.jsonl`
- Modify: `tests/test_project_docs.py`

- [ ] **Step 1: Write the failing docs tests for batch manifests and retry artifacts**

Extend `tests/test_project_docs.py`:

```python
def test_readme_mentions_batch_manifest_resume_and_failed_jsonl() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "jsonl" in readme
    assert "--resume" in readme
    assert "failed.jsonl" in readme
    assert "output/.wiki2md/batches/" in readme


def test_example_batch_manifest_is_valid_jsonl() -> None:
    lines = Path("examples/batch/person-manifest.jsonl").read_text(encoding="utf-8").splitlines()

    payloads = [json.loads(line) for line in lines if line.strip()]
    assert payloads[0]["url"].startswith("https://")
    assert payloads[0]["page_type"] == "person"
    assert isinstance(payloads[0]["tags"], list)
```

- [ ] **Step 2: Run the docs tests to verify they fail**

Run:

```bash
uv run pytest tests/test_project_docs.py -q
```

Expected: FAIL because the README does not document the new batch runtime and the example manifest file does not exist.

- [ ] **Step 3: Update README and add a minimal manifest example**

Update `README.md` with a structured batch section:

```markdown
## Batch Manifests

`wiki2md batch FILE` accepts either:

- plain text (`.txt`) with one URL per line
- structured `jsonl` manifests

Example `jsonl` manifest:

```json
{"url":"https://en.wikipedia.org/wiki/Andrej_Karpathy","page_type":"person","slug":"andrej-karpathy","tags":["ai","person"],"output_group":"people-ai"}
{"url":"https://en.wikipedia.org/wiki/Fei-Fei_Li","page_type":"person","tags":["ai","vision"],"output_group":"people-ai"}
```

Useful flags:

```bash
wiki2md batch examples/batch/person-manifest.jsonl --output-dir output --concurrency 4
wiki2md batch examples/batch/person-manifest.jsonl --output-dir output --resume output/.wiki2md/batches/6fa459eaee8a/state.json
```

Batch artifacts:

- `output/.wiki2md/batches/6fa459eaee8a/batch-report.json`
- `output/.wiki2md/batches/6fa459eaee8a/failed.txt`
- `output/.wiki2md/batches/6fa459eaee8a/failed.jsonl`
- `output/.wiki2md/batches/6fa459eaee8a/invalid.jsonl` when `--skip-invalid` is used

Use `failed.jsonl` as the preferred retry input because it preserves manifest metadata such as `slug`, `tags`, and `output_group`.
```

Create `examples/batch/person-manifest.jsonl`:

```json
{"url":"https://en.wikipedia.org/wiki/Andrej_Karpathy","page_type":"person","slug":"andrej-karpathy","tags":["ai","person"],"output_group":"people-ai"}
{"url":"https://en.wikipedia.org/wiki/Geoffrey_Hinton","page_type":"person","tags":["ai","deep-learning"],"output_group":"people-ai"}
```

- [ ] **Step 4: Run the docs tests to verify they pass**

Run:

```bash
uv run pytest tests/test_project_docs.py -q
```

Expected: PASS.

- [ ] **Step 5: Run the full verification suite**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv build
```

Expected:

- all tests pass
- ruff passes
- build succeeds

- [ ] **Step 6: Commit**

```bash
git add README.md examples/batch/person-manifest.jsonl tests/test_project_docs.py
git commit -m "docs: add batch manifest workflow"
```

## Self-Review

Spec coverage check:

- manifest contract: covered by Task 2
- output path and metadata threading: covered by Task 1
- state location and report artifacts: covered by Task 3
- runner semantics, retries, and resume: covered by Task 4
- CLI flags and public entrypoint: covered by Task 5
- README/examples/docs contract: covered by Task 6

Placeholder scan:

- no `TODO`, `TBD`, or deferred implementation notes remain in task steps
- each task includes exact file paths, concrete tests, commands, and commit points

Type consistency check:

- `ConversionContext` is introduced in Task 1 and reused by Tasks 4 and 5
- `BatchRunConfig`, `BatchStateEntry`, and `BatchRunResult` are introduced in Task 3 before Task 4 depends on them
- `BatchManifestEntry` and `PlannedBatchTask` are introduced in Task 2 before state/report/runtime tasks consume them
