import json
import re
from datetime import UTC, datetime
from pathlib import Path

from wiki2md.document import (
    Document,
    HeadingBlock,
    InfoboxData,
    InfoboxField,
    InfoboxImage,
    ParagraphBlock,
    ReferenceEntry,
    ReferenceLink,
)
from wiki2md.models import ArticleMetadata
from wiki2md.render_markdown import render_markdown


def build_example_document() -> Document:
    return Document(
        title="Andrej Karpathy",
        infobox=InfoboxData(
            title="Andrej Karpathy",
            image=InfoboxImage(
                title="File:Andrej_Karpathy_2024.jpg",
                path="assets/001-infobox.jpg",
                alt="Andrej Karpathy portrait",
                caption="Karpathy in 2024",
            ),
            fields=[
                InfoboxField(
                    label="Born",
                    text="3 October 1986 Bratislava, Czechoslovakia",
                    links=[],
                ),
                InfoboxField(label="Occupation", text="Computer scientist", links=[]),
            ],
        ),
        summary=["Andrej Karpathy is a computer scientist."],
        blocks=[
            HeadingBlock(level=2, text="Career"),
            ParagraphBlock(text="Karpathy worked at OpenAI and Tesla."),
        ],
        references=[
            ReferenceEntry(
                id="cite_note-karpathy-profile-1",
                text="Sample reference entry for Andrej Karpathy.",
                primary_url="https://example.com/karpathy-profile",
                links=[
                    ReferenceLink(
                        text="Example source",
                        href="https://example.com/karpathy-profile",
                        kind="external",
                    ),
                    ReferenceLink(
                        text="Andrej Karpathy",
                        href="https://en.wikipedia.org/wiki/Andrej_Karpathy",
                        kind="wiki",
                    ),
                ],
            )
        ],
    )


def build_example_metadata() -> ArticleMetadata:
    return ArticleMetadata(
        title="Andrej Karpathy",
        source_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
        source_lang="en",
        retrieved_at=datetime(2026, 4, 8, tzinfo=UTC),
        pageid=12345,
        revid=67890,
        image_manifest=[
            {
                "title": "File:Andrej_Karpathy_2024.jpg",
                "path": "assets/001-infobox.jpg",
            }
        ],
        cleanup_stats={
            "blocks": 2,
            "references": 1,
            "images_selected": 1,
            "infobox_fields": 2,
            "has_infobox": True,
        },
    )


def build_example_asset_map() -> dict[str, str]:
    return {"File:Andrej_Karpathy_2024.jpg": "assets/001-infobox.jpg"}


def test_readme_mentions_primary_cli_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "wiki2md convert <url>" in readme
    assert "wiki2md inspect <url>" in readme
    assert "wiki2md batch <file>" in readme
    assert "no inline Wikipedia citation markers" in readme
    assert "primary_url" in readme
    assert "kind" in readme
    assert "best-effort" in readme
    assert "may be null" in readme
    assert "jsonl" in readme
    assert "--resume" in readme
    assert "failed.jsonl" in readme
    assert "output/.wiki2md/batches/" in readme


def test_readme_uses_chinese_first_structure_and_keeps_english_summary() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    # Chinese-first homepage layout must stay before the English summary block.

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
    # Release flow coverage must call out trusted steps and artifacts.

    assert "GitHub Release" in readme
    assert "PyPI" in readme
    assert "Trusted Publishing" in readme
    assert "pyproject.toml" in readme
    assert "CHANGELOG.md" in readme
    assert "v0.1.1" in readme


def test_example_article_has_frontmatter_and_clean_prose() -> None:
    article = Path("examples/andrej-karpathy/article.md").read_text(encoding="utf-8")

    assert article.startswith("---\n")
    assert "source_url:" in article
    assert re.search(r"(?<=[\w\u4e00-\u9fff])\[\d+\]", article) is None


def test_example_references_sidecar_matches_enriched_contract() -> None:
    references = json.loads(
        Path("examples/andrej-karpathy/references.json").read_text(encoding="utf-8")
    )

    assert references == [
        reference.model_dump(mode="json") for reference in build_example_document().references
    ]


def test_readme_mentions_infobox_sidecar_and_profile_section() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "infobox.json" in readme
    assert "## Profile" in readme
    assert "      infobox.json" in readme
    assert (
        "Local `article.md`, `meta.json`, `references.json`, `infobox.json`, and `assets/` output"
        in readme
    )


def test_example_infobox_sidecar_matches_contract() -> None:
    payload = json.loads(
        Path("examples/andrej-karpathy/infobox.json").read_text(encoding="utf-8")
    )

    assert payload == build_example_document().infobox.model_dump(mode="json")


def test_example_article_matches_renderer_output() -> None:
    article = Path("examples/andrej-karpathy/article.md").read_text(encoding="utf-8")
    expected = render_markdown(
        build_example_document(),
        build_example_metadata(),
        build_example_asset_map(),
    )

    assert article == expected


def test_example_meta_matches_serialized_metadata() -> None:
    payload = json.loads(
        Path("examples/andrej-karpathy/meta.json").read_text(encoding="utf-8")
    )
    expected = build_example_metadata().model_dump(mode="json")
    expected = {key: value for key, value in expected.items() if key in payload}

    assert payload == expected


def test_batch_manifest_example_exists_and_is_valid_jsonl() -> None:
    manifest_path = Path("examples/batch/person-manifest.jsonl")
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    non_empty_lines = [line for line in lines if line.strip()]

    assert len(non_empty_lines) >= 2
    payloads = [json.loads(line) for line in non_empty_lines]
    assert all("url" in payload for payload in payloads)
    assert all(payload.get("page_type", "person") == "person" for payload in payloads)
    assert all("output_group" in payload for payload in payloads)
