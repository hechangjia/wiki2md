import json
from pathlib import Path

import typer

from wiki2md.batch_models import BatchRunConfig
from wiki2md.batch_runtime import run_batch
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
    concurrency: int = typer.Option(4, "--concurrency"),
    resume: Path | None = typer.Option(None, "--resume"),
    skip_invalid: bool = typer.Option(False, "--skip-invalid"),
) -> None:
    """Process batch manifest files (txt/jsonl) via the batch runtime."""
    config = BatchRunConfig(
        concurrency=concurrency,
        overwrite=overwrite,
        skip_invalid=skip_invalid,
        max_retries=2,
    )
    result = run_batch(
        manifest_path=file,
        output_root=output_dir,
        service_factory=lambda: build_service(output_dir),
        config=config,
        resume_path=resume,
    )

    printable_statuses = {"success", "failed", "skipped_existing", "invalid", "duplicate"}
    for entry in result.entries:
        if entry.status not in printable_statuses:
            continue
        line = f"{entry.status.upper()} {entry.url}".rstrip()
        if entry.error:
            line = f"{line} | {entry.error}"
        typer.echo(line)

    typer.echo(f"Summary: {json.dumps(result.totals, ensure_ascii=False)}")
