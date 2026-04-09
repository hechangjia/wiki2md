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
