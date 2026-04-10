# wiki2md Path Unification and Award Manifests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify single-page and batch output under `output/people/<slug>/`, safely auto-migrate simple legacy `output/person/<group>/<slug>/` bundles, and ship award-based starter manifests for batch corpus building.

**Architecture:** Introduce one small output-path helper module that owns canonical `people/<slug>` path construction and safe legacy migration. Thread that helper through `service.py` and the batch planner/runtime so both entrypoints converge on the same directory shape, then update README/tests/examples to teach and verify the new contract.

**Tech Stack:** Python 3.12+, `pathlib`, `shutil`, `pydantic`, `pytest`, `typer`, `uv`, `ruff`

---

## File Structure

- Create: `src/wiki2md/output_paths.py`
  - Canonical `people/<slug>` path construction
  - Legacy `person/*/<slug>` discovery
  - Safe one-candidate migration into the canonical path
- Create: `tests/test_output_paths.py`
  - Unit coverage for canonical path building and legacy migration
- Modify: `src/wiki2md/service.py`
  - Replace ad hoc `Path("people") / slug` handling with the shared helper
  - Run legacy migration before writing bundles
- Modify: `src/wiki2md/batch_planner.py`
  - Build `relative_output_dir` as `people/<slug>`
  - Keep `output_group` only in metadata, not the filesystem path
- Modify: `src/wiki2md/batch_runtime.py`
  - Apply migration before `skip-existing`
  - Keep `relative_output_dir`/`entry_key` aligned with the canonical path
- Modify: `tests/test_service.py`
  - Assert default single-page bundles land under `people/<slug>`
  - Update batch-context examples to `people/<slug>`
- Modify: `tests/test_batch_planner.py`
  - Assert planner emits `people/<slug>`
  - Assert duplicate detection is slug-based even when `output_group` differs
- Modify: `tests/test_batch_runtime.py`
  - Assert legacy `person/default/<slug>` bundles are auto-migrated then treated as `skipped_existing`
  - Update resume fixtures from `person/default/...` to `people/...`
- Modify: `tests/test_batch_state.py`
  - Update serialized `relative_output_dir` / `output_dir` fixtures to `people/...`
- Modify: `tests/test_cli.py`
  - Update fake batch-state payloads to `people/<slug>`
- Modify: `tests/test_writer.py`
  - Keep custom relative-output-dir coverage but update path-contract examples that currently assume `person/default/...`
- Modify: `README.md`
  - Document unified `output/people/<slug>/` layout
  - Explain that `output_group` remains metadata-only
  - Point users to award-based starter manifests
- Modify: `tests/test_project_docs.py`
  - Lock the new path contract in README/examples
  - Validate award manifests exist and parse
- Create: `examples/manifests/turing-award-core.jsonl`
- Create: `examples/manifests/fields-medal-core.jsonl`
- Create: `examples/manifests/nobel-physics-core.jsonl`

## Task 0: Isolate The Work In A Dedicated Worktree

**Files:**
- Create: `.worktrees/wiki2md-path-unification/` (git worktree)

- [ ] **Step 1: Create a dedicated worktree from clean `main`**

Run:

```bash
git worktree add .worktrees/wiki2md-path-unification -b wiki2md-path-unification
cd .worktrees/wiki2md-path-unification
```

Expected: a clean worktree rooted at `.worktrees/wiki2md-path-unification` with no unrelated `asset-download-resilience` edits.

- [ ] **Step 2: Install the dev environment inside the worktree**

Run:

```bash
uv sync --extra dev
```

Expected: the worktree has the same dependencies as root, but implementation happens in isolation.

- [ ] **Step 3: Verify the worktree starts clean**

Run:

```bash
git status --short
```

Expected: no output.

## Task 1: Write Failing Tests For Canonical `people/<slug>` Paths And Legacy Migration

**Files:**
- Create: `tests/test_output_paths.py`
- Modify: `tests/test_batch_planner.py`
- Modify: `tests/test_batch_runtime.py`
- Modify: `tests/test_service.py`
- Modify: `tests/test_batch_state.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add unit tests for canonical path building and legacy migration**

Create `tests/test_output_paths.py`:

```python
from pathlib import Path

import pytest

from wiki2md.errors import WriteError
from wiki2md.output_paths import (
    canonical_people_relative_output_dir,
    ensure_canonical_people_output_dir,
)


def test_canonical_people_relative_output_dir_uses_people_root() -> None:
    assert canonical_people_relative_output_dir("andrej-karpathy") == Path(
        "people/andrej-karpathy"
    )


