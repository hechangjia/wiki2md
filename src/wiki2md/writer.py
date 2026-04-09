import json
import shutil
from pathlib import Path

from wiki2md.errors import WriteError
from wiki2md.models import ArticleMetadata, ConversionResult, UrlResolution


def write_bundle(
    output_root: Path,
    resolution: UrlResolution,
    markdown: str,
    metadata: ArticleMetadata,
    staging_assets_dir: Path,
    overwrite: bool,
) -> ConversionResult:
    final_dir = output_root / "people" / resolution.slug
    temp_dir = output_root / ".tmp" / resolution.slug

    temp_dir.parent.mkdir(parents=True, exist_ok=True)
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    if final_dir.exists():
        if not overwrite:
            raise WriteError(f"Output already exists: {final_dir}")
        shutil.rmtree(final_dir)

    article_path = temp_dir / "article.md"
    meta_path = temp_dir / "meta.json"
    assets_path = temp_dir / "assets"

    article_path.write_text(markdown, encoding="utf-8")
    meta_path.write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if staging_assets_dir.exists():
        shutil.copytree(staging_assets_dir, assets_path)
    else:
        assets_path.mkdir()

    final_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.replace(final_dir)

    return ConversionResult(
        output_dir=str(final_dir),
        article_path=str(final_dir / "article.md"),
        meta_path=str(final_dir / "meta.json"),
        asset_count=len(list((final_dir / "assets").iterdir())),
        warnings=metadata.warnings,
    )
