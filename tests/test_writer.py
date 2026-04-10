import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from wiki2md.document import (
    InfoboxData,
    InfoboxField,
    ReferenceEntry,
    ReferenceLink,
    SectionEvidence,
    SectionEvidenceSource,
)
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
        relative_output_dir=Path("people") / resolution.slug,
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
    meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta_payload["source_lang"] == "en"
    assert "output_group" not in meta_payload
    assert "manifest_slug" not in meta_payload
    assert "resolved_slug" not in meta_payload
    assert "tags" not in meta_payload
    assert "batch_id" not in meta_payload
    references_payload = json.loads(
        (Path(result.output_dir) / "references.json").read_text(encoding="utf-8")
    )
    assert references_payload == [
        {"id": None, "text": "Reference number one.", "primary_url": None, "links": []}
    ]
    infobox_payload = json.loads(
        (Path(result.output_dir) / "infobox.json").read_text(encoding="utf-8")
    )
    assert infobox_payload == {"title": "Andrej Karpathy", "image": None, "fields": []}

def test_write_bundle_uses_custom_relative_output_dir(tmp_path: Path) -> None:
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
        page_type="person",
        output_group="people-ai",
        manifest_slug="karpathy-manifest",
        resolved_slug="karpathy-final",
        tags=["ai", "person"],
        batch_id="batch-123",
    )

    result = write_bundle(
        output_root=tmp_path / "output",
        relative_output_dir=Path("person/people-ai/karpathy-final"),
        resolution=resolution,
        markdown="# Andrej Karpathy\n",
        metadata=metadata,
        references=[],
        infobox=None,
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    assert Path(result.output_dir) == (
        tmp_path / "output" / "person" / "people-ai" / "karpathy-final"
    )


@pytest.mark.parametrize(
    ("relative_output_dir"),
    [
        Path("/tmp/escape"),
        Path("../escape"),
        Path("person/../escape"),
    ],
)
def test_write_bundle_rejects_unsafe_relative_output_dir(
    tmp_path: Path,
    relative_output_dir: Path,
) -> None:
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

    with pytest.raises(WriteError):
        write_bundle(
            output_root=tmp_path / "output",
            relative_output_dir=relative_output_dir,
            resolution=resolution,
            markdown="# Andrej Karpathy\n",
            metadata=metadata,
            references=[],
            infobox=None,
            staging_assets_dir=staging_assets,
            overwrite=False,
        )


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
        relative_output_dir=Path("people") / resolution.slug,
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


def test_write_bundle_writes_section_evidence_and_sources(tmp_path: Path) -> None:
    staging_assets = tmp_path / "assets"
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
        retrieved_at=datetime(2026, 4, 10, tzinfo=UTC),
    )

    result = write_bundle(
        output_root=tmp_path / "output",
        relative_output_dir=Path("person/default/example"),
        resolution=resolution,
        markdown="# Example\n",
        metadata=metadata,
        references=[],
        infobox=None,
        section_evidence=[
            SectionEvidence(
                section_id="career",
                heading="Career",
                level=2,
                paragraph_count=1,
                reference_ids=["cite_note-2"],
                reference_count=1,
                primary_urls=["https://example.com/source"],
                sources=[
                    SectionEvidenceSource(
                        id="cite_note-2",
                        text="Example source.",
                        primary_url="https://example.com/source",
                        link_kinds=["external"],
                    )
                ],
            )
        ],
        sources_markdown="# Sources for Example\n",
        staging_assets_dir=staging_assets,
        overwrite=False,
    )

    bundle_dir = Path(result.output_dir)
    assert (bundle_dir / "section_evidence.json").exists()
    assert (bundle_dir / "sources.md").read_text(encoding="utf-8").startswith(
        "# Sources for Example"
    )


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
            relative_output_dir=Path("people") / resolution.slug,
            resolution=resolution,
            markdown="# Andrej Karpathy\n",
            metadata=metadata,
            references=[],
            infobox=None,
            staging_assets_dir=tmp_path / "staging-assets",
            overwrite=False,
        )

    assert not (output_root / ".tmp" / "people" / "andrej-karpathy").exists()


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
        relative_output_dir=Path("people") / resolution.slug,
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