def test_ensure_canonical_people_output_dir_migrates_single_legacy_directory(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    legacy_dir = output_root / "person" / "default" / "andrej-karpathy"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "article.md").write_text("# Legacy\n", encoding="utf-8")

    final_dir = ensure_canonical_people_output_dir(
        output_root,
        Path("people/andrej-karpathy"),
    )

    assert final_dir == output_root / "people" / "andrej-karpathy"
    assert final_dir.exists()
    assert (final_dir / "article.md").read_text(encoding="utf-8") == "# Legacy\n"
    assert not legacy_dir.exists()


def test_ensure_canonical_people_output_dir_rejects_multiple_legacy_directories(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    (output_root / "person" / "default" / "andrej-karpathy").mkdir(parents=True)
    (output_root / "person" / "people-ai" / "andrej-karpathy").mkdir(parents=True)

    with pytest.raises(WriteError, match="Multiple legacy output directories"):
        ensure_canonical_people_output_dir(
            output_root,
            Path("people/andrej-karpathy"),
        )
```

- [ ] **Step 2: Update planner/runtime/service tests to the new path contract**

Apply these edits:

```python
# tests/test_batch_planner.py
assert tasks[0].relative_output_dir == "people/karpathy-manifest"
assert {item.relative_output_dir for item in duplicates} == {"people/andrej-karpathy"}


def test_plan_batch_tasks_treats_different_output_groups_as_one_canonical_slug() -> None:
    tasks, duplicates = plan_batch_tasks(
        [
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Geoffrey_Hinton",
                output_group="turing-award",
            ),
            BatchManifestEntry(
                url="https://en.wikipedia.org/wiki/Geoffrey_Hinton_(researcher)",
                slug="geoffrey-hinton",
                output_group="ai-core",
            ),
        ],
        output_root=Path("output"),
    )

    assert len(tasks) == 1
    assert len(duplicates) == 1
    assert duplicates[0].relative_output_dir == "people/geoffrey-hinton"
```

```python
# tests/test_batch_runtime.py
existing_dir = tmp_path / "output" / "person" / "default" / "fei-fei-li"
existing_dir.mkdir(parents=True)

...

assert statuses["https://en.wikipedia.org/wiki/Fei-Fei_Li"] == "skipped_existing"
assert (tmp_path / "output" / "people" / "fei-fei-li").exists()
assert not existing_dir.exists()
```

```python
# tests/test_service.py
assert Path(result.output_dir) == tmp_path / "output" / "people" / "andrej-karpathy"

...

context=ConversionContext(
    relative_output_dir="people/karpathy-final",
    page_type="person",
    output_group="people-ai",
    manifest_slug="karpathy-manifest",
    resolved_slug="karpathy-final",
    tags=["ai", "person"],
    batch_id="batch-123",
)

...

context=ConversionContext(
    relative_output_dir="people/custom-slug",
    page_type="person",
    output_group="people-ai",
    manifest_slug="karpathy-manifest",
)
```

```python
# tests/test_batch_state.py
relative_output_dir="people/andrej-karpathy"
output_dir=str(tmp_path / "output" / "people" / "andrej-karpathy")
```

```python
# tests/test_cli.py
relative_output_dir="people/andrej-karpathy"
relative_output_dir="people/fei-fei-li"
relative_output_dir="people/yann-lecun"
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
uv run pytest \
  tests/test_output_paths.py \
  tests/test_batch_planner.py \
  tests/test_batch_runtime.py \
  tests/test_service.py \
  tests/test_batch_state.py \
  tests/test_cli.py \
  -q
```

Expected: FAIL because `wiki2md.output_paths` does not exist and the current planner/runtime still emit `person/<group>/<slug>`.

- [ ] **Step 4: Commit the failing tests**

```bash
git add \
  tests/test_output_paths.py \
  tests/test_batch_planner.py \
  tests/test_batch_runtime.py \
  tests/test_service.py \
  tests/test_batch_state.py \
  tests/test_cli.py
git commit -m "test: cover canonical people output paths"
```

## Task 2: Implement Canonical Path Helpers And Thread Them Through Convert/Batch

**Files:**
- Create: `src/wiki2md/output_paths.py`
- Modify: `src/wiki2md/service.py`
- Modify: `src/wiki2md/batch_planner.py`
- Modify: `src/wiki2md/batch_runtime.py`
- Modify: `tests/test_output_paths.py`
- Modify: `tests/test_batch_planner.py`
- Modify: `tests/test_batch_runtime.py`
- Modify: `tests/test_service.py`
- Modify: `tests/test_batch_state.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add a shared output-path helper module**

Create `src/wiki2md/output_paths.py`:

