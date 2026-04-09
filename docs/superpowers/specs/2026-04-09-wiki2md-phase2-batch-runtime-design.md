# wiki2md Phase 2 Batch Runtime Design

## Goal

Upgrade `wiki2md` from a single-article converter with a basic batch loop into a resumable batch-processing tool that can reliably handle tens to hundreds of Wikipedia person-page URLs.

This phase focuses on three practical outcomes:

1. robust batch execution for large manifests
2. resumable state and useful failure artifacts
3. batch metadata that becomes part of the saved corpus, not just terminal output

The intent is to make `wiki2md` suitable for repeated corpus-building runs rather than one-off manual conversion.

## Why This Phase Next

The current project is already strong enough for single-page conversion and small ad hoc usage.

The biggest remaining gap between the current state and a more mature open-source tool is batch robustness:

- large runs should not fail on the first bad page
- existing outputs should be reused automatically
- failures should be easy to inspect and rerun
- batch-level metadata should survive into the final artifacts

This phase addresses those gaps without redesigning the article-conversion pipeline itself.

## Scope

### In Scope

- A dedicated internal batch runtime subsystem
- `jsonl` manifest support as the primary structured batch format
- Continued support for `wiki2md batch <file>` as the public CLI entrypoint
- Small-concurrency batch execution with continue-on-error behavior
- Automatic reuse of existing outputs via `skip-existing`
- Batch state storage and resumable execution
- Batch reports and retry artifacts
- Batch metadata threaded into `meta.json` and Markdown frontmatter

### Out of Scope

- New page-type parsing beyond `person`
- Generic non-person corpus support
- Distributed execution or queue-backed job orchestration
- Full checkpointed download resumability at the HTTP asset level
- Remote state stores or databases
- PyPI release automation and broader community docs beyond what this phase needs

## Recommended Architecture

`wiki2md` should keep the existing single-page conversion path as the canonical conversion unit.

Batch behavior should be implemented in a separate runtime subsystem with explicit module boundaries:

- `manifest`
  - load `txt` or `jsonl`
  - validate rows
  - fill defaults
  - normalize fields
- `planner`
  - resolve output paths
  - apply slug rules
  - detect duplicate URLs or output collisions
  - produce executable batch tasks
- `runner`
  - execute tasks with small concurrency
  - retry transient failures
  - honor `skip-existing`
  - continue on failure
- `state store`
  - persist batch state under the output directory
  - support automatic and explicit resume
- `reporter`
  - emit terminal progress
  - write machine-readable and human-readable batch artifacts

This is a deliberate split from the CLI layer. `cli.py` should stay thin and delegate orchestration to the batch runtime rather than embedding batch policy inline.

## CLI Contract

The public command should remain:

```bash
wiki2md batch <file>
```

The first phase of the batch runtime should add these options:

- `--output-dir`
- `--overwrite`
- `--concurrency <n>`
- `--resume <state-file>`
- `--skip-invalid`

Default behavior:

- continue on per-item conversion failure
- skip existing outputs
- small concurrency, recommended default `4`
- retry transient network-style failures `2` times

The existing `convert` and `inspect` commands should remain unchanged in user-facing behavior.

## Input Formats

### txt

Plain text remains supported for compatibility.

Rules:

- one URL per line
- ignore empty lines
- ignore lines beginning with `#`

Text input should be treated as the lowest-feature entry mode. It has no per-row metadata.

### jsonl Manifest

`jsonl` is the primary structured batch format for this phase.

Each line should represent one batch entry.

Recommended example:

```json
{"url":"https://en.wikipedia.org/wiki/Andrej_Karpathy","page_type":"person","slug":"andrej-karpathy","tags":["ai","person"],"output_group":"people-ai"}
```

Supported fields:

- `url`
- `page_type`
- `slug`
- `tags`
- `output_group`

Field rules:

- `url`
  - required
- `page_type`
  - optional
  - defaults to `person`
  - only `person` is valid in this phase
- `slug`
  - optional
  - when present, it overrides automatic slug derivation
- `tags`
  - optional
  - defaults to `[]`
  - must be `list[str]`
- `output_group`
  - optional
  - defaults to `default`

## Manifest Validation

Default behavior should be strict:

- validate the full manifest before starting the batch run
- if any row has a structural validation error, do not start execution
- exit with a non-zero status

