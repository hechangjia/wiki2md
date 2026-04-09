# wiki2md Clean Article And References Design

## Goal

Refine `wiki2md` so the primary Markdown artifact is easier for AI systems to read while the structured reference sidecar becomes more useful for retrieval, provenance, and downstream curation.

This supplement extends the baseline v1 design in `docs/superpowers/specs/2026-04-08-wiki2md-design.md`. It does not replace the original spec.

## Scope

This enhancement includes two behaviors:

1. Make `article.md` cleaner by removing inline Wikipedia-style citation markers from prose blocks.
2. Strengthen `references.json` so each reference entry exposes better link structure and a best-effort primary source URL.

This enhancement does not add commands, change the top-level directory layout, or expand page-type support beyond the existing person-article scope.

## Output Contract

### article.md

- Keep the existing frontmatter, headings, body text, local image links, and compact `## References` summary.
- Preserve Markdown links in `Further reading` and `External links`.
- Remove inline Wikipedia-style citation markers such as `[8]`, `[109]`, and repeated adjacent citation groups from prose-oriented blocks.
- Apply citation-marker cleanup to:
  - summary paragraphs
  - body paragraphs
  - ordinary list items
- Do not add Markdown footnotes or sentence-level citation mapping in this iteration.

### references.json

Each reference entry should continue to expose the existing text payload, but become more structured:

```json
{
  "id": "cite_note-example-1",
  "text": "Reference text...",
  "primary_url": "https://example.com/source",
  "links": [
    {
      "text": "Example source",
      "href": "https://example.com/source",
      "kind": "external"
    }
  ]
}
```

Required fields:

- `id`: reference anchor id when available, otherwise `null`
- `text`: cleaned human-readable reference text
- `primary_url`: best-effort canonical source URL, otherwise `null`
- `links`: extracted reference links with classification

Each link object must contain:

- `text`
- `href`
- `kind`

## Link Classification

`references.json` link classification should use a small, explicit enum:

- `external`
- `wiki`
- `archive`
- `identifier`
- `other`

Classification rules are heuristic and deterministic:

- URLs pointing to archive services such as `archive.org`, `webcache`, or `wayback` are `archive`.
- URLs for identifier systems such as DOI, PMID, arXiv, OCLC, ISBN, ISSN, HDL, or ProQuest are `identifier`.
- Wikipedia or internal wiki-normalized links are `wiki`.
- Non-wiki external sites are `external`.
- Anything that does not fit the above buckets is `other`.

## Primary URL Selection

Each reference entry should expose one `primary_url` chosen from its extracted links.

Selection order:

1. First link classified as `external`
2. First link classified as `archive`
3. First link classified as `identifier`
4. Otherwise `null`

This is intentionally heuristic. It is acceptable for some references to select an imperfect primary URL as long as the full link set remains available in `links`.

## Cleaning Rules

Inline citation cleanup should be conservative.

- Remove bracketed markers that match the common Wikipedia citation shape, such as `[1]`, `[23]`, `[note 4]`, and repeated adjacent groups like `[9] [10]`.
- Preserve bracketed text that is likely genuine content rather than citation noise.
- Do not remove prose inside quotation marks or parenthetical content that happens to include brackets for other reasons.
- Keep reference cleanup independent from `references.json`; removing inline markers from `article.md` must not delete or weaken the structured reference sidecar.

## Architecture Changes

The existing pipeline remains intact. The enhancement should fit into current module boundaries:

- `normalize.py`
  - strengthen prose cleanup for inline citation markers
  - preserve external URLs in link-bearing list sections
  - enrich structured reference extraction
- `document.py`
  - support link-aware list items
  - support richer reference entries and link metadata
- `render_markdown.py`
  - render Markdown links for list items with preserved `href`
  - keep compact reference rendering in `article.md`
- `writer.py`
  - continue writing `article.md` and `meta.json`
  - write enhanced `references.json`
- `service.py`
  - pass enriched references through to the writer

## Testing

Required test coverage:

- normalization tests that show inline citation markers are removed from English and Chinese prose
- regression tests proving `External links` and `Further reading` still render as Markdown links
- writer/service tests proving `references.json` is emitted
- reference-structure tests proving `primary_url` and link `kind` are present
- live smoke verification on at least:
  - one English person article
  - one Chinese person article

## Non-Goals

This enhancement does not include:

- sentence-to-reference alignment
- Markdown footnotes
- dual clean/annotated Markdown outputs
- generalized support for list pages, disambiguation pages, or heavily tabular pages
- perfect classification of every possible citation source pattern

## Recommendation

Adopt a clean-first output strategy:

- `article.md` is optimized for readability and AI ingestion.
- `references.json` is the authoritative structured provenance sidecar.

This keeps the main artifact simple while preserving enough source detail for downstream indexing and curation.
