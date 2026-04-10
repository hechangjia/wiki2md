# wiki2md Discovery Generator Design

Date: 2026-04-10
Status: Draft for review

## Context

`wiki2md` already has a stable conversion and batch-ingestion pipeline:

- single-page conversion
- batch ingestion from `txt` and `jsonl`
- structured article bundles under `output/people/<slug>/`

What it does not yet have is a strong discovery layer. Building a person corpus still depends too much on:

- the user's pre-existing knowledge of notable people
- small hand-curated starter manifests
- ad hoc recall of modern famous names

This is a poor fit for the actual corpus-building goal. A good corpus should be discoverable from stable, high-signal entry points such as:

- award pages
- list pages
- institution-centric people pages

Examples include:

- Turing Award
- Fields Medal
- Nobel Prize in Physics

These pages provide a better entry point than memory because they are:

- stable
- thematically coherent
- naturally expandable
- rich in historical figures the user may not already know

## Goal

This phase adds a discovery generator that can turn a Wikipedia entry page into a reusable person manifest.

The intended workflow is:

1. start from an entry page URL or a built-in preset
2. discover candidate people from that source page and a small bounded expansion
3. emit a reviewable manifest plus discovery sidecars
4. feed the manifest into the existing `wiki2md batch` pipeline

The output should help both:

- human browsing and curation
- programmatic corpus generation

## Non-Goals

- Do not replace the existing `batch <file>` ingestion workflow
- Do not build an unbounded crawler
- Do not add complex NLP-based person recognition
- Do not guarantee exhaustive historical coverage for any award or topic
- Do not change article conversion semantics in this phase
- Do not redesign the core person manifest schema

## Recommended CLI Surface

Add a discovery-oriented subcommand under the batch namespace:

```bash
wiki2md batch discover <url-or-preset> --output-dir output
```

This keeps the user model coherent:

- `batch <file>` consumes a manifest
- `batch discover <source>` produces a manifest

This is preferred over overloading `batch <input> --discover` because it keeps the existing stable contract intact and gives discovery its own explicit execution mode.

## Input Model

The discovery command should accept either:

- a Wikipedia entry page URL
- a built-in preset name

### Supported Source Types

First-version discovery should prioritize:

- award pages
- list pages
- institution-centric people index pages

### Built-In Presets

The initial built-in presets should be intentionally small and high-signal:

- `turing-award`
- `fields-medal`
- `nobel-physics`

Presets should not hide opaque logic. Each preset is simply:

- a stable entry page URL
- default tags
- a default `output_group`

## Output Contract

Discovery output should live under:

```text
output/discovery/<slug>/
```

For example:

```text
output/
  discovery/
    turing-award/
      manifest.jsonl
      index.md
      discovery.json
```

This directory must contain three artifacts:

### `manifest.jsonl`

This is the practical handoff artifact for the existing batch pipeline.

Each line should use the existing person manifest shape:

```json
{"url":"https://en.wikipedia.org/wiki/Geoffrey_Hinton","page_type":"person","slug":"geoffrey-hinton","tags":["award","computer-science","turing-award"],"output_group":"turing-award"}
```

The row should remain intentionally compact:

- `url`
- `page_type`
- `slug`
- `tags`
- `output_group`

### `index.md`

This is the human-readable review surface.

It should include:

- source page title
- source page URL
- source language
- discovered count
- the selected candidate list
- a short note about how each person was discovered
- the next recommended batch command

### `discovery.json`

This is the authoritative machine-readable provenance record.

It should preserve information that does not belong in the batch manifest, including:

- `source_url`
- `source_title`
- `source_lang`
- `discovery_method`
- `expanded_pages`
- configured limits
- candidate scoring and selection metadata
- per-candidate provenance such as:
  - `anchor_text`
  - `source_page`
  - `depth`
  - `score`
  - `selection_reason`
  - `rejected_reason` when applicable

## Discovery Strategy

The first version should use bounded two-layer discovery.

### Depth 0

Parse the entry page itself and collect candidate person links from:

- prose blocks
- list items
- tables

Depth 0 candidates are highest priority because they are closest to the source topic.

### Depth 1

From the entry page, expand into a small number of representative secondary pages and collect additional candidates.

Examples:

