from wiki2md.discovery_models import DiscoverySource
from wiki2md.urls import resolve_wikipedia_url, slugify_title

PRESET_SOURCES = {
    "turing-award": {
        "url": "https://en.wikipedia.org/wiki/Turing_Award",
        "tags": ["award", "computer-science", "turing-award"],
        "output_group": "turing-award",
    },
    "fields-medal": {
        "url": "https://en.wikipedia.org/wiki/Fields_Medal",
        "tags": ["award", "mathematics", "fields-medal"],
        "output_group": "fields-medal",
    },
    "nobel-physics": {
        "url": "https://en.wikipedia.org/wiki/Nobel_Prize_in_Physics",
        "tags": ["award", "physics", "nobel-physics"],
        "output_group": "nobel-physics",
    },
}

_TITLE_TAG_HINTS = (
    (("turing", "award"), ["award", "computer-science", "turing-award"]),
    (("fields", "medal"), ["award", "mathematics", "fields-medal"]),
    (("nobel", "physics"), ["award", "physics", "nobel-physics"]),
)


def _title_to_source_title(title: str) -> str:
    return title.replace("_", " ")


def derive_output_group(title: str) -> str:
    lowered = title.casefold().replace("_", " ")
    if "turing" in lowered and "award" in lowered:
        return "turing-award"
    if "fields" in lowered and "medal" in lowered:
        return "fields-medal"
    if "nobel" in lowered and "physics" in lowered:
        return "nobel-physics"
    return slugify_title(title)


def derive_tags(title: str) -> list[str]:
    lowered = title.casefold().replace("_", " ")
    for parts, tags in _TITLE_TAG_HINTS:
        if all(part in lowered for part in parts):
            return tags
    tags = [slugify_title(title)]
    if any(keyword in lowered for keyword in ("award", "medal", "prize")):
        return ["award", *tags]
    return tags


def resolve_discovery_source(source: str) -> DiscoverySource:
    preset = PRESET_SOURCES.get(source)
    if preset is not None:
        resolution = resolve_wikipedia_url(preset["url"])
        return DiscoverySource(
            kind="preset",
            resolution=resolution,
            slug=source,
            source_title=_title_to_source_title(resolution.title),
            output_group=preset["output_group"],
            tags=list(preset["tags"]),
        )

    resolution = resolve_wikipedia_url(source)
    derived_output_group = derive_output_group(resolution.title)
    return DiscoverySource(
        kind="url",
        resolution=resolution,
        slug=derived_output_group,
        source_title=_title_to_source_title(resolution.title),
        output_group=derived_output_group,
        tags=derive_tags(resolution.title),
    )
