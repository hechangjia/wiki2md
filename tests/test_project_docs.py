import json
import re
from pathlib import Path


def test_readme_mentions_primary_cli_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "wiki2md convert <url>" in readme
    assert "wiki2md inspect <url>" in readme
    assert "wiki2md batch <file>" in readme
    assert "no inline Wikipedia citation markers" in readme
    assert "primary_url" in readme
    assert "kind" in readme


def test_example_article_has_frontmatter_and_clean_prose() -> None:
    article = Path("examples/andrej-karpathy/article.md").read_text(encoding="utf-8")

    assert article.startswith("---\n")
    assert "source_url:" in article
    assert re.search(r"\[\d+\]", article) is None


def test_example_references_sidecar_matches_enriched_contract() -> None:
    references = json.loads(
        Path("examples/andrej-karpathy/references.json").read_text(encoding="utf-8")
    )
    allowed_kinds = {"external", "wiki", "archive", "identifier", "other"}

    assert isinstance(references, list)
    assert references

    first = references[0]
    assert set(first) == {"id", "text", "primary_url", "links"}
    assert isinstance(first["text"], str)
    assert isinstance(first["links"], list)

    for entry in references:
        assert set(entry) == {"id", "text", "primary_url", "links"}
        assert entry["id"] is None or isinstance(entry["id"], str)
        assert isinstance(entry["text"], str)
        assert entry["primary_url"] is None or isinstance(entry["primary_url"], str)
        assert isinstance(entry["links"], list)
        for link in entry["links"]:
            assert set(link) == {"text", "href", "kind"}
            assert isinstance(link["text"], str)
            assert isinstance(link["href"], str)
            assert link["kind"] in allowed_kinds
