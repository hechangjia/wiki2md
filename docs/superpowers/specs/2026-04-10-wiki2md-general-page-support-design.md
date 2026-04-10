# wiki2md General Page Support Design

Date: 2026-04-10
Status: Draft for review

## Context

`wiki2md` has grown from a person-focused Wikipedia bundle generator into a more general conversion tool:

- single-page conversion is stable
- batch ingestion is stable
- discovery exists and can generate manifests from award or index pages
- sidecars such as `meta.json`, `references.json`, `infobox.json`, `section_evidence.json`, and `sources.md` already exist

At the same time, the project accumulated a person-first bias:

- standard non-person pages can often convert successfully, but the semantics are still person-oriented
- some output assumptions belong more naturally in metadata than in `article.md`
- earlier design choices drifted toward RAG-oriented enhancement instead of a faithful, standardized Wikipedia projection

This phase resets the product direction.

`wiki2md` should primarily be understood as:

- a general Wikipedia-to-Markdown conversion tool
- focused on clean, structured, machine-readable output
- not a tool that pre-optimizes article text for a particular downstream AI workflow

The user can decide how to use the resulting Markdown and metadata for AI, RAG, indexing, or archival workflows afterward.

## Goal

Expand `wiki2md` from person-first conversion into broad support for common Wikipedia page types while keeping the output contract simple and stable.

The core target is:

- most common Wikipedia article pages should convert cleanly
- non-person pages should no longer obviously inherit person-only semantics
- `article.md` should remain a faithful cleaned article projection
- metadata and sidecars should carry structured classification and evidence
- discovery should remain available as a powerful auxiliary workflow, not the defining identity of the converter

## Non-Goals

- Do not redesign the repository around page-type-specific products
- Do not aggressively rewrite or summarize Wikipedia prose
- Do not add new RAG-specific blocks into `article.md`
- Do not turn discovery into a crawler or the primary entry point for all usage
- Do not require perfect page-type classification before conversion can succeed
- Do not break the current stable bundle shape unless there is a strong compatibility reason

## Product Direction

This phase makes three product-level choices explicit.

### 1. `article.md` stays pure

`article.md` should be the clean article artifact, not a speculative downstream format.

That means:

- preserve Wikipedia information structure as much as possible
- normalize formatting and remove obvious site/template noise
- avoid injecting new explanatory or derived content blocks
- keep structured classification in sidecars rather than in the article body

### 2. Metadata carries classification

`meta.json` remains the proper place for:

- `page_type`
- source and revision metadata
- warnings
- cleanup and extraction signals
- future page-shape or confidence fields

This lets the article stay simple while still supporting programmatic downstream use.

### 3. Discovery is auxiliary

Discovery remains valuable for building a people corpus from strong Wikipedia indexes such as:

- awards
- institutions
- universities
- list pages

But discovery does not define what `wiki2md` is.

The core product remains conversion.

## Scope

This phase should raise support quality for the following page shapes:

- standard biography pages
- standard concept or topic pages
- company and organization pages
- technology or software pages
- institution pages
- award pages
- list-like and timeline-like pages when they are common and informative

Support targets should be understood as:

- standard article pages: higher-quality target
- list and nav-heavy pages: best-effort target

The system should prefer producing a usable bundle with warnings over rejecting a page unless conversion is clearly impossible.

## Output Contract

The bundle shape should remain stable.

Primary output continues to be:

```text
output/people/<slug>/
  article.md
  meta.json
  references.json
  assets/
```

Additional sidecars may continue to exist when available, such as:

- `infobox.json`
- `section_evidence.json`
- `sources.md`

This phase does not require changing the directory root from `people/`. The path can remain stable while `meta.json` becomes more semantically accurate for non-person pages.

### `article.md`

`article.md` should:

- keep the article as the center
- preserve headings, paragraphs, lists, tables, and images when meaningful
- avoid person-only assumptions for non-person pages
- stop short of becoming a derived knowledge card

### `meta.json`

`meta.json` should become the authoritative place for semantic interpretation, including:

- resolved `page_type`
- extraction warnings
- cleanup signals
- future support-level or confidence fields

## Recommended Technical Approach

Upgrade the current normalizer from a person-heavy extractor into a more general block-based content extractor.

The intent is not to create a separate parser for every page type. It is to make the core extractor broad enough that common page structures can pass through with minimal page-specific branching.

### Block Model

The normalizer should primarily reason in terms of reusable content blocks such as:

- heading
- paragraph
- list
- table
- image
- quote

This is a better long-term model than a biography-first structure because:

- biographies, concept pages, organization pages, and award pages all reuse these blocks
- list and timeline pages can often be represented as combinations of headings, lists, and tables
- page-specific behavior can stay narrow and mostly metadata-oriented

### Page-Type Semantics

The system should still infer page shape where practical, but page type should not be the main driver of extraction behavior.

That means:

- extraction should mostly be content-structure-first
- page classification should mainly inform metadata and small rendering choices
- successful conversion should not depend on a rigid early page-type fork

## Cleaning Boundaries

The cleaning rule should be conservative:

- preserve information structure
- delete only obvious non-content
- do not delete material merely because it is not prose-like

### Always Remove

These are safe to treat as non-content noise:

- edit controls
- `v/t/e` template controls
- site chrome
- language UI
- navigation-only boxes
- footer templates
- obvious sidebar or navbox noise
- purely decorative template fragments

### Preserve When Informative

These should generally stay if they contain real information:

- infobox content
- long but meaningful tables
- award or recipient tables
- member or officeholder lists
- chronology blocks
- timeline-like sections
- images and captions
- references and citation traces where already supported

### Best-Effort Cases

For complex pages such as:

- long list pages
- timeline pages
- award-history pages
- navigation-heavy institutional pages

the target is:

- keep usable article structure
- remove obvious chrome
- allow warnings instead of failing the whole conversion

## Discovery Positioning

Discovery remains part of the project, but as a secondary workflow.

Its role is:

- help users discover noteworthy people from strong Wikipedia indexes
- generate manifests from awards, institutions, universities, and related entry pages
- accelerate corpus expansion without making the user guess names from memory

Its role is not:

- to define the article output contract
- to make the project person-only again
- to replace direct URL conversion as the primary user path

In practice:

- `convert` remains the center of the product
- `batch` remains the scale workflow
- `batch discover` remains a corpus-building helper

## Success Criteria

This phase is successful if the following become true:

1. Common non-person Wikipedia pages convert more stably than before.
2. Non-person pages no longer obviously inherit person-only semantics in the bundle.
3. `article.md` becomes more clearly a clean article projection instead of a downstream AI-optimized derivative.
4. Metadata becomes the main home for classification and extraction interpretation.
5. Discovery remains useful and can continue evolving independently without redefining the converter.
6. The project moves closer to a finished, general-purpose Wikipedia conversion tool.

## Deferred Work

This phase intentionally does not fully solve:

- exhaustive page-type taxonomy
- perfect classification of every Wikipedia page
- custom rendering strategies for every special page family
- advanced discovery ranking for every domain
- downstream chunking or embedding export formats

Those can come later after the general conversion contract is cleaner and more stable.
