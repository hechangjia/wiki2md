# wiki2md README And Examples Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the repository homepage and examples so first-time visitors immediately understand `wiki2md` as a Wikipedia-to-Markdown corpus tool for RAG workflows.

**Architecture:** Keep the implementation docs-only. Lock the new onboarding promises in `tests/test_project_docs.py`, then rewrite `README.md` to lead with corpus value, a single-page artifact example, and a local-first quickstart. Reuse the existing `examples/andrej-karpathy/` and `examples/batch/person-manifest.jsonl` artifacts instead of adding new conversion behavior.

**Tech Stack:** Markdown, pytest, pathlib, json, Python 3.12, ruff

---

## File Structure

- `README.md`: rewrite the public-facing narrative so the homepage leads with RAG corpus value, a single-page example, and a local-first quickstart
- `tests/test_project_docs.py`: strengthen docs tests so the new README structure and examples contract remain stable
- `examples/andrej-karpathy/article.md`: existing single-page example used as the canonical excerpt source; no content change expected
- `examples/batch/person-manifest.jsonl`: existing batch example referenced from the README; only change if the README and example drift

### Task 1: Lock The New README Contract In Docs Tests

**Files:**
- Modify: `tests/test_project_docs.py`

- [ ] **Step 1: Add failing docs tests for README flow and single-page example emphasis**

Extend `tests/test_project_docs.py` with these tests:

```python
def test_readme_leads_with_rag_value_and_local_quickstart() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "RAG-ready local corpus artifacts" in readme
    assert "uv sync --extra dev" in readme
    assert 'uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"' in readme
    assert readme.index("## Quickstart") < readme.index("## Batch Workflow")


def test_readme_shows_single_page_example_before_batch_details() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## Single-Page Example" in readme
    assert "examples/andrej-karpathy/" in readme
    assert "# Andrej Karpathy" in readme
    assert "## Profile" in readme
    assert "Andrej Karpathy is a computer scientist." in readme
    assert readme.index("## Single-Page Example") < readme.index("## Batch Workflow")


def test_readme_points_to_examples_index_and_artifact_contract() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## Output Contract" in readme
    assert "`article.md`: the clean-first reading artifact for people and AI" in readme
    assert "`references.json`: structured provenance and source trail" in readme
    assert "`infobox.json`: machine-readable person facts" in readme
    assert "`assets/`: local images referenced by the article" in readme
    assert "examples/andrej-karpathy/" in readme
    assert "examples/batch/person-manifest.jsonl" in readme
```

- [ ] **Step 2: Run the docs tests to verify the new contract fails**

Run:

```bash
uv run pytest tests/test_project_docs.py -q
```

Expected: FAIL because the current README does not yet contain the new value proposition phrase, `## Single-Page Example`, or the stronger artifact-contract wording.

- [ ] **Step 3: Commit nothing yet**

Do not commit after the failing test step. Keep the worktree dirty and move directly to the README rewrite.

### Task 2: Rewrite README Around The Single-Page Corpus Demo

**Files:**
- Modify: `README.md`
- Verify only if needed: `examples/batch/person-manifest.jsonl`

- [ ] **Step 1: Rewrite the README opening to lead with corpus value**

Update the top of `README.md` so it opens with a product-style value statement and a short RAG-oriented explanation:

```md
# wiki2md

Turn Wikipedia person pages into cleaner, RAG-ready local corpus artifacts.

`wiki2md` takes noisy Wikipedia article pages and saves a deterministic local bundle that is easier to chunk, embed, index, and audit than raw HTML.
```

Follow it immediately with a short value section:

```md
## Why It Works For RAG

- Clean-first `article.md` output without inline Wikipedia citation markers in prose
- Structured sidecars for provenance, infobox facts, and run metadata
- Local image assets referenced from Markdown
- Resumable batch processing for larger corpus-building runs
```

- [ ] **Step 2: Add a local-first quickstart and keep the command surface explicit**

Rewrite the command and setup portion so the first runnable path is:

```md
## Quickstart

```bash
uv sync --extra dev
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
```
```

Preserve the existing command reference strings so docs tests and readers still see the public interface:

```md
## Commands

```bash
wiki2md convert <url>
wiki2md inspect <url>
wiki2md batch <file>
```
```

- [ ] **Step 3: Add a true single-page example section before the batch section**

