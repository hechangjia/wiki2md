import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from wiki2md.assets import download_assets, select_assets
from wiki2md.client import MediaWikiClient
from wiki2md.document import Document
from wiki2md.models import ArticleMetadata, ConversionContext, ConversionResult, InspectionResult
from wiki2md.normalize import normalize_article
from wiki2md.render_markdown import render_markdown
from wiki2md.urls import resolve_wikipedia_url
from wiki2md.writer import normalize_relative_output_dir, write_bundle


def _with_infobox_asset_paths(document: Document, asset_map: dict[str, str]) -> Document:
    if document.infobox is None or document.infobox.image is None:
        return document

    relative_path = asset_map.get(document.infobox.image.title)
    if relative_path is None or document.infobox.image.path == relative_path:
        return document

    return document.model_copy(
        update={
            "infobox": document.infobox.model_copy(
                update={
                    "image": document.infobox.image.model_copy(
                        update={"path": relative_path}
                    )
                }
            )
        }
    )


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

    def convert_url(
        self,
        url: str,
        overwrite: bool = False,
        context: ConversionContext | None = None,
    ) -> ConversionResult:
        resolution = resolve_wikipedia_url(url)
        relative_output_dir = normalize_relative_output_dir(Path("people") / resolution.slug)
        resolved_slug: str | None = None
        if context is not None:
            relative_output_dir = normalize_relative_output_dir(Path(context.relative_output_dir))
            resolved_slug = relative_output_dir.name

        article = self.client.fetch_article(resolution)
        document = normalize_article(article)
        selected_assets = select_assets(document, article.media)
        asset_map = {asset.title: asset.relative_path for asset in selected_assets}
        document = _with_infobox_asset_paths(document, asset_map)

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
                page_type=context.page_type if context is not None else "person",
                image_manifest=[
                    {"title": asset.title, "path": asset.relative_path} for asset in selected_assets
                ],
                warnings=document.warnings,
                cleanup_stats={
                    "blocks": len(document.blocks),
                    "references": len(document.references),
                    "images_selected": len(selected_assets),
                    "infobox_fields": len(document.infobox.fields) if document.infobox else 0,
                    "has_infobox": document.infobox is not None,
                },
                output_group=context.output_group if context is not None else None,
                manifest_slug=context.manifest_slug if context is not None else None,
                resolved_slug=resolved_slug,
                tags=list(context.tags) if context is not None else [],
                batch_id=context.batch_id if context is not None else None,
            )
            markdown = render_markdown(
                document,
                metadata,
                asset_map,
            )

            return write_bundle(
                output_root=self.output_root,
                relative_output_dir=relative_output_dir,
                resolution=resolution,
                markdown=markdown,
                metadata=metadata,
                references=document.references,
                infobox=document.infobox,
                staging_assets_dir=staging_assets_dir,
                overwrite=overwrite,
            )
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
