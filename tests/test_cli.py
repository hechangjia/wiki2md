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
    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService(output_dir))

    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(
        "# comment\nhttps://en.wikipedia.org/wiki/Andrej_Karpathy\n\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "batch",
            str(batch_file),
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    assert "Processed 1 URL(s)." in result.stdout
