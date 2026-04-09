import json
from pathlib import Path

import typer

from wiki2md.client import MediaWikiClient
from wiki2md.service import Wiki2MdService

DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_USER_AGENT = "wiki2md-bot/0.1 (2136414704@qq.com)"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Convert Wikipedia articles into clean Markdown artifacts.",
)


def build_service(output_dir: Path) -> Wiki2MdService:
    client = MediaWikiClient(user_agent=DEFAULT_USER_AGENT)
    return Wiki2MdService(client=client, output_root=output_dir)


def _close_service(service: object) -> None:
    client = getattr(service, "client", None)
    close = getattr(client, "close", None)
    if callable(close):
        close()


@app.command()
def convert(
    url: str,
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Convert a Wikipedia article URL into local Markdown artifacts."""
    service = build_service(output_dir)
    try:
        result = service.convert_url(url, overwrite=overwrite)
    finally:
        _close_service(service)
    typer.echo(result.article_path)


@app.command()
def inspect(
    url: str,
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
) -> None:
    """Inspect a Wikipedia article URL without writing files."""
    service = build_service(output_dir)
    try:
        result = service.inspect_url(url)
    finally:
        _close_service(service)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


@app.command()
def batch(
    file: Path,
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Process a text file containing one Wikipedia URL per line."""
    service = build_service(output_dir)
    processed = 0

    try:
        for raw_line in file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            service.convert_url(line, overwrite=overwrite)
            processed += 1
    finally:
        _close_service(service)

    typer.echo(f"Processed {processed} URL(s).")
