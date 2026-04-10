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
    assert tasks[0].relative_output_dir == "people/karpathy-manifest"


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
    assert {item.relative_output_dir for item in duplicates} == {"people/andrej-karpathy"}


def test_plan_batch_tasks_treats_different_output_groups_as_one_canonical_slug() -> None:
    tasks, duplicates = plan_batch_tasks(
        [
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
                output_group="turing-award",
            ),
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Geoffrey_Hinton_(researcher)",
                slug="geoffrey-hinton",
                output_group="ai-core",
            ),
        ],
        output_root=Path("output"),
    )

    assert len(tasks) == 1
    assert len(duplicates) == 1
    assert duplicates[0].relative_output_dir == "people/geoffrey-hinton"


def test_plan_batch_tasks_keeps_people_output_root_for_generic_entries() -> None:
    tasks, duplicates = plan_batch_tasks(
        [
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Linux",
                page_type=None,
            )
        ],
        output_root=Path("output"),
    )

    assert duplicates == []
    assert tasks[0].relative_output_dir == "people/linux"