```python
from pathlib import Path

from wiki2md.errors import WriteError
from wiki2md.writer import normalize_relative_output_dir


def canonical_people_relative_output_dir(slug: str) -> Path:
    return normalize_relative_output_dir(Path("people") / slug)


def _legacy_people_candidates(output_root: Path, slug: str) -> list[Path]:
    legacy_root = output_root / "person"
    if not legacy_root.exists():
        return []
    return sorted(
        candidate
        for candidate in legacy_root.glob(f"*/{slug}")
        if candidate.is_dir()
    )


def ensure_canonical_people_output_dir(output_root: Path, relative_output_dir: Path) -> Path:
    relative_output_dir = normalize_relative_output_dir(relative_output_dir)
    final_dir = output_root / relative_output_dir

    if relative_output_dir.parts[:1] != ("people",):
        return final_dir
    if final_dir.exists():
        return final_dir

    slug = relative_output_dir.name
    legacy_candidates = _legacy_people_candidates(output_root, slug)
    if not legacy_candidates:
        return final_dir
    if len(legacy_candidates) > 1:
        candidates = ", ".join(
            str(path.relative_to(output_root)) for path in legacy_candidates
        )
        raise WriteError(
            f"Multiple legacy output directories found for slug '{slug}': {candidates}"
        )

    legacy_dir = legacy_candidates[0]
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    legacy_dir.replace(final_dir)

    legacy_parent = legacy_dir.parent
    if legacy_parent.exists() and not any(legacy_parent.iterdir()):
        legacy_parent.rmdir()

    legacy_root = output_root / "person"
    if legacy_root.exists() and not any(legacy_root.iterdir()):
        legacy_root.rmdir()

    return final_dir
```

- [ ] **Step 2: Route single-page conversion through the shared canonical path**

Modify `src/wiki2md/service.py`:

```python
from wiki2md.output_paths import (
    canonical_people_relative_output_dir,
    ensure_canonical_people_output_dir,
)

...

relative_output_dir = canonical_people_relative_output_dir(resolution.slug)
resolved_slug: str | None = None
if context is not None:
    relative_output_dir = normalize_relative_output_dir(Path(context.relative_output_dir))
    resolved_slug = relative_output_dir.name

ensure_canonical_people_output_dir(self.output_root, relative_output_dir)
```

This keeps direct `convert` canonical and makes normal execution absorb a single legacy `person/*/<slug>` directory before bundle writing.

- [ ] **Step 3: Route batch planning and `skip-existing` through the same canonical path**

Modify `src/wiki2md/batch_planner.py`:

```python
from wiki2md.output_paths import canonical_people_relative_output_dir

...

resolved_slug = entry.slug or resolution.slug
relative_output_dir = str(canonical_people_relative_output_dir(resolved_slug))
```

Modify `src/wiki2md/batch_runtime.py`:

```python
from pathlib import Path

from wiki2md.output_paths import ensure_canonical_people_output_dir

...

relative_output_dir = Path(task.relative_output_dir)
target_dir = ensure_canonical_people_output_dir(output_root, relative_output_dir)
if target_dir.exists() and not config.overwrite:
    return BatchStateEntry(
        entry_key=task.entry_key,
        url=task.entry.url,
        status="skipped_existing",
        relative_output_dir=task.relative_output_dir,
        output_dir=str(target_dir),
        manifest_entry=task.entry,
    )
```

Do not remove `output_group` from `ConversionContext` or `ArticleMetadata`; only remove it from path construction.

- [ ] **Step 4: Run the targeted tests and then the full suite**

Run:

```bash
uv run pytest \
  tests/test_output_paths.py \
  tests/test_batch_planner.py \
  tests/test_batch_runtime.py \
  tests/test_service.py \
  tests/test_batch_state.py \
  tests/test_cli.py \
  -q
uv run pytest -q
```

Expected: the targeted path tests pass first, then the full suite passes after the remaining fixture updates are applied.

- [ ] **Step 5: Commit the path-unification implementation**

```bash
git add \
  src/wiki2md/output_paths.py \
  src/wiki2md/service.py \
  src/wiki2md/batch_planner.py \
  src/wiki2md/batch_runtime.py \
  tests/test_output_paths.py \
  tests/test_batch_planner.py \
  tests/test_batch_runtime.py \
  tests/test_service.py \
  tests/test_batch_state.py \
  tests/test_cli.py
git commit -m "feat: unify wiki2md output paths under people"
```

## Task 3: Update README, Doc Tests, And Add Award-Based Starter Manifests

