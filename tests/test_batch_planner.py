from pathlib import Path

from wiki2md.batch_models import BatchManifestEntry
from wiki2md.batch_planner import plan_batch_tasks


def test_plan_batch_tasks_prefers_manifest_slug_and_builds_output_dir() -> None:
    tasks, duplicates = plan_batch_tasks(
        [
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                slug="karpathy-manifest",
                output_group="people-ai",
                tags=["ai"],
            )
        ],
        output_root=Path("output"),
    )

    assert duplicates == []
    assert tasks[0].resolved_slug == "karpathy-manifest"
    assert tasks[0].relative_output_dir == "person/people-ai/karpathy-manifest"


def test_plan_batch_tasks_skips_duplicate_urls_and_duplicate_output_dirs() -> None:
    tasks, duplicates = plan_batch_tasks(
        [
            BatchManifestEntry(url="https://en.wikipedia.org/wiki/Andrej_Karpathy"),
            BatchManifestEntry(url="https://en.wikipedia.org/wiki/Andrej_Karpathy"),
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Andrej_Karpathy_(researcher)",
                slug="andrej-karpathy",
            ),
        ],
        output_root=Path("output"),
    )

    assert len(tasks) == 1
    assert len(duplicates) == 2
    assert {item.reason for item in duplicates} == {"duplicate_url", "duplicate_output_dir"}
    assert {item.relative_output_dir for item in duplicates} == {"person/default/andrej-karpathy"}
