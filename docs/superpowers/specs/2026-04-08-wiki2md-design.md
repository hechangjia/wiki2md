# wiki2md Design

Date: 2026-04-08
Status: Proposed
Project: `wiki2md`

## 1. Summary

`wiki2md` is a standalone Wikipedia data-cleaning project that converts high-quality Wikipedia articles into stable, local-first Markdown artifacts for AI workflows.

The first version targets a practical, repeatable workflow:

- The user provides a Wikipedia article URL.
- `wiki2md` fetches the article from Wikipedia's official APIs.
- The tool cleans page noise, preserves useful structure, downloads meaningful images locally, and writes a standard Markdown artifact plus metadata.

The project is designed as both:

- A command-line tool for direct daily use
- A Python library for reuse in notebooks, pipelines, and downstream tools

## 2. Goals

- Produce clean, stable Markdown from Wikipedia article URLs
- Prioritize English Wikipedia support and support Chinese Wikipedia in the first version
- Make person pages the first-class page type in v1
- Preserve useful evidence chains in the body while compressing noisy tail sections
- Store images locally and rewrite Markdown references to local relative paths
- Expose the functionality through both a CLI and a reusable Python package
- Establish a repo structure, output contract, and test strategy suitable for an open-source project

## 3. Non-Goals

- Supporting all Wikipedia page types in v1
- Using Firecrawl, Tavily, or generic web-search MCPs as the primary ingestion path
- Publishing directly into any note-taking system as a first-class output target
- Running LLM summarization, rewriting, or semantic enrichment in the core conversion path
- Solving remote image hosting in v1

## 4. Scope

### In Scope for v1

- Input: direct Wikipedia article URLs
- Languages: English first, Chinese supported
- Page type focus: person pages
- Output artifacts:
  - `article.md`
  - `meta.json`
  - local `assets/` directory for images
- CLI commands for conversion, inspection, and batch processing
- Python package API for programmatic reuse
- Deterministic cleanup rules for common Wikipedia page noise

### Out of Scope for v1

- Disambiguation pages
- List pages
- Category pages
- Talk, Help, Special, and search pages
- Complex non-person articles as a quality target, though the architecture should allow future expansion

## 5. Product Shape

The project will be packaged as a Python package named `wiki2md`.

It will contain two layers:

- `core library`
  - URL parsing and validation
  - Wikipedia fetching
  - normalization into an internal document model
  - Markdown rendering
  - artifact writing
- `CLI`
  - direct user-facing commands for day-to-day use

Recommended Python stack:

- `httpx` for HTTP requests
- `pydantic` for structured data models
- `beautifulsoup4` or `selectolax` for HTML parsing and cleanup
- a small custom rendering layer for deterministic Markdown output
- `typer` for the CLI
- `pytest` for tests

## 6. Source Strategy

The primary data source should be Wikipedia's own MediaWiki REST API on each language site:

- `https://<lang>.wikipedia.org/w/rest.php/v1/...`

The project should not depend on the Wikimedia Core REST API hosted under `api.wikimedia.org/core/v1` because Wikimedia has announced deprecation for that surface beginning in July 2026. The project should also avoid using third-party crawlers as the core source for Wikipedia articles when official article APIs are available.

Recommended fetch strategy:

- Resolve and validate the input URL
- Fetch page metadata from `/w/rest.php/v1/page/{title}/bare`
- Fetch rendered article HTML from `/w/rest.php/v1/page/{title}/html`
- Fetch linked media from `/w/rest.php/v1/page/{title}/links/media`
- Fetch selected file details from `/w/rest.php/v1/file/{title}` when downloading kept images

Raw wikitext endpoints such as `/w/rest.php/v1/page/{title}` or `?action=raw` may be used only as fallback diagnostics or future debugging aids, not as the primary conversion input.

## 7. Architecture

The conversion pipeline should be split into five explicit stages.

### 7.1 URL Resolver

Responsibilities:

- Accept a Wikipedia URL
- Extract language and title
- Normalize canonical article identity
- Reject unsupported page namespaces and obvious unsupported page types

Expected behavior:

- Accept standard article URLs from supported languages
- Reject unsupported namespaces with clear errors
- Flag likely disambiguation or list pages before conversion

