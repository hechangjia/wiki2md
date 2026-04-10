import re
from pathlib import Path

from wiki2md.client import MediaWikiClient
from wiki2md.discovery_extract import extract_expansion_links, extract_person_candidates
from wiki2md.discovery_models import DiscoveryRun, rank_candidates
from wiki2md.discovery_presets import resolve_discovery_source
from wiki2md.discovery_writer import write_discovery_bundle

DEFAULT_DISCOVERY_EXPANSIONS = 5
DEFAULT_DISCOVERY_MAX_PEOPLE = 37
_PERSON_DESCRIPTION_RE = re.compile(r"\((?:born\s+\d{4}|\d{4}[–-]\d{4}|\d{4}[–-]present)")
_PERSON_DESCRIPTION_ZH_RE = re.compile(r"[（(](?:生于|生於|\d{4}年)")


def _collect_candidates(
    client: MediaWikiClient,
    source_url: str,
    *,
    max_expansions: int = DEFAULT_DISCOVERY_EXPANSIONS,
) -> tuple[list, list[str]]:
    source_html = client.fetch_html_url(source_url)
    candidates = extract_person_candidates(source_html, source_url=source_url, depth=0)

    expansion_links = extract_expansion_links(source_html, source_url=source_url)[:max_expansions]
    for expansion_url in expansion_links:
        try:
            expansion_html = client.fetch_html_url(expansion_url)
        except Exception:
            continue
        candidates.extend(
            extract_person_candidates(
                expansion_html,
                source_url=expansion_url,
                depth=1,
            )
        )

    return candidates, expansion_links


def _looks_like_person_description(description: str | None) -> bool:
    if not description:
        return False

    normalized = description.casefold()
    return bool(
        _PERSON_DESCRIPTION_RE.search(normalized)
        or _PERSON_DESCRIPTION_ZH_RE.search(description)
    )


def _select_person_candidates(
    client: MediaWikiClient,
    candidates: list,
    *,
    max_people: int,
) -> list:
    selected = []

    for candidate in rank_candidates(candidates):
        try:
            summary = client.fetch_page_summary(candidate.url)
        except Exception:
            candidate.rejected_reason = "summary-fetch-failed"
            continue

        description = summary.get("description")
        if not isinstance(description, str) or not _looks_like_person_description(description):
            candidate.rejected_reason = "summary-not-person"
            continue

        candidate.selection_reason = (
            "depth0-direct-link" if candidate.depth == 0 else "depth1-ranked-fill"
        )
        selected.append(candidate)
        if len(selected) >= max_people:
            break

    return selected


def run_discovery(
    source: str,
    *,
    output_root: Path,
    user_agent: str = "wiki2md-bot/0.1 (2136414704@qq.com)",
) -> Path:
    discovery_source = resolve_discovery_source(source)

    with MediaWikiClient(user_agent=user_agent) as client:
        candidates, expansion_links = _collect_candidates(
            client,
            discovery_source.resolution.normalized_url,
        )
        selected_candidates = _select_person_candidates(
            client,
            candidates,
            max_people=DEFAULT_DISCOVERY_MAX_PEOPLE,
        )

    run = DiscoveryRun(
        source=discovery_source,
        candidates=candidates,
        selected_candidates=selected_candidates,
        expanded_pages=expansion_links,
        max_people=DEFAULT_DISCOVERY_MAX_PEOPLE,
    )
    return write_discovery_bundle(run, output_root=output_root)
