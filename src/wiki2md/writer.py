import json
import shutil
from pathlib import Path

from wiki2md.document import InfoboxData, ReferenceEntry
from wiki2md.errors import WriteError
from wiki2md.models import ArticleMetadata, ConversionResult, UrlResolution


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

    if final_dir.exists():
        if not overwrite:
            raise WriteError(f"Output already exists: {final_dir}")
        shutil.rmtree(final_dir)

    temp_dir.parent.mkdir(parents=True, exist_ok=True)
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    article_path = temp_dir / "article.md"
    meta_path = temp_dir / "meta.json"
    references_path = temp_dir / "references.json"
    infobox_path = temp_dir / "infobox.json"
    assets_path = temp_dir / "assets"

    article_path.write_text(markdown, encoding="utf-8")
    meta_path.write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    references_path.write_text(
        json.dumps(
            [reference.model_dump(mode="json") for reference in references],
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    infobox_payload = (
        infobox if infobox is not None else InfoboxData(title=metadata.title)
    ).model_dump(mode="json")
    infobox_path.write_text(
        json.dumps(infobox_payload, indent=2, ensure_ascii=False) + "\n",
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
        references_path=str(final_dir / "references.json"),
        asset_count=len(list((final_dir / "assets").iterdir())),
        warnings=metadata.warnings,
    )
