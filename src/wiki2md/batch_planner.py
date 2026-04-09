from pathlib import Path

from wiki2md.batch_models import BatchManifestEntry, DuplicateBatchEntry, PlannedBatchTask
from wiki2md.urls import resolve_wikipedia_url


def plan_batch_tasks(
    entries: list[BatchManifestEntry],
    output_root: Path,
) -> tuple[list[PlannedBatchTask], list[DuplicateBatchEntry]]:
    del output_root

    tasks: list[PlannedBatchTask] = []
    duplicates: list[DuplicateBatchEntry] = []
    seen_urls: set[str] = set()
    seen_output_dirs: set[str] = set()

    for entry in entries:
        resolution = resolve_wikipedia_url(entry.url)
        if resolution.normalized_url in seen_urls:
            duplicates.append(DuplicateBatchEntry(entry=entry, reason="duplicate_url"))
            continue

        resolved_slug = entry.slug or resolution.slug
        relative_output_dir = f"{entry.page_type}/{entry.output_group}/{resolved_slug}"
        if relative_output_dir in seen_output_dirs:
            duplicates.append(DuplicateBatchEntry(entry=entry, reason="duplicate_output_dir"))
            continue

        seen_urls.add(resolution.normalized_url)
        seen_output_dirs.add(relative_output_dir)

        tasks.append(
            PlannedBatchTask(
                entry=entry,
                resolution=resolution,
                resolved_slug=resolved_slug,
                relative_output_dir=relative_output_dir,
                entry_key=f"{resolution.normalized_url}|{relative_output_dir}",
            )
        )

    return tasks, duplicates
