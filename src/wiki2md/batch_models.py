from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wiki2md.models import UrlResolution
from wiki2md.urls import slugify_title


def _normalize_path_segment(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty")

    path = Path(stripped)
    if path.is_absolute() or len(path.parts) != 1 or stripped in {".", ".."}:
        raise ValueError(f"{field_name} must be a single safe path segment")

    normalized = slugify_title(stripped)
    if normalized in {"", ".", ".."}:
        raise ValueError(f"{field_name} must resolve to a non-empty safe path segment")

    return normalized


class BatchManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    page_type: Literal["person"] = "person"
    slug: str | None = None
    tags: list[str] = Field(default_factory=list)
    output_group: str = "default"

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_path_segment(value, field_name="slug")

    @field_validator("output_group")
    @classmethod
    def normalize_output_group(cls, value: str) -> str:
        return _normalize_path_segment(value, field_name="output_group")


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
    resolved_slug: str
    relative_output_dir: str


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
