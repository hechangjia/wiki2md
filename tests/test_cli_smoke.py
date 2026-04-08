from typer.testing import CliRunner

from wiki2md.cli import app

runner = CliRunner()


def test_cli_help_shows_primary_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "convert" in result.stdout
    assert "inspect" in result.stdout
    assert "batch" in result.stdout
