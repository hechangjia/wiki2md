# wiki2md README And Examples Polish Design

## Goal

Improve the public-facing repository experience so a first-time visitor immediately understands that `wiki2md` turns Wikipedia person pages into clean, RAG-ready local corpus artifacts.

This phase focuses on repository presentation, not new extraction logic.

## Why This Phase Now

The core product is already functional:

- single-page conversion works
- batch conversion works
- structured sidecars and local assets work
- tests, lint, and build pass

What is still weak is the first-visit experience.

Right now the repository explains the tool, but it does not yet lead with the strongest value proposition for the intended audience:

- AI / RAG corpus builders
- Python CLI users

For those users, the first question is not "what flags does the CLI support?" It is:

`What corpus does this produce, and why is it better than scraping raw Wikipedia HTML?`

This phase fixes that.

## Audience

### Primary

- AI / RAG users who want cleaner source material for chunking, embeddings, and local knowledge bases
- Python users who want a deterministic CLI workflow and stable output contract

### Secondary

- note-taking and content-workflow users who want local Markdown plus structured sidecars

## Scope

### In Scope

- Rewrite the README opening narrative to lead with corpus value
- Show a single concrete person-page artifact example
- Make local-first usage the default quickstart path
- Explain the artifact contract more clearly
- Keep batch workflow documentation, but position it after the single-page example
- Strengthen `examples/` as a readable product demo surface
- Lock the new README/examples contract into docs tests

### Out of Scope

- new conversion features
- parser or normalization changes
- CI setup
- `CONTRIBUTING.md`
- issue templates or PR templates
- PyPI publishing or release workflow
- adding many more sample outputs

## Positioning

The README should read like a product page for a corpus-building tool, not just a CLI reference.

The primary message should be:

`wiki2md turns noisy Wikipedia pages into cleaner local corpus artifacts for RAG workflows.`

The secondary message should be:

`It is also a practical Python CLI with a stable artifact contract.`

The README should prioritize the first message and support the second.

## README Information Architecture

The README should be reordered into this flow:

1. **Value proposition**
   - one-sentence explanation of what `wiki2md` produces
   - one short paragraph explaining why this is useful for RAG / embeddings / local knowledge bases

2. **Why it is useful**
   - short bullets
   - emphasize clean prose, structured sidecars, local assets, and batch resumability

3. **Quickstart**
   - local-first setup
   - default path is:

   ```bash
   uv sync --extra dev
   uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
   ```

4. **Single-page example**
   - show the output directory tree
   - show a real `article.md` excerpt
   - make the reader understand the artifact set in under 10 seconds

5. **Artifact contract**
   - explain what each output file is for

6. **Batch workflow**
   - explain `txt` and `jsonl`
   - explain `--resume`
   - explain batch report artifacts
   - explain why `failed.jsonl` is the preferred retry input

7. **Examples index**
   - point readers to the single-page example first
   - point readers to the batch manifest example second

## README Content Priorities

### What Should Be Shown Early

The README should show two proof points near the top:

1. the output directory tree for a single converted person page
2. a real `article.md` excerpt with clean prose

The purpose is to make the output legible before the user reads about internal details.

### What Should Not Dominate Early

The README should not start with:

- a long flag table
- internal architecture detail
- batch runtime internals
- exhaustive JSON schema documentation

Those details matter, but they should come after the user understands the product outcome.

## Example Strategy

This phase should keep examples intentionally small and focused.

### Primary Example

`examples/andrej-karpathy/` remains the main example.

It should be the canonical answer to:

`What does one converted Wikipedia page look like?`

### Batch Example

`examples/batch/person-manifest.jsonl` remains the minimal structured batch example.

It should answer:

`What do I feed into batch mode?`

### Non-Goals For Examples

Do not add:

- many more people examples
- a full saved batch output directory
- separate English and Chinese demo sets

One strong single-page example is better than many thin ones.

## Artifact Contract Messaging

The README should explain the existing artifact set in plain user-facing language:

- `article.md`: the clean-first reading artifact for people and AI
- `meta.json`: run metadata and article-level context
- `references.json`: structured provenance and source trail
- `infobox.json`: machine-readable person facts
- `assets/`: local images referenced by the article

The explanation should stay high-signal and practical, not turn into a raw schema dump.

## Batch Workflow Messaging

Batch should remain documented, but it should be framed as:

- the next step after a successful single conversion
- a way to scale corpus building safely

Required batch topics:

- `txt` and `jsonl` manifest support
- useful flags, especially `--concurrency`, `--skip-invalid`, and `--resume`
- state and report files under `output/.wiki2md/batches/`
- `failed.jsonl` as the preferred retry input because it preserves metadata

## Testing Requirements

This phase should update repository docs tests so the public-facing contract stays stable.

Tests should assert:

- the README mentions `jsonl`
- the README mentions `--resume`
- the README mentions `failed.jsonl`
- the README mentions `output/.wiki2md/batches/`
- the batch example file exists and is valid JSONL

If README structure changes later, these tests should still enforce the critical onboarding promises.

## Success Criteria

This phase is successful if a new visitor can do all of the following from the repository homepage:

1. understand that `wiki2md` is a corpus-building tool for Wikipedia-to-Markdown workflows
2. see what a single converted person page looks like
3. run the first local command without guessing
4. understand what the core output files are for
5. find the batch entrypoint and resume/retry path without reading source code

## Non-Functional Constraints

- Keep the README concise enough to scan quickly
- Prefer real examples over abstract claims
- Keep the main example centered on one person page
- Do not let batch workflow details overwhelm the single-page narrative
- Preserve accuracy with the current codebase and tests
