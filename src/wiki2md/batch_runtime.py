from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from wiki2md.batch_manifest import load_manifest_entries
from wiki2md.batch_models import (
    BatchRunConfig,
    BatchRunResult,
    BatchStateEntry,
    DuplicateBatchEntry,
    InvalidManifestRow,
    PlannedBatchTask,
)
from wiki2md.batch_planner import plan_batch_tasks
from wiki2md.batch_state import (
    default_state_path,
    load_batch_state,
    save_batch_state,
    write_batch_reports,
)
from wiki2md.errors import FetchError
from wiki2md.models import ConversionContext


def _entry_totals(entries: list[BatchStateEntry]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for entry in entries:
        totals[entry.status] = totals.get(entry.status, 0) + 1
    return totals


def _build_invalid_entries(invalid_rows: list[InvalidManifestRow]) -> list[BatchStateEntry]:
    entries: list[BatchStateEntry] = []
    for row in invalid_rows:
        entries.append(
            BatchStateEntry(
                entry_key=f"invalid:{row.line_number}",
                url="",
                status="invalid",
                error=row.error,
            )
        )
    return entries


def _build_duplicate_entries(duplicates: list[DuplicateBatchEntry]) -> list[BatchStateEntry]:
    entries: list[BatchStateEntry] = []
    for index, duplicate in enumerate(duplicates, start=1):
        resolved_slug = duplicate.entry.slug or ""
        relative_output_dir = (
            f"{duplicate.entry.page_type}/{duplicate.entry.output_group}/{resolved_slug}"
            if resolved_slug
            else None
        )
        entries.append(
            BatchStateEntry(
                entry_key=f"duplicate:{index}:{duplicate.reason}:{duplicate.entry.url}",
                url=duplicate.entry.url,
                status="duplicate",
                relative_output_dir=relative_output_dir,
                manifest_entry=duplicate.entry,
                error=duplicate.reason,
            )
        )
    return entries


def _run_task(
    task: PlannedBatchTask,
    output_root: Path,
    service_factory: Callable[[], object],
    config: BatchRunConfig,
    batch_id: str,
) -> BatchStateEntry:
    target_dir = output_root / task.relative_output_dir
    if target_dir.exists() and not config.overwrite:
        return BatchStateEntry(
            entry_key=task.entry_key,
            url=task.entry.url,
            status="skipped_existing",
            relative_output_dir=task.relative_output_dir,
            output_dir=str(target_dir),
            manifest_entry=task.entry,
        )

    attempt = 0
    while True:
        try:
            service = service_factory()
            try:
                conversion = service.convert_url(
                    task.entry.url,
                    overwrite=config.overwrite,
                    context=ConversionContext(
                        relative_output_dir=task.relative_output_dir,
                        page_type=task.entry.page_type,
                        output_group=task.entry.output_group,
                        manifest_slug=task.entry.slug,
                        resolved_slug=task.resolved_slug,
                        tags=task.entry.tags,
                        batch_id=batch_id,
                    ),
                )
            finally:
                client = getattr(service, "client", None)
                close = getattr(client, "close", None)
                if callable(close):
                    close()
            return BatchStateEntry(
                entry_key=task.entry_key,
                url=task.entry.url,
                status="success",
                relative_output_dir=task.relative_output_dir,
                output_dir=conversion.output_dir,
                manifest_entry=task.entry,
            )
        except FetchError as exc:
            if attempt >= config.max_retries:
                return BatchStateEntry(
                    entry_key=task.entry_key,
                    url=task.entry.url,
                    status="failed",
                    relative_output_dir=task.relative_output_dir,
                    manifest_entry=task.entry,
                    error=str(exc),
                )
            attempt += 1
        except Exception as exc:  # noqa: BLE001
            return BatchStateEntry(
                entry_key=task.entry_key,
                url=task.entry.url,
                status="failed",
                relative_output_dir=task.relative_output_dir,
                manifest_entry=task.entry,
                error=str(exc),
            )


def run_batch(
    manifest_path: Path,
    output_root: Path,
    service_factory: Callable[[], object],
    config: BatchRunConfig,
    resume_path: Path | None = None,
) -> BatchRunResult:
    entries, invalid_rows = load_manifest_entries(manifest_path, skip_invalid=config.skip_invalid)
    tasks, duplicates = plan_batch_tasks(entries, output_root=output_root)

    state_path = resume_path or default_state_path(output_root, manifest_path)
    if state_path.exists():
        result = load_batch_state(state_path)
        batch_id = result.batch_id
        state_by_key = {
            entry.entry_key: entry
            for entry in result.entries
            if entry.status not in {"invalid", "duplicate"}
        }
    else:
        batch_id = state_path.parent.name
        result = BatchRunResult(
            batch_id=batch_id,
            manifest_path=str(manifest_path),
            output_root=str(output_root),
            config=config,
            totals={},
            entries=[],
            invalid_rows=invalid_rows,
        )
        state_by_key: dict[str, BatchStateEntry] = {}

    static_entries = [
        *_build_invalid_entries(invalid_rows),
        *_build_duplicate_entries(duplicates),
    ]

    pending_tasks = []
    for task in tasks:
        existing = state_by_key.get(task.entry_key)
        if existing is not None and existing.status in {"success", "skipped_existing"}:
            continue
        pending_tasks.append(task)

    max_workers = max(1, config.concurrency)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_run_task, task, output_root, service_factory, config, batch_id)
            for task in pending_tasks
        ]
        for future in as_completed(futures):
            entry = future.result()
            state_by_key[entry.entry_key] = entry
            snapshot_entries = [*state_by_key.values(), *static_entries]
            snapshot = result.model_copy(
                update={
                    "batch_id": batch_id,
                    "manifest_path": str(manifest_path),
                    "output_root": str(output_root),
                    "config": config,
                    "entries": snapshot_entries,
                    "invalid_rows": invalid_rows,
                    "totals": _entry_totals(snapshot_entries),
                }
            )
            save_batch_state(state_path, snapshot)

    final_entries = [*state_by_key.values(), *static_entries]
    final_result = result.model_copy(
        update={
            "batch_id": batch_id,
            "manifest_path": str(manifest_path),
            "output_root": str(output_root),
            "config": config,
            "entries": final_entries,
            "invalid_rows": invalid_rows,
            "totals": _entry_totals(final_entries),
        }
    )
    save_batch_state(state_path, final_result)
    write_batch_reports(state_path.parent, final_result)
    return final_result
