# wiki2md

Turn Wikipedia person pages into RAG-ready local corpus artifacts with clean Markdown, structured sidecars, and local assets.

`wiki2md` converts noisy article pages into deterministic local files that are easy for people, embeddings pipelines, and retrieval systems to consume.

## Why It Works For RAG

- Clean-first prose optimized for reading and chunking
- Sidecar JSON artifacts keep metadata and provenance structured
- Local `assets/` paths avoid remote fetch drift during indexing
- Resumable batch processing supports long-running corpus builds

## Scope

- English-first Wikipedia support with Chinese article compatibility
- Person article URLs as the v1 target
- Local `article.md`, `meta.json`, `references.json`, `infobox.json`, and `assets/` output
- MediaWiki REST API as the primary data source

## Quickstart

```bash
uv sync --extra dev
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
```

## Commands

```bash
wiki2md convert <url>
wiki2md inspect <url>
wiki2md batch <file>
```

`inspect` prints JSON metadata without writing files:

```bash
uv run wiki2md inspect "https://en.wikipedia.org/wiki/Andrej_Karpathy"
```

## Single-Page Example

Repository example:
- `examples/andrej-karpathy/`

Representative runtime output:

```text
output/
  people/
    andrej-karpathy/
      article.md
      meta.json
      references.json
      infobox.json
      assets/
```

The checked-in example focuses on the text sidecars (`article.md`, `meta.json`, `references.json`, `infobox.json`). Binary `assets/` are part of normal runtime output but are not committed to the repository example.

Excerpt from `examples/andrej-karpathy/article.md`:

```markdown
# Andrej Karpathy

## Profile

Andrej Karpathy is a computer scientist.
```

## Output Contract

- `article.md`: the clean-first reading artifact for people and AI
- `meta.json`: run metadata and article-level context
- `references.json`: structured provenance and source trail
- `infobox.json`: machine-readable person facts
- `assets/`: local images referenced by the article

Contract notes:
- `article.md` is clean-first prose with no inline Wikipedia citation markers (for example, no `[8]` markers embedded in paragraph text).
- `article.md` renders a readable `## Profile` section when infobox fields are available for the person page.
- `infobox.json` stores the machine-readable infobox data, including the selected image metadata and field list.
- `references.json` is a provenance sidecar where each reference includes a best-effort `primary_url` (it may be null when no suitable source URL is available), and each link entry includes a classified `kind` (`external`, `wiki`, `archive`, `identifier`, or `other`).

## Batch Workflow

`batch` supports both plain `txt` URL lists and structured `jsonl` manifests.

`txt` mode reads one URL per non-empty line and ignores `#` comments:

```bash
uv run wiki2md batch urls.txt --output-dir output
```

`jsonl` mode supports per-row metadata (`page_type`, `slug`, `tags`, `output_group`):

```bash
uv run wiki2md batch examples/batch/person-manifest.jsonl --output-dir output
```

Example `jsonl` row:

```json
{"url":"https://en.wikipedia.org/wiki/Andrej_Karpathy","page_type":"person","slug":"andrej-karpathy","tags":["ai","person"],"output_group":"people-ai"}
```

Useful flags:
- `--output-dir`: choose output root (default `output`)
- `--overwrite`: re-run even when target output exists
- `--concurrency`: set worker count (default `4`)
- `--skip-invalid`: skip bad manifest rows instead of failing strict validation
- `--resume`: resume from an explicit state file

Resume usage:

```bash
uv run wiki2md batch examples/batch/person-manifest.jsonl \
  --output-dir output \
  --resume output/.wiki2md/batches/<batch-id>/state.json
```

Batch artifacts are written under `output/.wiki2md/batches/`:
- `state.json`: resumable execution state
- `batch-report.json`: full run summary and per-entry outcomes
- `failed.txt`: failed URLs for quick review
- `failed.jsonl`: failed manifest rows (preferred retry input)
- `invalid.jsonl`: invalid manifest rows (only when invalid rows exist)

Retry failed rows directly:

```bash
uv run wiki2md batch output/.wiki2md/batches/<batch-id>/failed.jsonl --output-dir output
```

## Examples

- `examples/andrej-karpathy/`
- `examples/batch/person-manifest.jsonl`
