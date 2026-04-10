# wiki2md Path Unification and Award Manifest Design

Date: 2026-04-10
Status: Draft for review

## Context

`wiki2md` currently has two conflicting default output path contracts:

- single-page `convert` writes to `output/people/<slug>/`
- batch `batch` writes to `output/person/<output_group>/<slug>/`

Both produce valid article bundles, but the mismatch creates practical corpus-management problems:

- the same person can be saved twice under different directory trees
- single-page testing and batch corpus building do not compose cleanly
- path-based deduplication becomes harder than necessary
- README examples and runtime behavior are no longer aligned

At the same time, the project would benefit from a stronger starter indexing story. Rather than relying on ad hoc recall of famous people, the first curated manifests should start from high-signal award ecosystems such as:

- Turing Award
- Fields Medal
- Nobel Prize in Physics

These lists are better corpus seeds because they are stable, prestigious, and naturally expand into related institutions, collaborators, and eras.

## Goal

This phase has two linked goals:

1. unify `wiki2md` on one stable default output path contract
2. add curated starter manifests that help users build high-quality person corpora from award-centered entry points

The intended outcome is a cleaner operational model:

- every person bundle lives under one canonical directory shape
- batch metadata still survives in sidecars
- users have ready-to-run manifests that do not depend on personal memory of notable people

## Non-Goals

- Do not redesign batch manifest schema
- Do not add new page types beyond `person`
- Do not add automatic web discovery of list pages or laureate lists
- Do not build a generic migration command in this phase
- Do not change article content extraction behavior beyond path-related metadata threading

## Recommended Path Contract

The project should standardize on:

```text
output/people/<slug>/
```

This should be the canonical directory for both:

- `wiki2md convert <url>`
- `wiki2md batch <txt|jsonl>`

`output_group` should remain part of metadata, but it should no longer participate in the physical directory shape.

This design is preferred over keeping batch-only grouping in the filesystem because the corpus should prioritize one canonical location per person over folder-level topical clustering.

## Why `people/<slug>` Is The Better Default

Compared with `person/default/<slug>`:

- it is shorter and easier to inspect manually
- it matches the existing single-page mental model the user already expects
- it reduces redundant path semantics
- it avoids teaching users that `default` is an important corpus concept when it is really just batch metadata

Compared with `people/<output_group>/<slug>`:

- it avoids the same person appearing in multiple directories just because they were included in multiple thematic runs
- it keeps stable paths even when tagging or grouping strategies change later

The canonical identity of a person bundle should be the slug, not the batch grouping.

## Directory Compatibility And Automatic Migration

This phase should include conservative automatic migration from legacy batch paths.

### Legacy Paths

Legacy batch outputs currently live under:

```text
output/person/<output_group>/<slug>/
```

### Migration Rule

When converting or batching a page whose canonical target is `output/people/<slug>/`:

- if `output/people/<slug>/` already exists, use it directly
- else if exactly one legacy directory exists that matches `output/person/*/<slug>/`, move that directory to `output/people/<slug>/`
- else if multiple legacy directories exist for the same slug, do not auto-migrate and raise a clear error
- else create a fresh `output/people/<slug>/`

This keeps the migration behavior safe:

- simple legacy layouts are automatically unified
- ambiguous legacy layouts are not silently merged

### Migration Scope

Automatic migration should happen only as part of normal execution. This phase does not add a separate migration CLI command.

## Metadata Contract

Even though the filesystem no longer includes `output_group`, batch metadata should remain visible in artifacts.

Continue to preserve the following where applicable:

- `page_type`
- `output_group`
- `manifest_slug`
- `resolved_slug`
- `batch_id`
- `tags`

These fields should still appear in:

- `meta.json`
- Markdown frontmatter
- batch reporting artifacts

The difference is only that `relative_output_dir` and physical output layout become canonicalized around `people/<slug>`.

## Batch Runtime Impact

The batch runtime should continue to support:

- `txt` URL lists
- `jsonl` manifests
- `--resume`
- `--skip-invalid`
- duplicate detection
- batch reporting

But planner/runtime path resolution changes from:

```text
person/<output_group>/<slug>
```

to:

```text
people/<slug>
```

Consequences:

- duplicate detection becomes slug-path based within `people/`
- repeated entries with different `output_group` values but the same final slug now target one canonical bundle
- batch reports still keep the original `output_group` values for traceability

This is intentional. Grouping remains a corpus annotation, not a filesystem partition.

## README And Example Contract

README and examples should be updated to reflect the unified path contract:

- single-page examples show `output/people/<slug>/`
- batch examples also show `output/people/<slug>/`
- any mention of `person/default/<slug>` should be removed from user-facing docs unless explicitly marked as legacy

This phase should also add starter manifests under:

```text
examples/manifests/
```

## Starter Manifest Strategy

The first curated manifests should be award-centered rather than personality-centered.

Recommended initial files:

- `examples/manifests/turing-award-core.jsonl`
- `examples/manifests/fields-medal-core.jsonl`
- `examples/manifests/nobel-physics-core.jsonl`

These are not required to be exhaustive historical lists. They should be high-quality starter sets sized for practical batch runs.

Recommended target size:

- `10` to `20` people per manifest

Each entry should use the existing manifest schema and carry topical metadata:

```json
{"url":"https://en.wikipedia.org/wiki/Geoffrey_Hinton","page_type":"person","slug":"geoffrey-hinton","tags":["ai","turing-award"],"output_group":"turing-award"}
```

### Selection Principle

These starter manifests should optimize for:

- high notability
- strong article quality
- broad historical coverage
- usefulness as expansion anchors for later corpus growth

They should not try to encode every laureate immediately.

## Testing Strategy

Add regression coverage for the new path contract and migration behavior:

1. single-page path contract
   - `convert` writes to `people/<slug>`

2. batch path contract
   - `batch` writes to `people/<slug>`
   - `output_group` remains in metadata and report payloads

3. compatibility migration
   - a single matching legacy directory under `person/*/<slug>` is auto-migrated to `people/<slug>`
   - multiple matching legacy directories cause a clear error rather than silent merge

4. doc/examples contract
   - README and example manifests align with the unified output path

## Success Criteria

This phase is successful if:

- single-page and batch runs now emit the same canonical directory shape
- legacy simple batch outputs are automatically unified without manual cleanup
- ambiguous legacy collisions are rejected safely
- README no longer teaches conflicting path layouts
- the repository ships with award-based starter manifests that users can batch-run immediately

## Risks

The main risk is unintentional data movement during automatic migration.

Mitigations:

- only auto-migrate when there is exactly one legacy candidate
- never merge multiple legacy directories automatically
- keep migration limited to the current slug target rather than broad filesystem scanning

## Follow-Ups

Possible later work, but not part of this phase:

- a dedicated migration CLI for large legacy corpora
- manifest packs for additional award ecosystems such as Nobel Chemistry or Abel Prize
- list-page-assisted manifest generation workflows
