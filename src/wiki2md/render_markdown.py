from typing import Iterable

import yaml

from wiki2md.document import (
    Document,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ListItem,
    ParagraphBlock,
)
from wiki2md.models import ArticleMetadata

MAX_REFERENCES = 5


def _render_frontmatter(metadata: ArticleMetadata) -> str:
    payload = {
        "title": metadata.title,
        "source_url": metadata.source_url,
        "source_lang": metadata.source_lang,
        "source_type": metadata.source_type,
        "retrieved_at": metadata.retrieved_at.isoformat(),
        "page_type": metadata.page_type,
        "pageid": metadata.pageid,
        "revid": metadata.revid,
    }
    return f"---\n{yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()}\n---"


def _render_list(items: Iterable[ListItem], ordered: bool) -> list[str]:
    lines = []
    for index, item in enumerate(items, start=1):
        prefix = f"{index}." if ordered else "-"
        content = item.text if item.href is None else f"[{item.text}]({item.href})"
        lines.append(f"{prefix} {content}")
    return lines


def _render_profile(document: Document, metadata: ArticleMetadata) -> list[str]:
    if metadata.page_type != "person":
        return []

    if document.infobox is None or not document.infobox.fields:
        return []

    lines = ["## Profile", ""]
    for field in document.infobox.fields:
        lines.append(f"- {field.label}: {field.text}")
    lines.append("")
    return lines


def render_markdown(
    document: Document,
    metadata: ArticleMetadata,
    asset_map: dict[str, str],
) -> str:
    lines: list[str] = [_render_frontmatter(metadata), "", f"# {document.title}", ""]

    infobox_image_title = (
        document.infobox.image.title
        if document.infobox and document.infobox.image
        else None
    )

    if document.infobox and document.infobox.image:
        relative_path = asset_map.get(document.infobox.image.title) or document.infobox.image.path
        if relative_path:
            lines.append(f"![{document.infobox.image.alt}](./{relative_path})")
            if document.infobox.image.caption:
                lines.append(f"*{document.infobox.image.caption}*")
            lines.append("")

    lines.extend(_render_profile(document, metadata))

    for paragraph in document.summary:
        lines.append(paragraph)
        lines.append("")

    for block in document.blocks:
        if isinstance(block, HeadingBlock):
            lines.append(f"{'#' * block.level} {block.text}")
            lines.append("")
        elif isinstance(block, ParagraphBlock):
            lines.append(block.text)
            lines.append("")
        elif isinstance(block, ListBlock):
            lines.extend(_render_list(block.items, ordered=block.ordered))
            lines.append("")
        elif isinstance(block, ImageBlock):
            if block.role == "infobox" or block.title == infobox_image_title:
                continue
            relative_path = asset_map.get(block.title)
            if relative_path:
                lines.append(f"![{block.alt}](./{relative_path})")
                if block.caption:
                    lines.append(f"*{block.caption}*")
                lines.append("")

    if document.references:
        lines.append("## References")
        lines.append("")
        kept_references = document.references[:MAX_REFERENCES]
        reference_items = [ListItem(text=reference.text) for reference in kept_references]
        lines.extend(_render_list(reference_items, ordered=True))
        omitted = len(document.references) - len(kept_references)
        if omitted > 0:
            lines.append("")
            lines.append(f"_{omitted} additional reference(s) omitted for brevity._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
