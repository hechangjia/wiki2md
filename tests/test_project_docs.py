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
    assert "wiki2md batch discover <url-or-preset>" in readme
    assert "primary_url" in readme
    assert "kind" in readme
    assert "jsonl" in readme
    assert "--resume" in readme
    assert "failed.jsonl" in readme
    assert "output/.wiki2md/batches/" in readme


def test_readme_installed_user_batch_example_uses_local_input() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    quickstart = readme.split("用户安装路径：", maxsplit=1)[1].split(
        "贡献者仓库路径：", maxsplit=1
    )[0]

    assert "wiki2md batch ./urls.txt --output-dir output" in quickstart
    assert "examples/batch/person-manifest.jsonl" not in quickstart


def test_readme_uses_chinese_first_structure_and_keeps_english_summary() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    # Chinese-first homepage layout must stay before the English summary block.

    assert "Wikipedia 条目" in readme
    assert "本地 Markdown" in readme
    assert "## English Summary" in readme
    chinese_headings = [
        "## 为什么适合",
        "## 快速开始",
        "## 核心命令",
        "## 单篇转换示例",
        "## 批量语料工作流",
        "## 输出契约",
        "## 发布流程",
    ]

    for heading in chinese_headings:
        assert heading in readme

    english_summary_index = readme.index("## English Summary")
    chinese_indices = {heading: readme.index(heading) for heading in chinese_headings}
    assert all(index < english_summary_index for index in chinese_indices.values())
    assert max(chinese_indices.values()) < english_summary_index
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


def test_readme_shows_single_page_example_before_batch_details() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## 单篇转换示例" in readme
    assert "examples/andrej-karpathy/" in readme
    assert "# Andrej Karpathy" in readme
    assert "Andrej Karpathy is a computer scientist." in readme
    assert "`assets/`" in readme
    assert "Linux" in readme
    assert readme.index("## 单篇转换示例") < readme.index("## 输出契约")
    assert readme.index("## 单篇转换示例") < readme.index("## 批量语料工作流")


def test_readme_points_to_examples_index_and_artifact_contract() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## 输出契约" in readme
    assert "article.md" in readme
    assert "references.json" in readme
    assert "infobox.json" in readme
    assert "`assets/`" in readme
    assert "examples/andrej-karpathy/" in readme
    assert "examples/manifests/turing-award-core.jsonl" in readme
    assert "examples/manifests/fields-medal-core.jsonl" in readme
    assert "examples/manifests/nobel-physics-core.jsonl" in readme


def test_readme_documents_discovery_to_batch_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## 人物发现工作流" in readme
    assert "wiki2md batch discover turing-award --output-dir output" in readme
    assert "output/discovery/turing-award/manifest.jsonl" in readme
    assert "wiki2md batch output/discovery/turing-award/manifest.jsonl --output-dir output" in (
        readme
    )


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


def test_readme_mentions_infobox_sidecar_and_article_purity() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "infobox.json" in readme
    assert "      infobox.json" in readme
    assert "article.md" in readme
    assert "page_type" in readme


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


def test_readme_uses_people_output_contract_for_single_and_batch_examples() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "output/\n  people/" in readme
    assert "output/people/<slug>/" in readme
    assert "person/default/" not in readme


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
        assert all("url" in payload for payload in payloads)
        assert all(payload.get("page_type", "person") == "person" for payload in payloads)
        assert all(payload.get("output_group") == output_group for payload in payloads)
        assert all(payload.get("slug") for payload in payloads)


def test_readme_positions_project_as_general_wikipedia_converter() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "通用 Wikipedia -> Markdown 转换工具" in readme
    assert "并不只限于人物页" in readme
    assert "page_type" in readme
