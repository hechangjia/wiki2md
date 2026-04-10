from wiki2md.document import SectionEvidence


def render_sources_markdown(title: str, sections: list[SectionEvidence]) -> str:
    lines = [f"# Sources for {title}", ""]

    for section in sections:
        lines.append(f"{'#' * max(section.level, 2)} {section.heading}")
        lines.append("")

        if not section.sources:
            lines.append("_No explicit sources mapped._")
            lines.append("")
            continue

        for source in section.sources:
            line = f"- {source.text}"
            if source.primary_url:
                line += f" ({source.primary_url})"
            if source.link_kinds:
                line += f" [{', '.join(source.link_kinds)}]"
            lines.append(line)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
