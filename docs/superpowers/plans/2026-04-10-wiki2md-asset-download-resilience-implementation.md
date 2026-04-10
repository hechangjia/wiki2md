# wiki2md Asset Download Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Wikimedia asset downloads retry transient failures and degrade gracefully so article export still succeeds when individual assets remain unavailable.

**Architecture:** Keep asset selection unchanged, but make the downloader return explicit success and failure results. The service layer will render and persist only the successfully downloaded assets while surfacing skipped assets as warnings.

**Tech Stack:** Python, httpx, pytest, respx, pydantic

---

### Task 1: Lock in downloader behavior with tests

**Files:**
- Modify: `tests/test_assets.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_download_assets_retries_429_then_succeeds(...):
    ...


def test_download_assets_does_not_retry_404(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_assets.py -v`
Expected: FAIL because `download_assets()` currently raises instead of retrying or returning partial results.

- [ ] **Step 3: Write minimal implementation**

```python
class AssetDownloadReport(BaseModel):
    downloaded: list[SelectedAsset] = Field(default_factory=list)
    failures: list[AssetDownloadFailure] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_assets.py -v`
Expected: PASS

### Task 2: Lock in service-level degradation behavior

**Files:**
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_convert_url_skips_failed_assets_and_records_warnings(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_service.py::test_convert_url_skips_failed_assets_and_records_warnings -v`
Expected: FAIL because the service currently assumes all selected assets are downloadable.

- [ ] **Step 3: Write minimal implementation**

```python
download_report = download_assets(...)
asset_map = {asset.title: asset.relative_path for asset in download_report.downloaded}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_service.py -v`
Expected: PASS

### Task 3: Verify targeted regression coverage

**Files:**
- Modify: `src/wiki2md/assets.py`
- Modify: `src/wiki2md/models.py`
- Modify: `src/wiki2md/service.py`
- Modify: `tests/test_assets.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Run targeted suite**

Run: `uv run pytest tests/test_assets.py tests/test_service.py -v`
Expected: PASS

- [ ] **Step 2: Run full suite**

Run: `uv run pytest -v`
Expected: PASS
