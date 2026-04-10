# wiki2md Heavy Person Cleanup Design

Date: 2026-04-10
Status: Draft for review

## Context

`wiki2md` already converts standard Wikipedia person pages into:

- `article.md`
- `meta.json`
- `references.json`
- `infobox.json`
- `assets/`

Recent live testing on heavyweight pages such as `Elon_Musk` exposed a remaining quality gap. The output can still include page-level template noise that belongs to Wikipedia's navigation and framing system rather than the article body. Examples include:

- sidebar and series template link trees
- portal and succession boxes
- template control fragments such as `v`, `t`, `e`
- orphan blocks such as standalone dates emitted by template markup

The project goal is not to preserve the full rendered web page. The goal is to preserve the article body as clean, source-faithful corpus material.

## Problem Statement

Current normalization is still too permissive for heavyweight person pages with dense template usage. Some non-body blocks can leak into `Document.blocks`, where they are later rendered as ordinary prose or lists.

This creates two problems:

1. `article.md` becomes noisier and less useful for AI / RAG corpus consumption.
2. The output drifts away from "clean article body" toward "flattened page DOM".

## Goals

- Preserve actual article-body content from heavyweight person pages.
- Remove non-body template/navigation noise before it enters the document model.
- Improve `Elon_Musk`-class pages without introducing summary logic or rewriting content.
- Keep `External links`, `Further reading`, references, infoboxes, and body images working as they do now.

## Non-Goals

- Do not add new information.
- Do not summarize, rewrite, or interpret Wikipedia prose.
- Do not implement generic table extraction in this phase.
- Do not broaden this phase into a full semantic classifier for arbitrary page types.

## Cleaning Principle

Normalization should target the article body, not the full rendered page.

The core admission rule is:

> A block should be included only if it is part of the article's narrative body or a retained source-oriented appendix section.

This means:

- Keep:
  - lead summary paragraphs
  - article headings
  - article prose paragraphs
  - article lists that belong to the current section
  - infobox
  - body images and captions
  - references
  - `Further reading`
  - `External links`
- Drop:
  - sidebar boxes
  - series templates
  - succession boxes
  - portal boxes
  - navboxes
  - hatnotes and maintenance frames
  - template control fragments
  - obvious navigation-only link trees
  - orphan blocks that are emitted by template structure rather than article prose

## Recommended Approach

Use stricter block admission rules inside normalization.

The strategy is intentionally structural rather than semantic-heavy:

1. Filter at DOM-to-document time, not Markdown render time.
2. Exclude blocks nested inside tables by default.
3. Add lightweight noise heuristics for non-table blocks that are still clearly template residue.
4. Preserve section-aware link lists for `External links` and `Further reading`.

This approach is preferred over a large class-name blacklist because template classes vary widely across Wikipedia pages, while body-vs-template block behavior is more stable.

## Proposed Changes

### 1. Strengthen Block Admission

Normalization should continue to walk candidate nodes, but it should reject blocks that are structurally unlikely to be article body.

Baseline rule:

- Any candidate node nested inside a `table` is excluded from body extraction.

This already fixes one important leakage path for sidebar and related template families.

### 2. Add Lightweight Noise Filters

For candidate blocks that are not inside tables, apply conservative heuristics to reject obvious template residue.

Initial targets:

- standalone date-like paragraphs with no surrounding narrative context
- single-token or ultra-short template control fragments such as `v`, `t`, `e`
- short navigation-only list clusters that have the shape of template link trees rather than prose lists

These heuristics must stay conservative. If the block could plausibly be real article content, prefer keeping it.

### 3. Preserve Appendix-Style Source Sections

`External links` and `Further reading` remain explicitly preserved.

These sections are source-oriented appendices and are useful corpus material even though they are not narrative prose. Their current link-preserving behavior should remain intact.

### 4. Avoid Table Support in This Phase

The project still does not support generic table extraction.

Rather than partially extracting tables and then trying to distinguish good tables from bad ones, this phase keeps the contract simple:

- infobox is handled explicitly
- other tables are excluded from `Document.blocks`

## Data Flow Impact

The change belongs in normalization only.

Expected pipeline after this phase:

1. HTML fetched from Wikipedia
2. DOM cleaned of known noise selectors
3. Candidate blocks traversed
4. Stronger admission rules reject non-body blocks
5. Clean `Document` emitted
6. Existing renderers and writers run unchanged

This keeps the blast radius small and avoids output-format churn.

## Error Handling

This phase should not introduce new hard failures.

If a block cannot be confidently classified as template noise, it should be kept. The failure mode should be "slightly noisy output" rather than "missing real article content".

## Testing Strategy

Add focused regression coverage around heavyweight page noise:

1. Sidebar/template leakage
   - ensure sidebar lists inside tables do not enter `Document.blocks`
   - cover collapsed link-tree structures that previously looked like article lists

2. Orphan noise blocks
   - ensure standalone date-like fragments do not become ordinary paragraphs when they are clearly template residue
   - ensure template control fragments such as `v/t/e` do not survive as list items

3. Body protection
   - ensure genuine section headings, paragraphs, and body lists are preserved
   - ensure `External links` and `Further reading` still preserve URLs

4. Live regression
   - verify on `Elon_Musk`
   - confirm that the emitted article body no longer includes known template link soup

## Success Criteria

This phase is successful if:

- heavyweight person pages no longer emit obvious navigation/template noise into `article.md`
- `Elon_Musk` no longer includes the previously observed sidebar link tree
- normal person-page output remains stable
- all existing tests still pass

## Risks

The main risk is over-filtering and accidentally removing legitimate content.

Mitigation:

- keep heuristics conservative
- prefer structural filters over aggressive textual guessing
- add regression tests for preserved body content

## Out of Scope Follow-ups

Possible later work, but not part of this phase:

- more advanced detection for orphan date/template fragments
- generalized non-person article cleanup
- optional "strict corpus mode" with more aggressive cleaning rules
