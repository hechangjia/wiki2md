from pathlib import Path


def test_readme_mentions_primary_cli_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "wiki2md convert <url>" in readme
    assert "wiki2md inspect <url>" in readme
    assert "wiki2md batch <file>" in readme


def test_example_article_has_frontmatter() -> None:
    article = Path("examples/andrej-karpathy/article.md").read_text(encoding="utf-8")

    assert article.startswith("---\n")
    assert "source_url:" in article


def test_example_references_sidecar_exists() -> None:
    references = Path("examples/andrej-karpathy/references.json").read_text(encoding="utf-8")

    assert references.startswith("[\n")
