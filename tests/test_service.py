import json
from pathlib import Path

from wiki2md.document import (
    Document,
    InfoboxData,
    InfoboxField,
    InfoboxImage,
    ParagraphBlock,
    ReferenceEntry,
    ReferenceLink,
    SectionEvidence,
)
from wiki2md.models import ConversionContext, ConversionResult, SelectedAsset
from wiki2md.service import Wiki2MdService


class FakeClient:
    user_agent = "wiki2md-test-bot/0.1 (2136414704@qq.com)"

    def fetch_article(self, resolution):
        from wiki2md.models import FetchedArticle

        return FetchedArticle(
            resolution=resolution,
            canonical_title="Andrej Karpathy",
            pageid=12345,
            revid=67890,
            html="<html></html>",
            media=[],
        )


def test_convert_url_orchestrates_pipeline(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")

    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(
            title="Andrej Karpathy",
            infobox=InfoboxData(
                title="Andrej Karpathy",
                image=None,
                fields=[
                    InfoboxField(
                        label="Occupation",
                        text="Computer scientist",
                        links=[],
                    )
                ],
            ),
            summary=["Andrej Karpathy is a computer scientist."],
            blocks=[ParagraphBlock(text="Karpathy worked at OpenAI.")],
            references=[
                ReferenceEntry(
                    id="cite_note-example-1",
                    text="Reference number one.",
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
        ),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: None,
    )
    monkeypatch.setattr(
        "wiki2md.service.render_markdown",
        lambda document, metadata, asset_map: "# Andrej Karpathy\n",
    )

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Andrej_Karpathy",
        overwrite=False,
    )

    assert isinstance(result, ConversionResult)
    assert Path(result.article_path).exists()
    assert Path(result.references_path).exists()
    assert (Path(result.output_dir) / "infobox.json").exists()
    assert json.loads(Path(result.references_path).read_text(encoding="utf-8")) == [
        {
            "id": "cite_note-example-1",
            "text": "Reference number one.",
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
    payload = json.loads(Path(result.meta_path).read_text(encoding="utf-8"))
    assert payload["cleanup_stats"] == {
        "blocks": 1,
        "references": 1,
        "images_selected": 0,
        "infobox_fields": 1,
        "has_infobox": True,
    }
    assert "resolved_slug" not in payload
    assert result.asset_count == 0


def test_convert_url_backfills_infobox_image_path_from_selected_assets(
    monkeypatch, tmp_path: Path
) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")

    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(
            title="Andrej Karpathy",
            infobox=InfoboxData(
                title="Andrej Karpathy",
                image=InfoboxImage(
                    title="File:Andrej_Karpathy_2024.jpg",
                    alt="Andrej Karpathy portrait",
                    caption="Karpathy in 2024",
                ),
                fields=[InfoboxField(label="Occupation", text="Computer scientist", links=[])],
            ),
            summary=["Andrej Karpathy is a computer scientist."],
        ),
    )
    monkeypatch.setattr(
        "wiki2md.service.select_assets",
        lambda document, media: [
            SelectedAsset(
                title="File:Andrej_Karpathy_2024.jpg",
                source_url="https://upload.wikimedia.org/example.jpg",
                filename="001-infobox.jpg",
                relative_path="assets/001-infobox.jpg",
            )
        ],
    )
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: None,
    )
    monkeypatch.setattr(
        "wiki2md.service.render_markdown",
        lambda document, metadata, asset_map: "# Andrej Karpathy\n",
    )

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Andrej_Karpathy",
        overwrite=False,
    )

    infobox_payload = json.loads(
        (Path(result.output_dir) / "infobox.json").read_text(encoding="utf-8")
    )
    assert infobox_payload["image"]["path"] == "assets/001-infobox.jpg"


def test_convert_url_threads_batch_context_into_metadata(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")
    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(title="Andrej Karpathy", summary=["Example summary."]),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: None,
    )
    monkeypatch.setattr(
        "wiki2md.service.render_markdown",
        lambda document, metadata, asset_map: "# Andrej Karpathy\n",
    )

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Andrej_Karpathy",
        context=ConversionContext(
            relative_output_dir="person/people-ai/karpathy-final",
            page_type="person",
            output_group="people-ai",
            manifest_slug="karpathy-manifest",
            resolved_slug="karpathy-final",
            tags=["ai", "person"],
            batch_id="batch-123",
        ),
    )

    payload = json.loads(Path(result.meta_path).read_text(encoding="utf-8"))
    assert payload["page_type"] == "person"
    assert payload["output_group"] == "people-ai"
    assert payload["manifest_slug"] == "karpathy-manifest"
    assert payload["resolved_slug"] == "karpathy-final"
    assert payload["tags"] == ["ai", "person"]
    assert payload["batch_id"] == "batch-123"


def test_convert_url_derives_resolved_slug_from_relative_output_dir(
    monkeypatch, tmp_path: Path
) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")
    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(title="Andrej Karpathy", summary=["Example summary."]),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: None,
    )
    monkeypatch.setattr(
        "wiki2md.service.render_markdown",
        lambda document, metadata, asset_map: "# Andrej Karpathy\n",
    )

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Andrej_Karpathy",
        context=ConversionContext(
            relative_output_dir="person/people-ai/custom-slug",
            page_type="person",
            output_group="people-ai",
            manifest_slug="karpathy-manifest",
        ),
    )

    payload = json.loads(Path(result.meta_path).read_text(encoding="utf-8"))
    assert payload["resolved_slug"] == "custom-slug"


def test_convert_url_writes_section_evidence_artifacts(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")
    document = Document(
        title="Example",
        summary=["Lead."],
        section_evidence=[
            SectionEvidence(
                section_id="career",
                heading="Career",
                level=2,
                paragraph_count=1,
                reference_ids=[],
                reference_count=0,
                primary_urls=[],
                sources=[],
            )
        ],
    )
    monkeypatch.setattr("wiki2md.service.normalize_article", lambda article: document)
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: None,
    )
    monkeypatch.setattr(
        "wiki2md.service.render_markdown",
        lambda document, metadata, asset_map: "# Example\n",
    )

    result = service.convert_url("https://en.wikipedia.org/wiki/Example")

    bundle_dir = Path(result.output_dir)
    assert (bundle_dir / "section_evidence.json").exists()
    assert (bundle_dir / "sources.md").exists()
