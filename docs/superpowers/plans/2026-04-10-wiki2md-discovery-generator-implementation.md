# wiki2md Discovery Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bounded discovery generator that turns a Wikipedia entry page or preset into a reusable person manifest plus provenance sidecars.

**Architecture:** Introduce a dedicated discovery subsystem under the existing batch namespace. Keep discovery separate from `batch <file>` ingestion: discovery resolves a source, extracts and ranks candidates, writes `manifest.jsonl` / `index.md` / `discovery.json`, and hands off to the existing batch runtime.

**Tech Stack:** Python, httpx, BeautifulSoup4, Typer, pytest, respx, pydantic

---

### Task 1: Add discovery models and preset resolution

**Files:**
- Add: `src/wiki2md/discovery_models.py`
- Add: `src/wiki2md/discovery_presets.py`
- Modify: `tests/`

- [ ] **Step 1: Write the failing tests**

Cover:
- preset lookup for `turing-award`, `fields-medal`, `nobel-physics`
- source resolution from URL vs preset
- default metadata derivation:
  - `page_type = "person"`
  - derived `tags`
  - derived `output_group`
- final selection hard cap of `37`

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `uv run pytest tests/test_discovery_models.py -v`
Expected: FAIL because discovery models and preset resolution do not exist yet.

- [ ] **Step 3: Add minimal implementation**

Implement:
- `DiscoverySource`
- `DiscoveryCandidate`
- `DiscoveryRun`
- preset registry with the three built-in presets

- [ ] **Step 4: Run targeted tests to verify pass**

Run: `uv run pytest tests/test_discovery_models.py -v`
Expected: PASS

### Task 2: Add candidate extraction and bounded expansion

**Files:**
- Add: `src/wiki2md/discovery_extract.py`
- Modify: `tests/`

- [ ] **Step 1: Write the failing extraction tests**

Cover:
- extracting candidates from prose, lists, and tables
- excluding:
  - `Category:`
  - `Help:`
  - `Special:`
  - `Talk:`
  - fragment links
  - template/navigation control links
- preserving Depth 0 priority over expanded Depth 1 candidates

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `uv run pytest tests/test_discovery_extract.py -v`
Expected: FAIL because extractor and ranking logic do not exist yet.

- [ ] **Step 3: Add minimal implementation**

Implement:
- HTML candidate extraction helpers
- light person-link heuristics
- bounded `Depth 0` / `Depth 1` expansion hooks
- frequency- and depth-aware ranking

- [ ] **Step 4: Run targeted tests to verify pass**

Run: `uv run pytest tests/test_discovery_extract.py -v`
Expected: PASS

### Task 3: Add discovery writers and artifact contract

**Files:**
- Add: `src/wiki2md/discovery_writer.py`
- Modify: `tests/`

- [ ] **Step 1: Write the failing writer tests**

Cover:
- `manifest.jsonl` row shape
- `index.md` content contract
- `discovery.json` provenance contract
- output path under `output/discovery/<slug>/`

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `uv run pytest tests/test_discovery_writer.py -v`
Expected: FAIL because discovery artifact writers do not exist yet.

- [ ] **Step 3: Add minimal implementation**

Implement:
- manifest writer
- human-readable `index.md` renderer
- provenance-rich `discovery.json` writer

- [ ] **Step 4: Run targeted tests to verify pass**

Run: `uv run pytest tests/test_discovery_writer.py -v`
Expected: PASS

### Task 4: Add `wiki2md batch discover` CLI integration

**Files:**
- Modify: `src/wiki2md/cli.py`
- Add: `src/wiki2md/discovery_service.py`
- Modify: `tests/`

- [ ] **Step 1: Write the failing CLI smoke tests**

Cover:
- `wiki2md batch discover <preset>`
- `wiki2md batch discover <url>`
- generation of the three discovery artifacts
- emitted next-step guidance pointing to `wiki2md batch <manifest.jsonl>`

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `uv run pytest tests/test_cli.py -k discovery -v`
Expected: FAIL because the subcommand does not exist yet.

- [ ] **Step 3: Add minimal implementation**

Implement:
- `batch discover` command path
- source resolution
- discovery service orchestration
- artifact writeout under `output/discovery/<slug>/`

- [ ] **Step 4: Run targeted tests to verify pass**

Run: `uv run pytest tests/test_cli.py -k discovery -v`
Expected: PASS

### Task 5: Verify batch handoff and repository contract

**Files:**
- Modify: `README.md`
- Add or modify: `examples/`
- Modify: `tests/test_project_docs.py`

- [ ] **Step 1: Write the failing repo-contract tests**

Cover:
- README mentions `wiki2md batch discover`
- README shows discovery-to-batch workflow
- example discovery usage aligns with CLI contract

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `uv run pytest tests/test_project_docs.py -v`
Expected: FAIL because discovery workflow is not documented yet.

- [ ] **Step 3: Add minimal implementation**

Update:
- README discovery section
- example usage snippets
- any docs contract expectations

- [ ] **Step 4: Run targeted tests to verify pass**

Run: `uv run pytest tests/test_project_docs.py -v`
Expected: PASS

### Task 6: Verify end-to-end stability

**Files:**
- Modify as needed:
  - `src/wiki2md/cli.py`
  - `src/wiki2md/discovery_*.py`
  - `tests/test_discovery_*.py`
  - `README.md`

- [ ] **Step 1: Run discovery-focused suite**

Run:
`uv run pytest tests/test_discovery_models.py tests/test_discovery_extract.py tests/test_discovery_writer.py tests/test_cli.py -k discovery -v`

Expected: PASS

- [ ] **Step 2: Run full suite**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 3: Run lint**

Run: `uv run ruff check .`
Expected: PASS

- [ ] **Step 4: Run build**

Run: `uv build`
Expected: PASS