**Files:**
- Modify: `README.md`
- Modify: `tests/test_project_docs.py`
- Modify: `tests/test_writer.py`
- Create: `examples/manifests/turing-award-core.jsonl`
- Create: `examples/manifests/fields-medal-core.jsonl`
- Create: `examples/manifests/nobel-physics-core.jsonl`

- [ ] **Step 1: Update README to teach the unified path contract**

Apply edits like:

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

Update the batch section to explain:

```markdown
批量模式和单篇模式现在都会统一落到 `output/people/<slug>/`。
`output_group` 仍然保留在 `meta.json`、frontmatter 和 batch report 中，但不再参与目录层级。
```

Point users at an award-based starter run:

```bash
uv run wiki2md batch examples/manifests/turing-award-core.jsonl --output-dir output
```

- [ ] **Step 2: Add award-based starter manifests under `examples/manifests/`**

Create `examples/manifests/turing-award-core.jsonl`:

```json
{"url":"https://en.wikipedia.org/wiki/John_McCarthy_(computer_scientist)","page_type":"person","slug":"john-mccarthy","tags":["computer-science","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Donald_Knuth","page_type":"person","slug":"donald-knuth","tags":["computer-science","algorithms","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Edsger_W._Dijkstra","page_type":"person","slug":"edsger-w-dijkstra","tags":["computer-science","programming-languages","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Barbara_Liskov","page_type":"person","slug":"barbara-liskov","tags":["computer-science","programming-languages","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Leslie_Lamport","page_type":"person","slug":"leslie-lamport","tags":["computer-science","distributed-systems","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Judea_Pearl","page_type":"person","slug":"judea-pearl","tags":["computer-science","ai","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Tim_Berners-Lee","page_type":"person","slug":"tim-berners-lee","tags":["computer-science","web","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Geoffrey_Hinton","page_type":"person","slug":"geoffrey-hinton","tags":["computer-science","ai","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Yann_LeCun","page_type":"person","slug":"yann-lecun","tags":["computer-science","ai","turing-award"],"output_group":"turing-award"}
{"url":"https://en.wikipedia.org/wiki/Alan_Kay","page_type":"person","slug":"alan-kay","tags":["computer-science","oop","turing-award"],"output_group":"turing-award"}
```

Create `examples/manifests/fields-medal-core.jsonl`:

```json
{"url":"https://en.wikipedia.org/wiki/Jean-Pierre_Serre","page_type":"person","slug":"jean-pierre-serre","tags":["mathematics","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/Michael_Atiyah","page_type":"person","slug":"michael-atiyah","tags":["mathematics","geometry","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/John_Milnor","page_type":"person","slug":"john-milnor","tags":["mathematics","topology","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/David_Mumford","page_type":"person","slug":"david-mumford","tags":["mathematics","algebraic-geometry","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/Shing-Tung_Yau","page_type":"person","slug":"shing-tung-yau","tags":["mathematics","geometry","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/Grigori_Perelman","page_type":"person","slug":"grigori-perelman","tags":["mathematics","geometry","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/Terence_Tao","page_type":"person","slug":"terence-tao","tags":["mathematics","analysis","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/Peter_Scholze","page_type":"person","slug":"peter-scholze","tags":["mathematics","number-theory","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/Maryna_Viazovska","page_type":"person","slug":"maryna-viazovska","tags":["mathematics","number-theory","fields-medal"],"output_group":"fields-medal"}
{"url":"https://en.wikipedia.org/wiki/Lars_Ahlfors","page_type":"person","slug":"lars-ahlfors","tags":["mathematics","analysis","fields-medal"],"output_group":"fields-medal"}
```

Create `examples/manifests/nobel-physics-core.jsonl`:

```json
{"url":"https://en.wikipedia.org/wiki/Albert_Einstein","page_type":"person","slug":"albert-einstein","tags":["physics","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Marie_Curie","page_type":"person","slug":"marie-curie","tags":["physics","chemistry","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Niels_Bohr","page_type":"person","slug":"niels-bohr","tags":["physics","quantum","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Max_Planck","page_type":"person","slug":"max-planck","tags":["physics","quantum","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Erwin_Schr%C3%B6dinger","page_type":"person","slug":"erwin-schrodinger","tags":["physics","quantum","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Richard_Feynman","page_type":"person","slug":"richard-feynman","tags":["physics","qed","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Steven_Weinberg","page_type":"person","slug":"steven-weinberg","tags":["physics","particle-physics","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Peter_Higgs","page_type":"person","slug":"peter-higgs","tags":["physics","particle-physics","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Subrahmanyan_Chandrasekhar","page_type":"person","slug":"subrahmanyan-chandrasekhar","tags":["physics","astrophysics","nobel-physics"],"output_group":"nobel-physics"}
{"url":"https://en.wikipedia.org/wiki/Donna_Strickland","page_type":"person","slug":"donna-strickland","tags":["physics","laser-physics","nobel-physics"],"output_group":"nobel-physics"}
```

