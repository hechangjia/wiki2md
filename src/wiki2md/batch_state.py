import hashlib
import json
from pathlib import Path

from wiki2md.batch_models import BatchRunResult


def build_batch_id(manifest_path: Path) -> str:
    digest = hashlib.sha1(str(manifest_path.resolve()).encode("utf-8")).hexdigest()
    return digest[:12]


def default_state_path(output_root: Path, manifest_path: Path) -> Path:
    batch_id = build_batch_id(manifest_path)
    return output_root / ".wiki2md" / "batches" / batch_id / "state.json"


def load_batch_state(state_path: Path) -> BatchRunResult:
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return BatchRunResult.model_validate(payload)


def save_batch_state(state_path: Path, result: BatchRunResult) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_batch_reports(batch_dir: Path, result: BatchRunResult) -> None:
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "batch-report.json").write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    failed_entries = [entry for entry in result.entries if entry.status == "failed"]
    failed_text = "\n".join(entry.url for entry in failed_entries)
    if failed_text:
        failed_text += "\n"
    (batch_dir / "failed.txt").write_text(failed_text, encoding="utf-8")

    failed_jsonl_lines = [
        json.dumps(entry.manifest_entry.model_dump(mode="json"), ensure_ascii=False)
        for entry in failed_entries
        if entry.manifest_entry is not None
    ]
    failed_jsonl = "\n".join(failed_jsonl_lines)
    if failed_jsonl:
        failed_jsonl += "\n"
    (batch_dir / "failed.jsonl").write_text(failed_jsonl, encoding="utf-8")

    if result.invalid_rows:
        invalid_jsonl = "\n".join(
            json.dumps(row.model_dump(mode="json"), ensure_ascii=False)
            for row in result.invalid_rows
        )
        if invalid_jsonl:
            invalid_jsonl += "\n"
        (batch_dir / "invalid.jsonl").write_text(invalid_jsonl, encoding="utf-8")
