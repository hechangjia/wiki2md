import json
from pathlib import Path

from typer.testing import CliRunner

from wiki2md.cli import app
from wiki2md.models import ConversionResult, InspectionResult, UrlResolution

runner = CliRunner()


class FakeService:
    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root

    def convert_url(self, url: str, overwrite: bool = False) -> ConversionResult:
        output_dir = self.output_root / "people" / "andrej-karpathy"
        output_dir.mkdir(parents=True, exist_ok=True)
        article_path = output_dir / "article.md"
        meta_path = output_dir / "meta.json"
        references_path = output_dir / "references.json"
        article_path.write_text("# Andrej Karpathy\n", encoding="utf-8")
        meta_path.write_text("{}", encoding="utf-8")
        references_path.write_text("[]", encoding="utf-8")
        return ConversionResult(
            output_dir=str(output_dir),
            article_path=str(article_path),
            meta_path=str(meta_path),
            references_path=str(references_path),
            asset_count=0,
        )

    def inspect_url(self, url: str) -> InspectionResult:
        return InspectionResult(
            resolution=UrlResolution(
                source_url=url,
                normalized_url=url,
                lang="en",
                title="Andrej_Karpathy",
                slug="andrej-karpathy",
            ),
            pageid=12345,
            revid=67890,
            media_count=2,
        )


def test_convert_command_prints_output_location(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))

    result = runner.invoke(
        app,
        [
            "convert",
            "https://en.wikipedia.org/wiki/Andrej_Karpathy",
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    assert "article.md" in result.stdout


def test_inspect_command_prints_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))

    result = runner.invoke(
        app,
        [
            "inspect",
            "https://en.wikipedia.org/wiki/Andrej_Karpathy",
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["media_count"] == 2


def test_batch_command_processes_non_empty_lines(monkeypatch, tmp_path: Path) -> None:
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(
        "# comment\nhttps://en.wikipedia.org/wiki/Andrej_Karpathy\n\n",
        encoding="utf-8",
    )
    resume_path = tmp_path / "output" / ".wiki2md" / "batches" / "resume" / "state.json"
    captured: dict[str, object] = {}

    def fake_run_batch(manifest_path, output_root, service_factory, config, resume_path=None):
        from wiki2md.batch_models import (
            BatchManifestEntry,
            BatchRunResult,
            BatchStateEntry,
        )

        captured["manifest_path"] = manifest_path
        captured["output_root"] = output_root
        captured["config"] = config
        captured["resume_path"] = resume_path
        service = service_factory()
        assert isinstance(service, FakeService)

        return BatchRunResult(
            batch_id="batch-123",
            manifest_path=str(manifest_path),
            output_root=str(output_root),
            config=config,
            totals={
                "success": 1,
                "failed": 1,
                "skipped_existing": 1,
                "invalid": 1,
                "duplicate": 1,
            },
            entries=[
                BatchStateEntry(
                    entry_key="success-1",
                    url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                    status="success",
                    manifest_entry=BatchManifestEntry(
                        url="https://en.wikipedia.org/wiki/Andrej_Karpathy"
                    ),
                    relative_output_dir="people/andrej-karpathy",
                ),
                BatchStateEntry(
                    entry_key="failed-1",
                    url="https://en.wikipedia.org/wiki/Fei-Fei_Li",
                    status="failed",
                    manifest_entry=BatchManifestEntry(
                        url="https://en.wikipedia.org/wiki/Fei-Fei_Li"
                    ),
                    error="Fetch failed",
                    relative_output_dir="people/fei-fei-li",
                ),
                BatchStateEntry(
                    entry_key="skipped-1",
                    url="https://en.wikipedia.org/wiki/Yann_LeCun",
                    status="skipped_existing",
                    manifest_entry=BatchManifestEntry(
                        url="https://en.wikipedia.org/wiki/Yann_LeCun"
                    ),
                    relative_output_dir="people/yann-lecun",
                ),
                BatchStateEntry(
                    entry_key="invalid-2",
                    url="",
                    status="invalid",
                    error="Invalid row",
                ),
                BatchStateEntry(
                    entry_key="duplicate-1",
                    url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                    status="duplicate",
                    manifest_entry=BatchManifestEntry(
                        url="https://en.wikipedia.org/wiki/Andrej_Karpathy"
                    ),
                    error="duplicate_url",
                ),
            ],
        )

    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))
    monkeypatch.setattr("wiki2md.cli.run_batch", fake_run_batch)

    result = runner.invoke(
        app,
        [
            "batch",
            str(batch_file),
            "--output-dir",
            str(tmp_path / "output"),
            "--overwrite",
            "--concurrency",
            "5",
            "--resume",
            str(resume_path),
            "--skip-invalid",
        ],
    )

    assert result.exit_code == 0
    assert captured["manifest_path"] == batch_file
    assert captured["output_root"] == tmp_path / "output"
    assert captured["resume_path"] == resume_path
    assert captured["config"].concurrency == 5
    assert captured["config"].overwrite is True
    assert captured["config"].skip_invalid is True
    assert captured["config"].max_retries == 2
    assert "SUCCESS https://en.wikipedia.org/wiki/Andrej_Karpathy" in result.stdout
    assert "FAILED https://en.wikipedia.org/wiki/Fei-Fei_Li" in result.stdout
    assert "SKIPPED_EXISTING https://en.wikipedia.org/wiki/Yann_LeCun" in result.stdout
    assert "INVALID" in result.stdout
    assert "DUPLICATE https://en.wikipedia.org/wiki/Andrej_Karpathy" in result.stdout
    summary_line = result.stdout.strip().splitlines()[-1]
    assert summary_line.startswith("Summary: ")
    totals = json.loads(summary_line.removeprefix("Summary: "))
    assert totals == {
        "success": 1,
        "failed": 1,
        "skipped_existing": 1,
        "invalid": 1,
        "duplicate": 1,
    }
