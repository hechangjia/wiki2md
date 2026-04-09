import json
from pathlib import Path

import pytest

from wiki2md.batch_manifest import load_manifest_entries
from wiki2md.errors import BatchManifestValidationError


def test_load_manifest_entries_from_txt_defaults_metadata(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text("https://en.wikipedia.org/wiki/Andrej_Karpathy\n", encoding="utf-8")

    entries, invalid_rows = load_manifest_entries(manifest, skip_invalid=False)

    assert invalid_rows == []
    assert len(entries) == 1
    assert entries[0].url.endswith("/wiki/Andrej_Karpathy")
    assert entries[0].page_type == "person"
    assert entries[0].output_group == "default"
    assert entries[0].tags == []


def test_load_manifest_entries_rejects_invalid_rows_in_strict_mode(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text(
        json.dumps({"url": "https://en.wikipedia.org/wiki/Andrej_Karpathy", "tags": "ai"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BatchManifestValidationError):
        load_manifest_entries(manifest, skip_invalid=False)


def test_load_manifest_entries_skips_invalid_rows_when_requested(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "url": "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                        "output_group": "people-ai",
                    }
                ),
                json.dumps({"url": "https://en.wikipedia.org/wiki/Fei-Fei_Li", "tags": "ai"}),
            ]
        ),
        encoding="utf-8",
    )

    entries, invalid_rows = load_manifest_entries(manifest, skip_invalid=True)

    assert [entry.output_group for entry in entries] == ["people-ai"]
    assert len(invalid_rows) == 1
    assert invalid_rows[0].line_number == 2


def test_load_manifest_entries_rejects_unknown_fields_in_strict_mode(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text(
        json.dumps(
            {
                "url": "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                "outputGroup": "people-ai",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BatchManifestValidationError):
        load_manifest_entries(manifest, skip_invalid=False)


def test_load_manifest_entries_normalizes_manifest_segments(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text(
        json.dumps(
            {
                "url": "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                "slug": "Karpathy Manifest",
                "output_group": "People AI",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    entries, invalid_rows = load_manifest_entries(manifest, skip_invalid=False)

    assert invalid_rows == []
    assert entries[0].slug == "karpathy-manifest"
    assert entries[0].output_group == "people-ai"


def test_load_manifest_entries_skips_invalid_url_and_path_segments_when_requested(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"url": "https://en.wikipedia.org/wiki/Andrej_Karpathy"}),
                json.dumps({"url": "https://example.com/not-wiki"}),
                json.dumps(
                    {
                        "url": "https://en.wikipedia.org/wiki/Fei-Fei_Li",
                        "slug": "../escape",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    entries, invalid_rows = load_manifest_entries(manifest, skip_invalid=True)

    assert [entry.url for entry in entries] == ["https://en.wikipedia.org/wiki/Andrej_Karpathy"]
    assert [row.line_number for row in invalid_rows] == [2, 3]