- award recipient lists
- year-grouped or era-grouped lists
- related institution or laureate pages linked from the source page

Depth 1 exists to improve recall for historically important people the user may not know already.

### Recursion Limit

Discovery stops at `Depth 1`.

This is deliberate. The goal is a useful, bounded manifest generator, not a crawler.

## Candidate Collection Rules

The parser should be broad in what it accepts, but not unbounded.

### Prefer To Collect

- direct Wikipedia article links that appear to point to people
- candidates in prose, list items, and tables
- candidates from list-style entry pages and award pages

### Always Exclude

- `Category:`
- `Help:`
- `Special:`
- `Talk:`
- same-page fragment links
- navigation template control links
- obvious site UI links
- non-article destinations

## Person Selection Rules

The first version should prioritize coverage without losing topical relevance.

### Hard Cap

Select at most `37` final people.

### Ordering Rule

When more than `37` valid candidates are available:

1. keep direct `Depth 0` person links first
2. fill remaining slots with `Depth 1` candidates ranked by:
   - appearance frequency
   - closeness to the original source page

### Recognition Heuristics

Do not introduce heavy NLP in this phase.

Use lightweight heuristics instead:

- target must be a Wikipedia article URL
- title or anchor text should plausibly look like a person name
- lightweight page confirmation may use categories, summaries, or other existing page metadata

Candidates that are ambiguous or low-confidence may remain in `discovery.json` without being promoted into `manifest.jsonl`.

## Metadata Defaults

Discovery should derive practical corpus metadata automatically from the source page.

### `page_type`

- always `person` in this phase

### `tags`

Tags should be auto-derived from the source page title or preset.

Examples:

- `["award", "computer-science", "turing-award"]`
- `["award", "mathematics", "fields-medal"]`

### `output_group`

`output_group` should also be auto-derived from the source page title or preset.

Examples:

- `turing-award`
- `fields-medal`
- `nobel-physics`

This is preferred over requiring manual overrides for the first version because discovery should feel like a fast indexing tool, not another data-entry step.

## Language Strategy

The first version should prioritize English entry pages and try to support Chinese entry pages where practical.

Guiding rule:

- English first
- Chinese second, best effort

When the source page is Chinese:

- prefer a stable canonical article URL if it can be resolved cleanly
- otherwise preserve the original language article URL

## Integration With Existing Batch Workflow

Discovery should plug directly into the existing batch runtime.

Recommended flow:

```bash
wiki2md batch discover turing-award --output-dir output
wiki2md batch output/discovery/turing-award/manifest.jsonl --output-dir output
```

`index.md` should include this recommended next-step command so the output directory is partly self-documenting.

## Testing Strategy

Add four classes of tests.

### 1. Discovery Model Tests

Cover:

- preset resolution
- URL source resolution
- hard cap of `37`
- direct-link priority over expanded links
- automatic `tags` and `output_group` derivation

### 2. Extraction Tests

Cover:

- award pages
- list pages
- institution pages
- exclusion of `Category:` / `Special:` / `Talk:` / fragments / template controls

### 3. Ranking And Filtering Tests

Cover:

- `Depth 0` preference over `Depth 1`
- frequency-based fill behavior
- ambiguous or non-person candidates staying out of `manifest.jsonl`

### 4. CLI Smoke Tests

Cover:

- `wiki2md batch discover <preset>`
- generation of `manifest.jsonl`, `index.md`, and `discovery.json`
- successful handoff into the existing `wiki2md batch` command

## Success Criteria

This phase is successful if:

- `turing-award`, `fields-medal`, and `nobel-physics` all generate stable discovery outputs
- discovery output is capped at `<= 37` selected people
- `manifest.jsonl` is immediately consumable by the existing batch pipeline
- `index.md` is readable enough for manual curation
- `discovery.json` preserves enough provenance for future refinement
- the user no longer needs to rely mostly on personal recall of notable people to build a corpus seed list

## Why This Is Better Than Only Adding More Handwritten Manifests

Handwritten manifests are useful, but they do not scale well as a discovery strategy.

The discovery generator is the more valuable next layer because it creates a reusable indexing workflow:

- start from a stable source page
- derive a candidate set
- review the result
- batch-ingest the selected people

Once this exists, the project can expand far beyond the first three presets without requiring repeated manual curation for every new domain.
