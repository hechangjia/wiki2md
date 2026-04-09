# wiki2md Release And README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `wiki2md` into a release-ready open-source project with stronger GitHub Actions workflows, a formal GitHub Release to PyPI publishing path, and a Chinese-first README.

**Architecture:** Keep extraction code untouched. Implement this phase as repository-surface work: add workflow contract tests, upgrade `.github/workflows/ci.yml`, add a dedicated `.github/workflows/publish.yml`, and rewrite `README.md` around a Chinese-first homepage plus release instructions. Use lightweight repository tests instead of snapshot-heavy YAML assertions.

**Tech Stack:** GitHub Actions YAML, Markdown, pytest, pathlib, PyYAML, Python 3.12/3.13, uv

---

## File Structure

- `README.md`: rewrite the repository homepage to be Chinese-first, add badges, add release instructions, keep a concise `## English Summary`
- `.github/workflows/ci.yml`: upgrade the existing CI workflow to support `push`, `pull_request`, and `workflow_dispatch`, with Python `3.12` and `3.13`
- `.github/workflows/publish.yml`: new release workflow triggered by `release.published`, validating the tag against `pyproject.toml` and publishing to PyPI via Trusted Publishing
- `tests/test_project_docs.py`: replace the current English-first README assertions with Chinese-first README and release-contract assertions while keeping the existing example artifact checks
- `tests/test_project_workflows.py`: new repository-level workflow contract tests for `ci.yml` and `publish.yml`
- `pyproject.toml`: version source read by the publish workflow; no edit expected in this phase
- `CHANGELOG.md`: referenced from the README release instructions; no content change required unless README and current changelog path drift

### Task 1: Lock The New README Contract In Tests

**Files:**
- Modify: `tests/test_project_docs.py`

- [ ] **Step 1: Replace the old English-first README assertions with Chinese-first contract tests**

Update the README-specific tests near the top of `tests/test_project_docs.py` so they assert the new homepage structure and release messaging:

```python
def test_readme_uses_chinese_first_structure_and_keeps_english_summary() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "把 Wikipedia 人物词条转换成适合 AI / RAG 使用的本地 Markdown 语料包" in readme
    assert "## 为什么适合 AI / RAG" in readme
    assert "## 快速开始" in readme
    assert "## 核心命令" in readme
    assert "## 单篇人物示例" in readme
    assert "## 批量语料工作流" in readme
    assert "## 输出契约" in readme
    assert "## 发布流程" in readme
    assert "## English Summary" in readme
    assert readme.index("## 快速开始") < readme.index("## 批量语料工作流")


def test_readme_mentions_release_flow_and_trusted_publishing() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "GitHub Release" in readme
    assert "PyPI" in readme
    assert "Trusted Publishing" in readme
    assert "pyproject.toml" in readme
    assert "CHANGELOG.md" in readme
    assert "v0.1.1" in readme
```

Keep the existing example/sidecar tests below them unchanged unless they need a heading rename to match the new README wording.

- [ ] **Step 2: Run the docs tests to verify the new README contract fails**

Run:

```bash
uv run pytest tests/test_project_docs.py -q
```

Expected: FAIL because the current README is still English-first and does not yet contain the Chinese headings, `## 发布流程`, or the Trusted Publishing release steps.

- [ ] **Step 3: Do not commit after the failing-test step**

Leave the worktree dirty and move directly to workflow-contract tests.

### Task 2: Add Workflow Contract Tests Before Changing CI

**Files:**
- Create: `tests/test_project_workflows.py`

- [ ] **Step 1: Create workflow-structure tests that parse GitHub Actions YAML safely**

Add a new `tests/test_project_workflows.py` with a YAML loader that preserves the literal `on` key:

```python
from pathlib import Path

import yaml


def load_workflow(path: str) -> dict[str, object]:
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_ci_workflow_supports_manual_dispatch_and_python_matrix() -> None:
    workflow = load_workflow(".github/workflows/ci.yml")

    assert "push" in workflow["on"]
    assert "pull_request" in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]

    matrix = workflow["jobs"]["quality"]["strategy"]["matrix"]["python-version"]
    assert matrix == ["3.12", "3.13"]


def test_ci_workflow_runs_quality_and_build_steps() -> None:
    workflow = load_workflow(".github/workflows/ci.yml")
    quality_steps = workflow["jobs"]["quality"]["steps"]
    build_steps = workflow["jobs"]["build"]["steps"]

    quality_commands = "\n".join(step.get("run", "") for step in quality_steps)
    build_commands = "\n".join(step.get("run", "") for step in build_steps)

    assert "uv run ruff check ." in quality_commands
    assert "uv run pytest -q" in quality_commands
    assert "uv build" in build_commands


def test_publish_workflow_uses_release_trigger_and_trusted_publishing() -> None:
    workflow = load_workflow(".github/workflows/publish.yml")

    assert workflow["on"]["release"]["types"] == ["published"]

    publish_job = workflow["jobs"]["publish"]
    assert publish_job["permissions"]["id-token"] == "write"
    assert publish_job["environment"]["name"] == "pypi"

    steps = publish_job["steps"]
    uses_values = [step.get("uses", "") for step in steps]
    assert "pypa/gh-action-pypi-publish@release/v1" in uses_values


def test_publish_workflow_validates_release_tag_against_pyproject_version() -> None:
    workflow = load_workflow(".github/workflows/publish.yml")
    validate_steps = workflow["jobs"]["validate-release"]["steps"]
    validate_commands = "\n".join(step.get("run", "") for step in validate_steps)

    assert "GITHUB_REF_NAME" in validate_commands
    assert "pyproject.toml" in validate_commands
    assert "version" in validate_commands
```

