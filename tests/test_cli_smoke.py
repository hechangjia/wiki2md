from typer.testing import CliRunner

from wiki2md.cli import app

runner = CliRunner()


def test_cli_help_shows_primary_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "convert" in result.stdout
    assert "inspect" in result.stdout
    assert "batch" in result.stdout


def test_convert_command_smoke_for_non_person_article(monkeypatch, tmp_path) -> None:
    class FakeService:
        def convert_url(self, url: str, overwrite: bool = False):
            output_dir = tmp_path / "people" / "linux"
            output_dir.mkdir(parents=True, exist_ok=True)
            article_path = output_dir / "article.md"
            article_path.write_text("# Linux\n", encoding="utf-8")
            return type("Result", (), {"article_path": str(article_path)})()

    monkeypatch.setattr("wiki2md.cli.build_service", lambda output_dir: FakeService())

    result = runner.invoke(
        app,
        ["convert", "https://en.wikipedia.org/wiki/Linux", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "article.md" in result.stdout
