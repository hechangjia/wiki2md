import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from wiki2md.document import InfoboxData, InfoboxField, ReferenceEntry, ReferenceLink
from wiki2md.errors import WriteError
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
        references=[ReferenceEntry(text="Reference number one.")],
        infobox=None,
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    article_path = Path(result.article_path)
    meta_path = Path(result.meta_path)

    assert article_path.exists()
    assert meta_path.exists()
    assert (Path(result.output_dir) / "references.json").exists()
    assert (Path(result.output_dir) / "assets" / "001-infobox.jpg").exists()
    assert json.loads(meta_path.read_text(encoding="utf-8"))["source_lang"] == "en"
    references_payload = json.loads(
        (Path(result.output_dir) / "references.json").read_text(encoding="utf-8")
    )
    assert references_payload == [
        {"id": None, "text": "Reference number one.", "primary_url": None, "links": []}
    ]


def test_write_bundle_serializes_reference_primary_urls(tmp_path: Path) -> None:
    staging_assets = tmp_path / "staging-assets"
    staging_assets.mkdir()
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
        retrieved_at=datetime(2026, 4, 9, tzinfo=UTC),
    )
    result = write_bundle(
        output_root=tmp_path / "output",
        resolution=resolution,
        markdown="# Andrej Karpathy\n",
        metadata=metadata,
        references=[
            ReferenceEntry(
                id="cite_note-example-1",
                text="Example article.",
                primary_url="https://example.com/source",
                links=[
                    ReferenceLink(
                        text="Example source",
                        href="https://example.com/source",
                        kind="external",
                    )
                ],
            )
        ],
        infobox=None,
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    payload = json.loads(Path(result.references_path).read_text(encoding="utf-8"))
    assert payload == [
        {
            "id": "cite_note-example-1",
            "text": "Example article.",
            "primary_url": "https://example.com/source",
            "links": [
                {
                    "text": "Example source",
                    "href": "https://example.com/source",
                    "kind": "external",
                }
            ],
        }
    ]


def test_write_bundle_does_not_leave_temp_dir_when_output_exists(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    final_dir = output_root / "people" / "andrej-karpathy"
    final_dir.mkdir(parents=True)
    (final_dir / "article.md").write_text("existing", encoding="utf-8")

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
    )

    with pytest.raises(WriteError):
        write_bundle(
            output_root=output_root,
            resolution=resolution,
            markdown="# Andrej Karpathy\n",
            metadata=metadata,
            references=[],
            infobox=None,
            staging_assets_dir=tmp_path / "staging-assets",
            overwrite=False,
        )

    assert not (output_root / ".tmp" / "andrej-karpathy").exists()


def test_write_bundle_writes_infobox_sidecar(tmp_path: Path) -> None:
    staging_assets = tmp_path / "staging-assets"
    staging_assets.mkdir()

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
        retrieved_at=datetime(2026, 4, 9, tzinfo=UTC),
        cleanup_stats={
            "blocks": 1,
            "references": 0,
            "images_selected": 0,
            "infobox_fields": 2,
            "has_infobox": True,
        },
    )

    result = write_bundle(
        output_root=tmp_path / "output",
        resolution=resolution,
        markdown="# Andrej Karpathy\n",
        metadata=metadata,
        references=[],
        infobox=InfoboxData(
            title="Andrej Karpathy",
            image=None,
            fields=[
                InfoboxField(
                    label="Born",
                    text="3 October 1986 Bratislava, Czechoslovakia",
                    links=[],
                ),
                InfoboxField(label="Occupation", text="Computer scientist", links=[]),
            ],
        ),
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    assert json.loads((Path(result.output_dir) / "infobox.json").read_text(encoding="utf-8")) == {
        "title": "Andrej Karpathy",
        "image": None,
        "fields": [
            {
                "label": "Born",
                "text": "3 October 1986 Bratislava, Czechoslovakia",
                "links": [],
            },
            {"label": "Occupation", "text": "Computer scientist", "links": []},
        ],
    }