### 7.2 Fetcher

Responsibilities:

- Request page metadata and rendered HTML from Wikipedia
- Request media metadata
- Apply timeout, retry, and user-agent policy consistently

Expected behavior:

- Use a recognizable `User-Agent`
- Support configurable timeouts and bounded retries
- Surface structured fetch errors instead of generic failures

### 7.3 Normalizer

Responsibilities:

- Convert raw HTML into an internal, stable document model
- Remove site-specific noise and UI fragments
- Preserve useful structure for Markdown rendering

Recommended internal model types:

- `Document`
- `Section`
- `Paragraph`
- `ListBlock`
- `QuoteBlock`
- `ImageBlock`
- `TableBlock`
- `CitationMarker`

Keep:

- page title
- lead summary
- body sections
- paragraphs
- lists
- useful quotes
- meaningful images
- limited citation markers
- simple, information-bearing tables where feasible

Remove:

- navigation boxes
- edit links
- page chrome
- coordinate widgets
- audio icons
- decorative icons
- template leftovers that do not carry article meaning
- language UI fragments
- other obvious site noise

### 7.4 Markdown Renderer

Responsibilities:

- Render the normalized document model into deterministic Markdown
- Apply stable heading and list conventions
- Rewrite kept image references to local relative paths
- Compress long reference sections while preserving useful traceability

Output qualities:

- predictable heading levels
- readable paragraphs and lists
- local image paths
- stable formatting suitable for version control and AI ingestion

### 7.5 Artifact Writer

Responsibilities:

- Write the final output directory
- persist Markdown, metadata, and assets
- avoid partial output on failure

Expected behavior:

- write to a temporary location first
- move into final place only on successful completion
- support overwrite or skip behavior for existing targets

## 8. Output Contract

Each converted article should be written into its own directory.

Recommended layout:

```text
output/
  people/
    andrej-karpathy/
      article.md
      meta.json
      assets/
        001-infobox.jpg
        002-body-image.png
```

Directory naming rules:

- Generate a slug from the canonical article title
- Use a stable kebab-case representation
- If collisions occur, disambiguate using language or page identifier

### 8.1 `article.md`

Purpose:

- primary artifact for humans and AI systems

Recommended structure:

- YAML frontmatter
- article title
- lead summary
- cleaned body content
- compressed reference material when retained

Recommended frontmatter fields:

```yaml
title: Andrej Karpathy
source_url: https://en.wikipedia.org/wiki/Andrej_Karpathy
source_lang: en
source_type: wikipedia
retrieved_at: 2026-04-08T00:00:00Z
page_type: person
pageid: 12345
revid: 67890
```

Markdown rules:

- Keep links as normal Markdown links
- Use local relative paths for assets
- Do not emit note-system-specific link syntax in the core output

### 8.2 `meta.json`

Purpose:

- preserve provenance and conversion details

Required fields:

- source URL
- canonical title
- language
- page type
- page identifier and revision identifier when available
- retrieval timestamp
- image manifest
- cleanup statistics
- warnings raised during conversion

### 8.3 `assets/`

Purpose:

- store meaningful local images used by the Markdown output

Rules:

- keep original file format when practical
- use deterministic filenames
- skip decorative or low-information images

## 9. Citation, Reference, and Link Policy

The project should preserve evidence without copying Wikipedia's noisiest tail sections verbatim.

Policy for v1:

- Keep citation cues in the body where practical
- Keep useful external links when they are part of the article content
- Compress or simplify large reference blocks instead of dumping the full noisy section unchanged
- Preserve enough provenance so a downstream reader can trace the source article reliably

The first version should prefer a readable, low-noise output over a fully lossless archive of every footnote structure.

## 10. Image Policy

The project should download kept images locally by default.

Priority order:

- infobox portrait or lead image
- meaningful in-body images

Images to exclude when possible:

- decorative icons
- UI symbols
- audio indicators
- tiny template fragments
- obvious non-content assets

Remote hosting is a future extension. The v1 storage backend is local filesystem output only.

## 11. CLI Design

The CLI should expose at least these commands:

```bash
wiki2md convert <url>
wiki2md inspect <url>
wiki2md batch <file>
```

