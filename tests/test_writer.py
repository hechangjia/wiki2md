import json
from datetime import UTC, datetime
from pathlib import Path

from wiki2md.models import ArticleMetadata, UrlResolution
from wiki2md.writer import write_bundle


def test_write_bundle_creates_expected_artifacts(tmp_path: Path) -> None:
    staging_assets = tmp_path / "staging-assets"
    staging_assets.mkdir()
    (staging_assets / "001-infobox.jpg").write_bytes(b"image-binary")

    resolution = UrlResolution(
        source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        normalized_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        lang="en",
        title="Andrej_Karpathy",
        slug="andrej-karpathy",
    )
    metadata = ArticleMetadata(
        title="Andrej Karpathy",
        source_url=resolution.source_url,
        source_lang="en",
        retrieved_at=datetime(2026, 4, 8, tzinfo=UTC),
        pageid=12345,
        revid=67890,
        image_manifest=[
            {
                "title": "File:Andrej_Karpathy_2024.jpg",
                "path": "assets/001-infobox.jpg",
            }
        ],
        cleanup_stats={"blocks": 3, "references": 1, "images_selected": 1},
    )

    result = write_bundle(
        output_root=tmp_path / "output",
        resolution=resolution,
        markdown="# Andrej Karpathy\n",
        metadata=metadata,
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    article_path = Path(result.article_path)
    meta_path = Path(result.meta_path)

    assert article_path.exists()
    assert meta_path.exists()
    assert (Path(result.output_dir) / "assets" / "001-infobox.jpg").exists()
    assert json.loads(meta_path.read_text(encoding="utf-8"))["source_lang"] == "en"
