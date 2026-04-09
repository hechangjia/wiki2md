# wiki2md Release And README Design

## Goal

Upgrade `wiki2md` from a functional open-source repository to a release-ready project with:

- stable day-to-day CI
- a formal GitHub Release to PyPI publishing flow
- a Chinese-first repository homepage with a short English summary

This phase focuses on release infrastructure and public-facing repository messaging, not extraction behavior.

## Why This Phase Now

The project already has the core product in place:

- single-page conversion works
- batch conversion works
- docs and examples already explain the output contract
- tests, lint, and build pass locally
- the repository already exists on GitHub

What is still incomplete is the outer operating surface:

- CI is currently minimal and single-version
- publishing is not yet formalized
- the README is still English-first even though the primary author and intended first users are Chinese-speaking

This phase closes that gap.

## Current State

The repository already contains:

- a basic `.github/workflows/ci.yml`
- `README.md`
- `CHANGELOG.md`
- `LICENSE`
- `pyproject.toml` with a fixed project version

The current version source is:

```toml
[project]
version = "0.1.0"
```

This phase should preserve that model. Versioning remains explicit and human-controlled.

## Audience

### Primary

- Chinese-speaking AI / RAG users building local knowledge corpora
- Python CLI users who want a reliable release and install path

### Secondary

- English-speaking open-source visitors who need a quick project summary

## Scope

### In Scope

- Upgrade CI to a clearer, release-ready structure
- Add a dedicated publish workflow for GitHub Release -> PyPI
- Use PyPI Trusted Publishing instead of stored API tokens
- Keep `pyproject.toml` as the single version source
- Rewrite the README to be Chinese-first
- Add a short English summary section to the README
- Add badges and release/install guidance that match the actual workflows
- Add tests that lock the new README and workflow contract at a high level

### Out of Scope

- parser changes
- corpus quality improvements
- live Wikipedia smoke tests in CI
- community files such as `CONTRIBUTING.md`, issue templates, or PR templates
- automatic versioning systems such as `setuptools-scm`
- TestPyPI or staged release environments

## Recommended Approach

There are three plausible paths:

1. minimal patching of the existing CI plus a simple release workflow
2. a release-ready structure with separate CI and publish workflows
3. a more platform-like automation setup with reusable workflows and heavier release tooling

The recommended approach is **2**.

It keeps the system understandable:

- one workflow for everyday quality gates
- one workflow for formal publishing
- one README optimized for the actual audience

It also avoids introducing more automation than the project currently needs.

## Workflow Architecture

This phase should keep the workflow surface intentionally small.

### `ci.yml`

Purpose:

- enforce the day-to-day quality bar for pushes and pull requests

Triggers:

- `push`
- `pull_request`
- `workflow_dispatch`

Runtime matrix:

- Python `3.12`
- Python `3.13`

Responsibilities:

- checkout code
- install `uv`
- run `uv sync --extra dev`
- run `uv run ruff check .`
- run `uv run pytest -q`
- run `uv build`

Constraints:

- no live Wikipedia network smoke tests
- no publishing logic
- no reliance on PyPI secrets

### `publish.yml`

Purpose:

- publish an official release to PyPI

Trigger:

- `release.published`

Responsibilities:

- validate the GitHub Release tag against the package version
- build the distribution artifacts
- optionally run a minimal publish-time verification step
- publish to PyPI through Trusted Publishing

Permissions should stay minimal and explicit. Publishing permissions should not live in `ci.yml`.

## Release Contract

The release model should be fully explicit.

### Version Source

The version source remains `[project].version` in [`pyproject.toml`](/Users/chia/Desktop/Projects/Wiki2Md/pyproject.toml).

No automatic version derivation from tags should be introduced in this phase.

### Release Flow

The intended release flow is:

1. bump the version in `pyproject.toml`
2. update `CHANGELOG.md`
3. push the release-ready commit to `main`
4. create and publish a GitHub Release such as `v0.1.1`
5. let `publish.yml` validate and publish the package to PyPI

### Validation Rules

`publish.yml` should enforce:

- the release tag must start with `v`
- the tag without `v` must exactly equal `[project].version`
- build artifacts must be produced successfully before publishing

This keeps tag/version drift impossible at publish time.

## PyPI Authentication

PyPI publishing should use **Trusted Publishing**.

That means:

- no long-lived PyPI API token stored in GitHub Secrets
- publishing is authorized through GitHub Actions OIDC
- repository documentation must mention the PyPI-side trusted publisher setup as a prerequisite

If the PyPI OIDC linkage is missing, the workflow should fail clearly rather than silently fallback to another auth mode.

## README Information Architecture

The README should become Chinese-first while staying legible to English-speaking visitors.

Recommended structure:

1. project title and badges
2. one-sentence Chinese value proposition
3. Chinese overview
4. Chinese quickstart
5. Chinese core commands
6. Chinese single-page example
7. Chinese batch / corpus workflow
8. Chinese output contract
9. Chinese development and release notes
10. `## English Summary`

This is not a full mirrored bilingual document. The English section should be concise and high-signal.

## README Content Priorities

The README should optimize for the primary audience first.

### Early Content

The first screen should communicate:

- what `wiki2md` produces
- why that output is useful for AI / RAG / local corpus workflows
- how to run one local example immediately

### Required Chinese Sections

The Chinese README content should clearly cover:

- project value proposition
- quickstart
- `convert`, `inspect`, and `batch`
- single-page example
- batch / resume / retry workflow
- output contract
- release process

### Required English Section

The `## English Summary` section should briefly explain:

- project purpose
- main commands
- primary outputs
- current scope: English-first Wikipedia, Chinese-compatible, person pages as current focus

## README Badges

This phase should add practical badges rather than decorative ones.

Recommended badges:

- CI status
- PyPI version
- supported Python versions
- license

Badge links should match the actual repository and workflows.

## Testing Requirements

This phase should protect the new repository contract with lightweight tests.

### README / Docs Tests

Tests should verify the README contains the key promises without freezing exact prose:

- Chinese quickstart content exists
- Chinese command coverage exists
- batch workflow and resume/retry content exist
- release steps are described
- `## English Summary` exists

### Workflow Contract Tests

Tests should verify at a structural level that:

- `ci.yml` exists
- `publish.yml` exists
- `ci.yml` contains `push`, `pull_request`, and `workflow_dispatch`
- `ci.yml` targets Python `3.12` and `3.13`
- `publish.yml` is triggered by `release.published`
- publishing is configured for Trusted Publishing rather than a token-based secret path

The goal is to catch accidental regressions without turning workflow tests into brittle YAML snapshots.

## Non-Functional Constraints

- keep CI stable and deterministic
- avoid live network dependencies in normal CI
- keep publishing logic isolated from test/lint workflow logic
- keep the README concise enough to scan from the repository homepage
- ensure all documentation matches the actual implemented release process

## Success Criteria

This phase is successful if:

1. the repository homepage is Chinese-first and clearly explains the product
2. English-speaking visitors can still understand the tool from a short summary
3. daily CI runs on `push`, `pull_request`, and manual dispatch across Python `3.12` and `3.13`
4. an official GitHub Release can trigger a PyPI publish through Trusted Publishing
5. version and release-tag mismatch is blocked automatically
6. local docs/tests/build continue to pass after the documentation and workflow changes
