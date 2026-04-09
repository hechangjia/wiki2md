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


class BatchRunConfig(BaseModel):
    concurrency: int = 4
    overwrite: bool = False
    skip_invalid: bool = False
    max_retries: int = 2


BatchEntryStatus = Literal[
    "pending",
    "success",
    "failed",
    "skipped_existing",
    "invalid",
    "duplicate",
]


class BatchStateEntry(BaseModel):
    entry_key: str
    url: str
    status: BatchEntryStatus
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