Insert a `## Single-Page Example` section that uses the existing Andrej Karpathy sample as the product demo.

Include:

```md
## Single-Page Example

Input:

```bash
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
```

Output:

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

Excerpt from `examples/andrej-karpathy/article.md`:

```md
# Andrej Karpathy

![Andrej Karpathy portrait](./assets/001-infobox.jpg)

## Profile

- Born: 3 October 1986 Bratislava, Czechoslovakia
- Occupation: Computer scientist

Andrej Karpathy is a computer scientist.
```
```

Keep this section above batch details.

- [ ] **Step 4: Rewrite the artifact contract in user-facing language**

Replace or tighten the existing artifact explanation with this shape:

```md
## Output Contract

- `article.md`: the clean-first reading artifact for people and AI
- `meta.json`: run metadata and article-level context
- `references.json`: structured provenance and source trail
- `infobox.json`: machine-readable person facts
- `assets/`: local images referenced by the article
```

Keep the existing provenance notes about `primary_url`, `kind`, and best-effort behavior, but move them under this contract section instead of letting them dominate the opening.

- [ ] **Step 5: Reframe batch docs as the next step after single-page conversion**

Rename or rewrite the batch section to `## Batch Workflow` and keep these details:

```md
## Batch Workflow

`wiki2md batch` supports both plain `txt` URL lists and structured `jsonl` manifests.

```bash
wiki2md batch examples/batch/person-manifest.jsonl --output-dir output
```

Useful flags:
- `--output-dir`
- `--overwrite`
- `--concurrency`
- `--skip-invalid`
- `--resume`

Batch artifacts are written under `output/.wiki2md/batches/`:
- `state.json`
- `batch-report.json`
- `failed.txt`
- `failed.jsonl`
- `invalid.jsonl`
```

Keep the sentence that `failed.jsonl` is the preferred retry input because it preserves manifest metadata.

- [ ] **Step 6: Add an examples index at the end of the README**

Close the README with a short examples pointer section:

```md
## Examples

- Single-page artifact set: `examples/andrej-karpathy/`
- Batch manifest input: `examples/batch/person-manifest.jsonl`
```

- [ ] **Step 7: Re-run the docs tests to verify the rewritten README passes**

Run:

```bash
uv run pytest tests/test_project_docs.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the README polish**

```bash
git add README.md tests/test_project_docs.py
git commit -m "docs: polish readme onboarding"
```

If `examples/batch/person-manifest.jsonl` needed a small alignment edit, add it to the same commit.

### Task 3: Run Full Verification And Close The Docs Pass

**Files:**
- Verify: `README.md`
- Verify: `tests/test_project_docs.py`
- Verify: `examples/batch/person-manifest.jsonl`

- [ ] **Step 1: Run the full test suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 2: Run repo-wide lint**

Run:

```bash
uv run ruff check .
```

Expected: PASS.

- [ ] **Step 3: Build the package to ensure the docs pass did not break packaging**

Run:

```bash
uv build
```

Expected:

- `dist/wiki2md-0.1.0.tar.gz`
- `dist/wiki2md-0.1.0-py3-none-any.whl`

- [ ] **Step 4: Commit any remaining docs/example alignment**

If Task 2 already produced the final docs commit and Task 3 adds no file changes, do not create an extra empty commit.

If any follow-up docs/example adjustment was required during verification, commit it with:

```bash
git add README.md tests/test_project_docs.py examples/batch/person-manifest.jsonl
git commit -m "docs: finalize readme polish"
```

## Self-Review

Spec coverage check:

- productized README opening: covered by Task 2
- single-page example emphasis: covered by Task 2
- artifact-contract messaging: covered by Task 2
- batch workflow positioning and resume docs: covered by Task 2
- examples indexing and docs contract tests: covered by Tasks 1 and 2

Placeholder scan:

- no `TODO`, `TBD`, or deferred implementation notes remain in task steps
- each task includes exact file paths, code snippets, commands, and expected results

Type consistency check:

- README heading names used in tests (`## Quickstart`, `## Single-Page Example`, `## Output Contract`, `## Batch Workflow`) match the content changes requested in Task 2
- docs tests continue to reference the existing `examples/andrej-karpathy/` and `examples/batch/person-manifest.jsonl` paths used by the current repository
