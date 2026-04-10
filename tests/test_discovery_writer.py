import importlib
import json
from pathlib import Path

import pytest


def _load_discovery_models():
    try:
        return importlib.import_module("wiki2md.discovery_models")
    except ModuleNotFoundError as exc:
        pytest.fail(str(exc))


def _load_discovery_writer():
    try:
        return importlib.import_module("wiki2md.discovery_writer")
    except ModuleNotFoundError as exc:
        pytest.fail(str(exc))


def _build_run():
    discovery_models = _load_discovery_models()
    source = discovery_models.DiscoverySource(
        kind="preset",
        resolution=importlib.import_module("wiki2md.discovery_presets").resolve_discovery_source(
            "turing-award"
        ).resolution,
        slug="turing-award",
        source_title="Turing Award",
        output_group="turing-award",
        tags=["award", "computer-science", "turing-award"],
    )
    selected = [
        discovery_models.DiscoveryCandidate(
            url="https://en.wikipedia.org/wiki/Alan_Turing",
            title="Alan Turing",
            slug="alan-turing",
            anchor_text="Alan Turing",
            source_page="https://en.wikipedia.org/wiki/Turing_Award",
            depth=0,
            frequency=1,
            selection_reason="depth0-direct-link",
        ),
        discovery_models.DiscoveryCandidate(
            url="https://en.wikipedia.org/wiki/Donald_Knuth",
            title="Donald Knuth",
            slug="donald-knuth",
            anchor_text="Donald Knuth",
            source_page="https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates",
            depth=1,
            frequency=2,
            selection_reason="depth1-ranked-fill",
        ),
    ]
    candidates = selected + [
        discovery_models.DiscoveryCandidate(
            url="https://en.wikipedia.org/wiki/Bell_Labs",
            title="Bell Labs",
            slug="bell-labs",
            anchor_text="Bell Labs",
            source_page="https://en.wikipedia.org/wiki/Turing_Award",
            depth=0,
            frequency=1,
            rejected_reason="non-person",
        )
    ]
    return discovery_models.DiscoveryRun(
        source=source,
        candidates=candidates,
        selected_candidates=selected,
        expanded_pages=["https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates"],
        max_people=37,
    )


def test_write_discovery_bundle_writes_manifest_index_and_provenance(tmp_path: Path) -> None:
    discovery_writer = _load_discovery_writer()
    run = _build_run()

    bundle_dir = discovery_writer.write_discovery_bundle(run, output_root=tmp_path / "output")

    assert bundle_dir == tmp_path / "output" / "discovery" / "turing-award"
    assert (bundle_dir / "manifest.jsonl").exists()
    assert (bundle_dir / "index.md").exists()
    assert (bundle_dir / "discovery.json").exists()


def test_write_discovery_bundle_emits_batch_ready_manifest_rows(tmp_path: Path) -> None:
    discovery_writer = _load_discovery_writer()
    run = _build_run()

    bundle_dir = discovery_writer.write_discovery_bundle(run, output_root=tmp_path / "output")

    lines = (bundle_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    payloads = [json.loads(line) for line in lines]

    assert payloads == [
        {
            "url": "https://en.wikipedia.org/wiki/Alan_Turing",
            "page_type": "person",
            "slug": "alan-turing",
            "tags": ["award", "computer-science", "turing-award"],
            "output_group": "turing-award",
        },
        {
            "url": "https://en.wikipedia.org/wiki/Donald_Knuth",
            "page_type": "person",
            "slug": "donald-knuth",
            "tags": ["award", "computer-science", "turing-award"],
            "output_group": "turing-award",
        },
    ]


def test_write_discovery_bundle_renders_human_review_index_and_provenance_json(
    tmp_path: Path,
) -> None:
    discovery_writer = _load_discovery_writer()
    run = _build_run()

    bundle_dir = discovery_writer.write_discovery_bundle(run, output_root=tmp_path / "output")

    index_markdown = (bundle_dir / "index.md").read_text(encoding="utf-8")
    provenance = json.loads((bundle_dir / "discovery.json").read_text(encoding="utf-8"))

    assert "# Turing Award" in index_markdown
    assert "Discovered: 2 selected / 3 total candidates" in index_markdown
    assert "wiki2md batch output/discovery/turing-award/manifest.jsonl --output-dir output" in (
        index_markdown
    )
    assert "Alan Turing" in index_markdown
    assert "depth0-direct-link" in index_markdown

    assert provenance["source_url"] == "https://en.wikipedia.org/wiki/Turing_Award"
    assert provenance["source_title"] == "Turing Award"
    assert provenance["source_lang"] == "en"
    assert provenance["expanded_pages"] == [
        "https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates"
    ]
    assert provenance["selected_count"] == 2
    assert provenance["configured_limits"]["max_people"] == 37
    assert provenance["candidates"][2]["rejected_reason"] == "non-person"
