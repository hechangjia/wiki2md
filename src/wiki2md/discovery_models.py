from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wiki2md.models import UrlResolution


class DiscoverySource(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["preset", "url"]
    resolution: UrlResolution
    slug: str
    source_title: str
    output_group: str
    page_type: Literal["person"] = "person"
    tags: list[str] = Field(default_factory=list)


class DiscoveryCandidate(BaseModel):
    url: str
    title: str
    slug: str
    anchor_text: str
    source_page: str
    depth: int
    frequency: int = 1
    score: int = 0
    selection_reason: str | None = None
    rejected_reason: str | None = None


class DiscoveryRun(BaseModel):
    source: DiscoverySource
    candidates: list[DiscoveryCandidate] = Field(default_factory=list)
    selected_candidates: list[DiscoveryCandidate] = Field(default_factory=list)
    expanded_pages: list[str] = Field(default_factory=list)
    max_people: int = 37


def rank_candidates(
    candidates: list[DiscoveryCandidate],
) -> list[DiscoveryCandidate]:
    merged: dict[str, DiscoveryCandidate] = {}

    for candidate in candidates:
        existing = merged.get(candidate.url)
        if existing is None:
            merged[candidate.url] = candidate.model_copy(deep=True)
            continue

        existing.frequency += candidate.frequency
        existing.score += candidate.score
        if candidate.depth < existing.depth:
            existing.depth = candidate.depth
            existing.anchor_text = candidate.anchor_text
            existing.source_page = candidate.source_page

    ranked = sorted(
        merged.values(),
        key=lambda candidate: (
            candidate.depth,
            -candidate.frequency,
        ),
    )

    return ranked


def select_candidates(
    candidates: list[DiscoveryCandidate],
    *,
    max_people: int = 37,
) -> list[DiscoveryCandidate]:
    ranked = rank_candidates(candidates)

    selected = ranked[:max_people]
    direct_count = sum(candidate.depth == 0 for candidate in selected)

    for index, candidate in enumerate(selected):
        if candidate.depth == 0:
            candidate.selection_reason = "depth0-direct-link"
        elif index >= direct_count:
            candidate.selection_reason = "depth1-ranked-fill"
        else:
            candidate.selection_reason = "depth0-ranked"

    return selected
