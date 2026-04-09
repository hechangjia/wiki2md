from pathlib import Path

import yaml


# BaseLoader preserves the `on:` mappings that GitHub Actions uses while avoiding tag resolution;
# the YAML input comes from in-repo workflow files we trust.
def load_workflow(path: str) -> dict[str, object]:
    # BaseLoader keeps the GitHub `on:` trigger literal instead of parsing it as a boolean,
    # avoiding the `on:` boolean hazard other loaders impose.
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

    assert "uv sync --frozen --extra dev" in quality_commands
    assert "uv sync --frozen --extra dev" in build_commands
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
    build_steps = workflow["jobs"]["build"]["steps"]

    validate_checkout = next(step for step in validate_steps if step.get("name") == "Checkout")
    build_checkout = next(step for step in build_steps if step.get("name") == "Checkout")
    assert validate_checkout["with"]["ref"] == "${{ github.event.release.tag_name }}"
    assert build_checkout["with"]["ref"] == "${{ github.event.release.tag_name }}"

    build_commands = "\n".join(step.get("run", "") for step in build_steps)
    assert "uv sync --frozen --extra dev" in build_commands

    validate_steps = workflow["jobs"]["validate-release"]["steps"]
    validate_commands = "\n".join(step.get("run", "") for step in validate_steps)

    assert "GITHUB_REF_NAME" in validate_commands
    assert "pyproject.toml" in validate_commands
    assert "version" in validate_commands
