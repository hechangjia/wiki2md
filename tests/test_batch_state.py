import json
from pathlib import Path

from wiki2md.batch_models import (
    BatchManifestEntry,
    BatchRunConfig,
    BatchRunResult,
    BatchStateEntry,
    InvalidManifestRow,
)
from wiki2md.batch_state import (
    build_batch_id,
    default_state_path,
    load_batch_state,
    save_batch_state,
    write_batch_reports,
)


def test_default_state_path_uses_output_hidden_batch_directory(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text("", encoding="utf-8")

    state_path = default_state_path(tmp_path / "output", manifest)

    assert state_path.parent.parent.parent == tmp_path / "output" / ".wiki2md"
    assert state_path.name == "state.json"


def test_build_batch_id_is_deterministic_for_manifest_path(tmp_path: Path) -> None:
    manifest = tmp_path / "people.jsonl"
    manifest.write_text("", encoding="utf-8")

    first = build_batch_id(manifest)
    second = build_batch_id(manifest)

    assert first == second
    assert len(first) == 12


def test_save_and_load_batch_state_roundtrip(tmp_path: Path) -> None:
    state_path = tmp_path / "output" / ".wiki2md" / "batches" / "batch-123" / "state.json"
    result = BatchRunResult(
        batch_id="batch-123",
        manifest_path="people.jsonl",
        output_root=str(tmp_path / "output"),
        config=BatchRunConfig(concurrency=4, overwrite=False, skip_invalid=False, max_retries=2),
        totals={"success": 1},
        entries=[
            BatchStateEntry(
                entry_key="entry-1",
                url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                status="success",
                relative_output_dir="person/default/andrej-karpathy",
                output_dir=str(tmp_path / "output" / "person" / "default" / "andrej-karpathy"),
            )
        ],
    )

    save_batch_state(state_path, result)
    loaded = load_batch_state(state_path)

    assert loaded.batch_id == "batch-123"
    assert loaded.entries[0].status == "success"


def test_write_batch_reports_writes_failed_and_invalid_artifacts(tmp_path: Path) -> None:
    batch_dir = tmp_path / "output" / ".wiki2md" / "batches" / "batch-123"
    result = BatchRunResult(
        batch_id="batch-123",
        manifest_path="people.jsonl",
        output_root=str(tmp_path / "output"),
        config=BatchRunConfig(concurrency=4, overwrite=False, skip_invalid=True, max_retries=2),
        totals={"failed": 1, "invalid": 1},
        entries=[
            BatchStateEntry(
                entry_key="failed-1",
                url="https://en.wikipedia.org/wiki/Bad_Page",
                status="failed",
                manifest_entry=BatchManifestEntry(
                    url="https://en.wikipedia.org/wiki/Bad_Page",
                    output_group="people-ai",
                ),
                error="Fetch failed",
            )
        ],
        invalid_rows=[
            InvalidManifestRow(
                line_number=2,
                raw_text='{"tags": "bad"}',
                error="Input should be a valid list",
            ),
        ],
    )

    write_batch_reports(batch_dir, result)

    assert json.loads((batch_dir / "batch-report.json").read_text(encoding="utf-8"))[
        "batch_id"
    ] == "batch-123"
    assert (
        batch_dir / "failed.txt"
    ).read_text(encoding="utf-8").strip() == "https://en.wikipedia.org/wiki/Bad_Page"
    assert "people-ai" in (batch_dir / "failed.jsonl").read_text(encoding="utf-8")
    assert "tags" in (batch_dir / "invalid.jsonl").read_text(encoding="utf-8")