Examples of validation errors:

- missing `url`
- `tags` not being an array of strings
- `page_type` not equal to `person`

Optional relaxed mode:

- `--skip-invalid`
- invalid rows are skipped instead of aborting the run
- invalid rows are written to batch reporting outputs
- `invalid.jsonl` should be produced for later repair

Strict validation is the default because the manifest is an input contract, not just a loose suggestion.

## Path Resolution And Corpus Layout

### Default Directory Structure

Batch output paths should become:

```text
output/
  person/
    default/
      andrej-karpathy/
        article.md
        meta.json
        references.json
        infobox.json
        assets/
```

The full shape is:

```text
output/<page_type>/<output_group>/<resolved_slug>/
```

Examples:

- `output/person/default/andrej-karpathy/`
- `output/person/people-ai/geoffrey-hinton/`

### Slug Resolution

Slug priority:

1. `manifest.slug`
2. automatically derived slug from the resolved article title

Rules:

- `manifest.slug` should be normalized and validated before use
- the final used path value should be recorded as `resolved_slug`
- the original requested value should be recorded as `manifest_slug`

### Duplicate Handling

The batch runtime should detect and skip:

- repeated URLs in the same manifest
- different rows that resolve to the same final output path or same effective slug within the same `page_type/output_group`

Skipped duplicates should be recorded in the batch report instead of aborting the entire run.

## Existing Output Policy

Default behavior is `skip-existing`.

If the target output directory already exists:

- do not rerun conversion
- record the item as `skipped_existing`
- continue the batch

This is a critical part of practical resume behavior for large corpus runs.

`--overwrite` should still force reruns when explicitly requested.

## Execution Model

The batch runtime should use small parallelism by default rather than full serial or aggressive high concurrency.

Recommended default:

- `concurrency = 4`

Why:

- fast enough for tens to hundreds of URLs
- less likely to trigger Wikipedia-side throttling or local instability
- easier to reason about during retries and reporting

Batch execution semantics:

- continue on per-item failure
- never stop the whole batch because one article failed conversion
- always print per-item outcome lines
- always print a final summary

Terminal statuses should include:

- `SUCCESS`
- `SKIPPED`
- `FAILED`
- `INVALID`
- `DUPLICATE`

## Retry Policy

Automatic retry should only apply to transient failures, not all failures.

Recommended default:

- retry transient network-style failures `2` times

Eligible examples:

- connection errors
- timeouts
- temporary upstream fetch failures
- retry-safe rate-limit style errors when identified as temporary

Ineligible examples:

- manifest validation errors
- unsupported page type
- output path conflicts
- deterministic parse failures that do not benefit from immediate retry

This keeps retries useful without turning repeated bad inputs into longer failures.

## Resume And State Model

### State Location

Batch state should live under the chosen output directory:

```text
output/.wiki2md/batches/<batch-id>/
```

This keeps state colocated with artifacts and makes runs portable with the output tree.

### Resume Modes

Both should be supported:

1. automatic resume
2. explicit resume via `--resume <state-file>`

Automatic resume should use a deliberately wide rule:

- if the same manifest path is used again, the batch runtime may continue using the existing state
- manifest content changes do not block rerun automatically
- reuse comes primarily from `skip-existing` plus saved state

This is intentionally pragmatic rather than cryptographically strict.

### State Contents

The persisted batch state should include at least:

- `batch_id`
- `manifest_path`
- `started_at`
- `updated_at`
- batch options such as concurrency and overwrite policy
- per-entry status
- resolved output path
- failure summary when applicable

Per-entry statuses should include:

- `pending`
- `success`
- `failed`
- `skipped_existing`
- `invalid`
- `duplicate`

## Reporting Artifacts

Each batch run should produce:

- terminal summary
- `batch-report.json`
- `failed.txt`
- `failed.jsonl`
- `invalid.jsonl` when invalid rows are skipped

### batch-report.json

This is the canonical machine-readable summary.

It should include:

- batch metadata
- manifest path
- output directory
- start/end timestamps
- configuration summary
- total counts by status
- per-entry outcomes

Each entry should capture enough detail for later debugging:

- original manifest row
- resolved slug
- resolved output path
- final status
- warning or error text when relevant

### failed.txt