Command purposes:

- `convert`
  - fetch, clean, render, and write artifacts
- `inspect`
  - validate and inspect the page without writing output
- `batch`
  - process a list of URLs from a file

The CLI should provide:

- clear success and failure messages
- meaningful exit codes
- flags for output directory and overwrite behavior
- a predictable default output path inside the project workspace

## 12. Python API Shape

The package should expose a programmatic API that mirrors the core conversion flow.

A minimal design target:

- one high-level conversion function for direct use
- lower-level typed components for advanced users

Example conceptual API:

```python
from wiki2md import convert_url

result = convert_url(
    "https://en.wikipedia.org/wiki/Andrej_Karpathy",
    output_dir="output",
)
```

The exact method names can change during implementation, but the package should make both simple and advanced usage possible.

## 13. Error Handling

Errors should be explicit and typed, not collapsed into generic failures.

Four categories should be handled distinctly:

### 13.1 Input Errors

Examples:

- invalid URL
- unsupported language
- unsupported namespace
- unsupported page type

Behavior:

- fail fast
- print a clear message in the CLI
- return a non-zero exit code

### 13.2 Fetch Errors

Examples:

- timeout
- rate limiting
- page not found
- upstream API errors

Behavior:

- use bounded retry logic where appropriate
- expose request context in error details
- keep failures understandable for CLI users and library consumers

### 13.3 Parse Errors

Examples:

- unexpected HTML structure
- missing image metadata
- section-level conversion failures

Behavior:

- degrade gracefully when only a section or asset fails
- keep the main article output when possible
- record warnings in metadata

### 13.4 Write Errors

Examples:

- filesystem permissions
- path collisions
- interrupted writes

Behavior:

- avoid half-written final directories
- support explicit overwrite or skip modes

## 14. Testing Strategy

The testing strategy should focus on output stability against real Wikipedia content.

### 14.1 Unit Tests

Cover:

- URL parsing
- slug generation
- frontmatter generation
- image naming
- citation compression
- output path rules

### 14.2 Fixture Tests

Store small, representative response fixtures covering:

- English person page
- Chinese person page
- page with infobox
- page with multiple useful images
- page with long references

Assert:

- key section structure
- title and lead presence
- image link rewriting
- reference compression behavior

### 14.3 End-to-End Smoke Tests

Run the CLI on controlled fixtures or stable snapshots and verify:

- output directory creation
- presence of `article.md`, `meta.json`, and `assets/`
- existence of expected article headings and selected assets

Recommended initial golden pages:

- Andrej Karpathy
- Fei-Fei Li
- Alan Turing
- Elon Musk
- one Chinese person article

## 15. Documentation and Open-Source Readiness

The repository should be structured so that a new user can understand and run the project quickly.

Recommended repo elements:

- `README.md` with a short explanation and before/after examples
- `docs/` for architecture, output format, and known limitations
- `examples/` with sample outputs
- `tests/` with fixtures and smoke tests
- `pyproject.toml` for packaging and CLI entry points
- `CHANGELOG.md`
- `LICENSE`
- CI workflow for lint, test, and build checks

Project quality bar:

- reliable output on common person pages
- understandable failure modes
- deterministic artifacts
- clear installation and usage instructions

## 16. Future Extensions

The architecture should allow later additions without changing the v1 artifact contract.

Planned extension areas:

- support for more page types beyond person pages
- pluggable asset storage backends such as GitHub or external image hosting
- discovery and enrichment commands
- optional integrations with Firecrawl, Tavily, or web-search MCPs for non-core tasks
- batch workflows with richer reporting

## 17. Decision Summary

Final design decisions for this project:

- Project name: `wiki2md`
- Package language: Python
- Product shape: CLI plus reusable Python library
- Input: direct Wikipedia article URLs
- Language support: English first, Chinese supported in v1
- Page focus: person pages first
- Source strategy: official MediaWiki REST API per language site
- Output strategy: `article.md` plus `meta.json` plus local `assets/`
- Citation policy: preserve body traceability, compress noisy tail references
- Image policy: store useful images locally by default
- Third-party crawlers and search tools: future extensions, not core dependencies
