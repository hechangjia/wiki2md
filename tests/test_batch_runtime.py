from pathlib import Path

from wiki2md.batch_models import BatchRunConfig, BatchRunResult
from wiki2md.batch_runtime import run_batch
from wiki2md.errors import FetchError
from wiki2md.models import ConversionResult


class FakeService:
    def __init__(
        self,
        output_root: Path,
        failures: dict[str, int] | None = None,
        call_counts: dict[str, int] | None = None,
    ) -> None:
        self.output_root = output_root
        self.failures = failures or {}
        self.call_counts = call_counts

    def convert_url(self, url: str, overwrite: bool = False, context=None) -> ConversionResult:
        del overwrite
        if self.call_counts is not None:
            self.call_counts[url] = self.call_counts.get(url, 0) + 1

        remaining = self.failures.get(url, 0)
        if remaining > 0:
            self.failures[url] = remaining - 1
            raise FetchError(f"temporary failure for {url}")
        output_dir = self.output_root / context.relative_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        article_path = output_dir / "article.md"
        meta_path = output_dir / "meta.json"
        references_path = output_dir / "references.json"
        article_path.write_text("# Example\n", encoding="utf-8")
        meta_path.write_text("{}", encoding="utf-8")
        references_path.write_text("[]", encoding="utf-8")
        return ConversionResult(
            output_dir=str(output_dir),
            article_path=str(article_path),
            meta_path=str(meta_path),
            references_path=str(references_path),
            asset_count=0,
        )


def test_run_batch_continues_on_failure_and_skips_existing(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text(
        "\n".join(
            [
                "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                "https://en.wikipedia.org/wiki/Fei-Fei_Li",
            ]
        ),
        encoding="utf-8",
    )
    existing_dir = tmp_path / "output" / "person" / "default" / "fei-fei-li"
    existing_dir.mkdir(parents=True)

    result = run_batch(
        manifest_path=manifest,
        output_root=tmp_path / "output",
        service_factory=lambda: FakeService(tmp_path / "output"),
        config=BatchRunConfig(concurrency=2, overwrite=False, skip_invalid=False, max_retries=2),
    )

    statuses = {entry.url: entry.status for entry in result.entries if entry.url}
    assert statuses["https://en.wikipedia.org/wiki/Andrej_Karpathy"] == "success"
    assert statuses["https://en.wikipedia.org/wiki/Fei-Fei_Li"] == "skipped_existing"


def test_run_batch_retries_fetch_errors(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text("https://en.wikipedia.org/wiki/Andrej_Karpathy\n", encoding="utf-8")
    failures = {"https://en.wikipedia.org/wiki/Andrej_Karpathy": 2}

    result = run_batch(
        manifest_path=manifest,
        output_root=tmp_path / "output",
        service_factory=lambda: FakeService(tmp_path / "output", failures),
        config=BatchRunConfig(concurrency=1, overwrite=False, skip_invalid=False, max_retries=2),
    )

    assert result.entries[0].status == "success"


def test_run_batch_resume_avoids_rerunning_success_and_skipped_existing(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text(
        "\n".join(
            [
                "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                "https://en.wikipedia.org/wiki/Fei-Fei_Li",
            ]
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "output"
    state_path = output_root / ".wiki2md" / "batches" / "batch-123" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        BatchRunResult(
            batch_id="batch-123",
            manifest_path=str(manifest),
            output_root=str(output_root),
            config=BatchRunConfig(
                concurrency=1,
                overwrite=False,
                skip_invalid=False,
                max_retries=2,
            ),
            totals={"success": 1, "skipped_existing": 1},
            entries=[
                {
                    "entry_key": "https://en.wikipedia.org/wiki/Andrej_Karpathy|person/default/andrej-karpathy",
                    "url": "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                    "status": "success",
                    "relative_output_dir": "person/default/andrej-karpathy",
                },
                {
                    "entry_key": "https://en.wikipedia.org/wiki/Fei-Fei_Li|person/default/fei-fei-li",
                    "url": "https://en.wikipedia.org/wiki/Fei-Fei_Li",
                    "status": "skipped_existing",
                    "relative_output_dir": "person/default/fei-fei-li",
                },
            ],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    calls: dict[str, int] = {}

    result = run_batch(
        manifest_path=manifest,
        output_root=output_root,
        service_factory=lambda: FakeService(output_root, call_counts=calls),
        config=BatchRunConfig(
            concurrency=2,
            overwrite=False,
            skip_invalid=False,
            max_retries=2,
        ),
        resume_path=state_path,
    )

    assert calls == {}
    assert result.totals["success"] == 1
    assert result.totals["skipped_existing"] == 1


def test_run_batch_resume_drops_stale_entries_not_in_current_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "people.txt"
    manifest.write_text("https://en.wikipedia.org/wiki/Andrej_Karpathy\n", encoding="utf-8")
    output_root = tmp_path / "output"
    state_path = output_root / ".wiki2md" / "batches" / "batch-123" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        BatchRunResult(
            batch_id="batch-123",
            manifest_path=str(manifest),
            output_root=str(output_root),
            config=BatchRunConfig(
                concurrency=1,
                overwrite=False,
                skip_invalid=False,
                max_retries=2,
            ),
            totals={"success": 2},
            entries=[
                {
                    "entry_key": "https://en.wikipedia.org/wiki/Andrej_Karpathy|person/default/andrej-karpathy",
                    "url": "https://en.wikipedia.org/wiki/Andrej_Karpathy",
                    "status": "success",
                    "relative_output_dir": "person/default/andrej-karpathy",
                },
                {
                    "entry_key": "https://en.wikipedia.org/wiki/Fei-Fei_Li|person/default/fei-fei-li",
                    "url": "https://en.wikipedia.org/wiki/Fei-Fei_Li",
                    "status": "success",
                    "relative_output_dir": "person/default/fei-fei-li",
                },
            ],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    calls: dict[str, int] = {}

    result = run_batch(
        manifest_path=manifest,
        output_root=output_root,
        service_factory=lambda: FakeService(output_root, call_counts=calls),
        config=BatchRunConfig(
            concurrency=1,
            overwrite=False,
            skip_invalid=False,
            max_retries=2,
        ),
        resume_path=state_path,
    )

    assert calls == {}
    assert [entry.url for entry in result.entries if entry.status == "success"] == [
        "https://en.wikipedia.org/wiki/Andrej_Karpathy"
    ]