- [ ] **Step 2: Run the new workflow tests to verify they fail**

Run:

```bash
uv run pytest tests/test_project_workflows.py -q
```

Expected: FAIL because `.github/workflows/publish.yml` does not exist yet and the current `ci.yml` has no `workflow_dispatch`, no Python matrix, and no `quality`/`build` job split.

- [ ] **Step 3: Do not commit after the failing-test step**

Proceed directly to the CI workflow implementation.

### Task 3: Upgrade The CI Workflow For Daily Quality Gates

**Files:**
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_project_workflows.py`

- [ ] **Step 1: Replace the current single-job CI with a matrix quality job plus a build job**

Rewrite `.github/workflows/ci.yml` to this shape:

```yaml
name: ci

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Setup Python
        uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}

      - name: Setup uv
        uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check .

      - name: Test
        run: uv run pytest -q

  build:
    runs-on: ubuntu-latest
    needs: quality
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Setup Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Setup uv
        uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Build
        run: uv build
```

Keep CI offline and deterministic. Do not add live Wikipedia smoke tests.

- [ ] **Step 2: Re-run the workflow tests for the CI contract**

Run:

```bash
uv run pytest tests/test_project_workflows.py::test_ci_workflow_supports_manual_dispatch_and_python_matrix tests/test_project_workflows.py::test_ci_workflow_runs_quality_and_build_steps -q
```

Expected: the two CI tests PASS, while the publish-workflow tests still FAIL because `publish.yml` is not in place yet.

- [ ] **Step 3: Commit the CI workflow upgrade**

```bash
git add .github/workflows/ci.yml tests/test_project_workflows.py
git commit -m "ci: expand workflow matrix and manual dispatch"
```

### Task 4: Add The Release-Publish Workflow With Trusted Publishing

**Files:**
- Create: `.github/workflows/publish.yml`
- Test: `tests/test_project_workflows.py`

- [ ] **Step 1: Add a dedicated publish workflow with validate, build, and publish jobs**

Create `.github/workflows/publish.yml` with this structure:

```yaml
name: publish

on:
  release:
    types: [published]