- [ ] **Step 3: Lock the README/examples contract in doc tests**

Modify `tests/test_project_docs.py`:

```python
def test_readme_uses_people_output_contract_for_single_and_batch_examples() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "output/\n  people/" in readme
    assert "output/people/" in readme
    assert "person/default/" not in readme
    assert "examples/manifests/turing-award-core.jsonl" in readme
    assert "examples/manifests/fields-medal-core.jsonl" in readme
    assert "examples/manifests/nobel-physics-core.jsonl" in readme


def test_award_manifests_exist_and_are_valid_jsonl() -> None:
    manifest_expectations = {
        "examples/manifests/turing-award-core.jsonl": "turing-award",
        "examples/manifests/fields-medal-core.jsonl": "fields-medal",
        "examples/manifests/nobel-physics-core.jsonl": "nobel-physics",
    }

    for path, output_group in manifest_expectations.items():
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        payloads = [json.loads(line) for line in lines if line.strip()]
        assert len(payloads) >= 10
        assert all(payload.get("page_type", "person") == "person" for payload in payloads)
        assert all(payload.get("output_group") == output_group for payload in payloads)
        assert all(payload.get("slug") for payload in payloads)
```

Update any writer-path assertions that still hard-code `person/default/...` so they follow the canonical `people/<slug>` examples.

- [ ] **Step 4: Run docs/examples tests and then the full verification suite**

Run:

```bash
uv run pytest tests/test_project_docs.py tests/test_writer.py -q
uv run pytest -q
uv run ruff check .
uv build
```

Expected: docs/tests pass, the full suite stays green, lint passes, and packaging still succeeds.

- [ ] **Step 5: Commit the docs and manifest additions**

```bash
git add \
  README.md \
  tests/test_project_docs.py \
  tests/test_writer.py \
  examples/manifests/turing-award-core.jsonl \
  examples/manifests/fields-medal-core.jsonl \
  examples/manifests/nobel-physics-core.jsonl
git commit -m "docs: add award starter manifests and path contract"
```

## Task 4: Smoke-Test The Unified Corpus Workflow

**Files:**
- Modify: none

- [ ] **Step 1: Smoke-test a single-page conversion into the canonical path**

Run:

```bash
uv run wiki2md convert "https://en.wikipedia.org/wiki/Carl_Friedrich_Gauss" --output-dir /tmp/wiki2md-path-smoke --overwrite
```

Expected: the returned `article.md` path is under `/tmp/wiki2md-path-smoke/people/carl-friedrich-gauss/`.

- [ ] **Step 2: Smoke-test an award manifest batch run**

Run:

```bash
uv run wiki2md batch examples/manifests/turing-award-core.jsonl --output-dir /tmp/wiki2md-award-batch
```

Expected:

- terminal prints `SUCCESS`/`SKIPPED_EXISTING` lines
- output bundles land under `/tmp/wiki2md-award-batch/people/<slug>/`
- `/tmp/wiki2md-award-batch/.wiki2md/batches/.../batch-report.json` exists

- [ ] **Step 3: Confirm grouping survived in metadata instead of the filesystem**

Run:

```bash
rg -n '"output_group": "turing-award"' /tmp/wiki2md-award-batch/people -g meta.json
```

Expected: at least one match inside a `meta.json`, proving `output_group` still survives in artifact metadata.

- [ ] **Step 4: Commit only if smoke uncovered a real fix**

If the smoke tests reveal a bug that required code changes, commit that fix separately:

```bash
git add <touched-files>
git commit -m "fix: complete people path unification smoke fixes"
```

If no additional code changes were needed, do not create an extra commit.

## Self-Review Checklist

- Spec coverage:
  - unified `people/<slug>` path: Task 1 + Task 2
  - safe legacy migration: Task 1 + Task 2
  - metadata keeps `output_group`: Task 2 + Task 3
  - README/examples contract: Task 3
  - award starter manifests: Task 3
- Placeholder scan:
  - no `TODO`/`TBD`
  - each code-changing step includes concrete code or exact file contents
- Type consistency:
  - helper names are consistent: `canonical_people_relative_output_dir`, `ensure_canonical_people_output_dir`
  - canonical runtime path stays `people/<slug>` across planner, service, runtime, docs, and tests
