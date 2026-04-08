import typer


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Convert Wikipedia articles into clean Markdown artifacts.",
)


@app.command()
def convert(url: str) -> None:
    """Convert a Wikipedia article URL into local Markdown artifacts."""
    typer.echo(f"convert not implemented yet: {url}")
    raise typer.Exit(code=1)


@app.command()
def inspect(url: str) -> None:
    """Inspect a Wikipedia article URL without writing files."""
    typer.echo(f"inspect not implemented yet: {url}")
    raise typer.Exit(code=1)


@app.command()
def batch(file: str) -> None:
    """Process a text file containing one Wikipedia URL per line."""
    typer.echo(f"batch not implemented yet: {file}")
    raise typer.Exit(code=1)