jobs:
  validate-release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Setup Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Validate release version
        run: |
          python - <<'PY'
          import os
          import tomllib
          from pathlib import Path

          ref_name = os.environ["GITHUB_REF_NAME"]
          if not ref_name.startswith("v"):
              raise SystemExit("Release tag must start with 'v'")

          project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
          version = project["project"]["version"]
          if ref_name[1:] != version:
              raise SystemExit(
                  f"Release tag {ref_name} does not match project version {version}"
              )

          print(f"Validated release tag {ref_name} against project version {version}")
          PY

  build:
    runs-on: ubuntu-latest
    needs: validate-release
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Setup Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Setup uv
        uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Build distributions
        run: uv build

      - name: Upload distributions
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/*

  publish:
    runs-on: ubuntu-latest
    needs: build
    permissions:
      id-token: write
    environment:
      name: pypi
      url: https://pypi.org/p/wiki2md
    steps:
      - name: Download distributions
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist

      - name: Publish package distributions to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

Keep the publish workflow separate from the main CI workflow. Do not introduce token-based PyPI secrets.

- [ ] **Step 2: Re-run the workflow test file until all workflow assertions pass**

Run:

```bash
uv run pytest tests/test_project_workflows.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit the publish workflow**

```bash
git add .github/workflows/publish.yml tests/test_project_workflows.py
git commit -m "ci: add github release publish workflow"
```

### Task 5: Rewrite README Into A Chinese-First Release-Ready Homepage

**Files:**
- Modify: `README.md`
- Modify: `tests/test_project_docs.py`

- [ ] **Step 1: Rewrite the top of `README.md` with badges and a Chinese-first value proposition**

Open `README.md` with a Chinese-first hero and real repository badges:

```md
# wiki2md

[![CI](https://github.com/hechangjia/wiki2md/actions/workflows/ci.yml/badge.svg)](https://github.com/hechangjia/wiki2md/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wiki2md)](https://pypi.org/project/wiki2md/)
[![Python versions](https://img.shields.io/pypi/pyversions/wiki2md)](https://pypi.org/project/wiki2md/)
[![License](https://img.shields.io/github/license/hechangjia/wiki2md)](https://github.com/hechangjia/wiki2md/blob/main/LICENSE)

把 Wikipedia 人物词条转换成适合 AI / RAG 使用的本地 Markdown 语料包。

`wiki2md` 会把噪声较多的百科页面整理成稳定的本地语料目录：干净的 `article.md`、结构化 sidecar，以及本地 `assets/`，更适合切块、embedding、检索和审计。
```

Follow with:

```md
## 为什么适合 AI / RAG

- `article.md` 优先保留干净 prose，方便阅读、切块和 embeddings
- `meta.json`、`references.json`、`infobox.json` 保留结构化上下文和来源线索
- 本地 `assets/` 避免远程图片漂移
- `batch` 支持可恢复的大批量语料构建
```

- [ ] **Step 2: Rewrite the core Chinese sections while keeping one concrete single-page example**

Restructure the README to include these headings in order:

```md
## 快速开始
## 核心命令
## 单篇人物示例
## 批量语料工作流
## 输出契约
## 发布流程
## English Summary
```

Inside them, preserve the public CLI and include these exact commands:

```md
```bash
uv sync --extra dev
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
uv run wiki2md inspect "https://en.wikipedia.org/wiki/Andrej_Karpathy"
uv run wiki2md batch examples/batch/person-manifest.jsonl --output-dir output
```
```

Keep the single-page example centered on `examples/andrej-karpathy/` and keep the batch section below it.

- [ ] **Step 3: Add explicit release instructions and Trusted Publishing prerequisites**

Add a Chinese `## 发布流程` section with a concise numbered release path:

```md
## 发布流程

正式发布由 GitHub Release 触发，并通过 PyPI Trusted Publishing 完成。

1. 更新 `pyproject.toml` 中的版本号，例如 `0.1.0` -> `0.1.1`
2. 更新 `CHANGELOG.md`
3. 将发布提交推送到 `main`
4. 在 GitHub 上创建并发布 `v0.1.1` Release
5. `publish.yml` 会校验 release tag 与 `pyproject.toml` 版本一致后，再自动发布到 PyPI

前置条件：
- 需要先在 PyPI 项目侧配置 GitHub OIDC Trusted Publisher
- 仓库内不保存长期 PyPI token
```

Then close with a concise English summary:

```md
## English Summary

`wiki2md` converts Wikipedia person pages into clean local corpus artifacts for AI workflows. It focuses on `article.md`, structured JSON sidecars, local assets, and resumable batch processing. Current scope: English-first Wikipedia, Chinese-compatible, person pages as the current focus.
```

- [ ] **Step 4: Re-run the docs tests and fix any README wording drift**

Run:

```bash
uv run pytest tests/test_project_docs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the README localization and release guide**

```bash
git add README.md tests/test_project_docs.py
git commit -m "docs: localize readme and release guide"
```

### Task 6: Run Full Repository Verification And Close The Phase

**Files:**
- Verify: `README.md`
- Verify: `.github/workflows/ci.yml`
- Verify: `.github/workflows/publish.yml`
- Verify: `tests/test_project_docs.py`
- Verify: `tests/test_project_workflows.py`

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

- [ ] **Step 3: Build the package locally**

Run:

```bash
uv build
```

Expected artifacts:

- `dist/wiki2md-0.1.0.tar.gz`
- `dist/wiki2md-0.1.0-py3-none-any.whl`

- [ ] **Step 4: Commit only if verification required a follow-up fix**

If verification exposes a final wording or workflow-contract mismatch, fix it and commit:

```bash
git add README.md .github/workflows/ci.yml .github/workflows/publish.yml tests/test_project_docs.py tests/test_project_workflows.py
git commit -m "docs: finalize release readiness"
```

If all verification passes without further file changes, do not create an empty commit.

## Self-Review

Spec coverage check:

- CI split into stable daily workflow with `push`, `pull_request`, and `workflow_dispatch`: covered by Tasks 2 and 3
- dedicated `GitHub Release -> PyPI` workflow with Trusted Publishing: covered by Tasks 2 and 4
- `pyproject.toml` as the version source and tag/version validation: covered by Task 4
- Chinese-first README with a short English summary: covered by Tasks 1 and 5
- release/process documentation and badges: covered by Task 5
- lightweight repository-level tests for docs and workflows: covered by Tasks 1, 2, 3, and 4

Placeholder scan:

- no `TODO`, `TBD`, or deferred implementation notes remain
- each task includes exact file paths, code snippets, commands, and expected outcomes

Type consistency check:

- README headings asserted in `tests/test_project_docs.py` match the headings introduced in Task 5
- workflow job names asserted in `tests/test_project_workflows.py` match the `quality`, `build`, `validate-release`, and `publish` jobs introduced in Tasks 3 and 4
- the publish workflow uses the same version source (`pyproject.toml`) and tag format (`vX.Y.Z`) described in the spec