This is the simple human-readable retry list.

It should contain one failed URL per line.

### failed.jsonl

This is the recommended retry artifact.

It should contain the full original manifest rows for failed items so metadata such as:

- `slug`
- `tags`
- `output_group`

is preserved for reruns.

`failed.txt` exists for quick human inspection. `failed.jsonl` is the authoritative structured retry input.

## Per-Artifact Metadata Threading

Batch metadata should not live only at the reporting layer.

For manifest-driven runs, the following fields should be written into both:

- `meta.json`
- `article.md` frontmatter

Required batch-aware additions:

- `manifest_slug`
- `resolved_slug`
- `output_group`
- `tags`

If the conversion is part of a batch run, it is also reasonable to include:

- `batch_id`

This makes the saved corpus self-describing even when files are later moved or consumed outside the original batch-report context.

## Internal Interfaces

The current single-article service should remain the conversion primitive.

Recommended adaptation:

- keep `Wiki2MdService.convert_url()` as the base unit
- extend conversion APIs so batch-specific metadata can influence:
  - output path selection
  - `meta.json`
  - Markdown frontmatter

This should be done through explicit typed inputs rather than implicit global state.

Recommended new internal concepts:

- `BatchManifestEntry`
- `PlannedBatchTask`
- `BatchRunConfig`
- `BatchRunState`
- `BatchEntryResult`

The intent is to keep batch logic typed, testable, and distinct from HTML normalization.

## Error Handling

The batch runtime should clearly separate:

- manifest validation errors
- planner conflicts
- transient conversion failures
- permanent conversion failures

Expected behavior:

- validation errors abort the run by default
- invalid rows are skipped only in `--skip-invalid` mode
- planner duplicates are skipped and reported
- transient conversion failures are retried
- permanent conversion failures are recorded and do not stop the batch

Terminal output should stay concise but specific enough to debug:

- item identifier
- status
- short failure reason when relevant

## Testing Strategy

This phase needs stronger test coverage in the batch layer than in the HTML parsing layer.

### Manifest Tests

Cover:

- valid `jsonl` rows
- missing `url`
- invalid `tags`
- unsupported `page_type`
- default filling for `page_type`, `tags`, and `output_group`
- `manifest.slug` priority

### Planner And State Tests

Cover:

- duplicate URL detection
- duplicate slug/path detection
- `skip-existing`
- state creation
- automatic resume
- explicit `--resume`
- reporting of duplicates and invalid rows

### Runner Tests

Cover:

- small-concurrency execution
- continue-on-error behavior
- transient retry behavior
- final status counts
- preservation of original manifest rows in `failed.jsonl`

### CLI Smoke Tests

Cover:

- `wiki2md batch <txt>`
- `wiki2md batch <jsonl>`
- generation of `batch-report.json`
- generation of `failed.txt`
- generation of `failed.jsonl`
- generation of `invalid.jsonl` under `--skip-invalid`

### Documentation Tests

Repository docs/examples should include at least one minimal `jsonl` manifest example and should stay aligned with the batch-report/output contract.

## Documentation Updates

This phase should update:

- `README.md`
  - explain `jsonl` manifests
  - explain resume behavior
  - explain `failed.jsonl` as the preferred retry input
- `examples/`
  - include a minimal manifest example
- CLI help text
  - document the new options and semantics

The README should remain concise, but batch usage must become a first-class documented workflow rather than a short note.

## Completion Criteria

Phase 2 should be considered complete when all of the following are true:

- `wiki2md batch` can process `50-100` person-page URLs without collapsing on the first error
- rerunning the same manifest meaningfully reuses prior outputs
- failed items can be retried from `failed.jsonl` without losing metadata
- manifest-driven metadata appears in `meta.json` and Markdown frontmatter
- state is written under `output/.wiki2md/batches/<batch-id>/`
- README and examples explain the batch workflow clearly
- test coverage exists for manifest validation, planning, state, reporting, and CLI smoke paths

## Recommendation

The recommended implementation strategy is to preserve the current public CLI shape while introducing a dedicated internal batch runtime.

That gives `wiki2md` a much stronger batch story without destabilizing the already-working single-article conversion path.

It also creates a clean foundation for later phases:

- broader page-type support
- smarter retry policies
- richer batch metadata
- more advanced corpus-management workflows
