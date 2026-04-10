from wiki2md.document import SectionEvidence, SectionEvidenceSource
from wiki2md.render_sources import render_sources_markdown


def test_render_sources_markdown_groups_sources_by_section() -> None:
    markdown = render_sources_markdown(
        title="Andrej Karpathy",
        sections=[
            SectionEvidence(
                section_id="career",
                heading="Career",
                level=2,
                paragraph_count=2,
                reference_ids=["cite_note-12"],
                reference_count=1,
                primary_urls=["https://openai.com/index/example"],
                sources=[
                    SectionEvidenceSource(
                        id="cite_note-12",
                        text="OpenAI biography page.",
                        primary_url="https://openai.com/index/example",
                        link_kinds=["external"],
                    )
                ],
            )
        ],
    )

    assert "# Sources for Andrej Karpathy" in markdown
    assert "## Career" in markdown
    assert "OpenAI biography page." in markdown
    assert "https://openai.com/index/example" in markdown
