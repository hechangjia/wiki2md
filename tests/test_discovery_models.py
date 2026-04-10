import importlib

import pytest


def _load_discovery_models():
    try:
        return importlib.import_module("wiki2md.discovery_models")
    except ModuleNotFoundError as exc:
        pytest.fail(str(exc))


def _load_discovery_presets():
    try:
        return importlib.import_module("wiki2md.discovery_presets")
    except ModuleNotFoundError as exc:
        pytest.fail(str(exc))


def test_resolve_discovery_source_supports_builtin_presets() -> None:
    _load_discovery_models()
    discovery_presets = _load_discovery_presets()

    source = discovery_presets.resolve_discovery_source("turing-award")

    assert source.kind == "preset"
    assert source.slug == "turing-award"
    assert source.output_group == "turing-award"
    assert source.page_type == "person"
    assert source.resolution.normalized_url == "https://en.wikipedia.org/wiki/Turing_Award"
    assert source.tags == ["award", "computer-science", "turing-award"]


def test_resolve_discovery_source_derives_defaults_from_url() -> None:
    discovery_models = _load_discovery_models()
    discovery_presets = _load_discovery_presets()

    source = discovery_presets.resolve_discovery_source(
        "https://en.wikipedia.org/wiki/Fields_Medal"
    )

    assert source == discovery_models.DiscoverySource(
        kind="url",
        slug="fields-medal",
        source_title="Fields Medal",
        output_group="fields-medal",
        page_type="person",
        tags=["award", "mathematics", "fields-medal"],
        resolution=source.resolution,
    )


def test_select_candidates_caps_final_selection_at_37_and_prefers_depth_zero() -> None:
    discovery_models = _load_discovery_models()

    candidates = [
        discovery_models.DiscoveryCandidate(
            url=f"https://en.wikipedia.org/wiki/Depth_Zero_{index}",
            title=f"Depth Zero {index}",
            slug=f"depth-zero-{index}",
            anchor_text=f"Depth Zero {index}",
            source_page="https://en.wikipedia.org/wiki/Turing_Award",
            depth=0,
            frequency=1,
        )
        for index in range(30)
    ] + [
        discovery_models.DiscoveryCandidate(
            url=f"https://en.wikipedia.org/wiki/Depth_One_{index}",
            title=f"Depth One {index}",
            slug=f"depth-one-{index}",
            anchor_text=f"Depth One {index}",
            source_page="https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates",
            depth=1,
            frequency=10 - (index % 3),
        )
        for index in range(20)
    ]

    selected = discovery_models.select_candidates(candidates, max_people=37)

    assert len(selected) == 37
    assert all(candidate.depth == 0 for candidate in selected[:30])
    assert all(candidate.depth in {0, 1} for candidate in selected)
    assert sum(candidate.depth == 1 for candidate in selected) == 7


def test_select_candidates_deduplicates_by_url_and_merges_frequency() -> None:
    discovery_models = _load_discovery_models()

    candidates = [
        discovery_models.DiscoveryCandidate(
            url="https://en.wikipedia.org/wiki/John_von_Neumann",
            title="John von Neumann",
            slug="john-von-neumann",
            anchor_text="John von Neumann",
            source_page="https://en.wikipedia.org/wiki/Turing_Award",
            depth=0,
            frequency=1,
        ),
        discovery_models.DiscoveryCandidate(
            url="https://en.wikipedia.org/wiki/John_von_Neumann",
            title="John von Neumann",
            slug="john-von-neumann",
            anchor_text="von Neumann",
            source_page="https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates",
            depth=1,
            frequency=3,
        ),
    ]

    selected = discovery_models.select_candidates(candidates, max_people=37)

    assert len(selected) == 1
    assert selected[0].url == "https://en.wikipedia.org/wiki/John_von_Neumann"
    assert selected[0].depth == 0
    assert selected[0].frequency == 4
