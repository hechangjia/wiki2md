import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from wiki2md.assets import download_assets, select_assets
from wiki2md.client import MediaWikiClient
from wiki2md.models import ArticleMetadata, ConversionResult, InspectionResult
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

    def convert_url(self, url: str, overwrite: bool = False) -> ConversionResult:
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
                references=document.references,
                staging_assets_dir=staging_assets_dir,
                overwrite=overwrite,
            )
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
