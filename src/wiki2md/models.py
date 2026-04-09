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
    cleanup_stats: dict[str, int | bool] = Field(default_factory=dict)


class InspectionResult(BaseModel):
    resolution: UrlResolution
    pageid: int | None = None
    revid: int | None = None
    media_count: int = 0


class ConversionResult(BaseModel):
    output_dir: str
    article_path: str
    meta_path: str
    references_path: str
    asset_count: int
    warnings: list[str] = Field(default_factory=list)
