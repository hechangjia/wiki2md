import json
import shutil
from pathlib import Path

from wiki2md.document import InfoboxData, ReferenceEntry, SectionEvidence
from wiki2md.errors import WriteError
from wiki2md.models import ArticleMetadata, ConversionResult, UrlResolution


def normalize_relative_output_dir(relative_output_dir: Path) -> Path:
    if relative_output_dir.is_absolute():
        raise WriteError(f"Output path must be relative: {relative_output_dir}")
    if not relative_output_dir.parts or relative_output_dir.name in {"", "."}:
        raise WriteError("Output path must include a final directory name")
    if ".." in relative_output_dir.parts:
        raise WriteError(f"Output path cannot escape output root: {relative_output_dir}")
    return relative_output_dir


def _metadata_payload(metadata: ArticleMetadata) -> dict[str, object]:
    payload = metadata.model_dump(mode="json")
    for key in ("output_group", "manifest_slug", "resolved_slug", "batch_id"):
        if payload.get(key) is None:
            payload.pop(key, None)
    if not payload.get("tags"):
        payload.pop("tags", None)
    return payload


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
    section_evidence: list[SectionEvidence] | None = None,
    sources_markdown: str | None = None,
) -> ConversionResult:
    relative_output_dir = normalize_relative_output_dir(relative_output_dir)
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
    section_evidence_path = temp_dir / "section_evidence.json"
    sources_path = temp_dir / "sources.md"
    assets_path = temp_dir / "assets"

    article_path.write_text(markdown, encoding="utf-8")
    meta_path.write_text(
        json.dumps(_metadata_payload(metadata), indent=2, ensure_ascii=False) + "\n",
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
    section_evidence_path.write_text(
        json.dumps(
            {
                "title": metadata.title,
                "sections": [
                    section.model_dump(mode="json") for section in (section_evidence or [])
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    sources_path.write_text(sources_markdown or "", encoding="utf-8")

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
