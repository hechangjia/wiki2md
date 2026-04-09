import json
from pathlib import Path

from pydantic import ValidationError

from wiki2md.batch_models import BatchManifestEntry, InvalidManifestRow
from wiki2md.errors import BatchManifestValidationError


def _parse_manifest_line(manifest_path: Path, line: str) -> dict[str, object]:
    if manifest_path.suffix == ".jsonl":
        return json.loads(line)
    return {"url": line}


def load_manifest_entries(
    manifest_path: Path,
    skip_invalid: bool,
) -> tuple[list[BatchManifestEntry], list[InvalidManifestRow]]:
    entries: list[BatchManifestEntry] = []
    invalid_rows: list[InvalidManifestRow] = []
    lines = manifest_path.read_text(encoding="utf-8").splitlines()

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            payload = _parse_manifest_line(manifest_path, line)
            entry = BatchManifestEntry.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            invalid_rows.append(
                InvalidManifestRow(
                    line_number=line_number,
                    raw_text=raw_line,
                    error=str(exc),
                )
            )
            continue

        entries.append(entry)

    if invalid_rows and not skip_invalid:
        raise BatchManifestValidationError(invalid_rows)

    return entries, invalid_rows
