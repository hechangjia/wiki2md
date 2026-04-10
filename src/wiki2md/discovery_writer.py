import json
from pathlib import Path

from wiki2md.discovery_models import DiscoveryRun


def _bundle_dir(run: DiscoveryRun, output_root: Path) -> Path:
    return output_root / "discovery" / run.source.slug


def _render_manifest_jsonl(run: DiscoveryRun) -> str:
    rows = []
    for candidate in run.selected_candidates:
        rows.append(
            json.dumps(
                {
                    "url": candidate.url,
                    "page_type": run.source.page_type,
                    "slug": candidate.slug,
                    "tags": run.source.tags,
                    "output_group": run.source.output_group,
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(rows) + ("\n" if rows else "")


def _render_index_markdown(run: DiscoveryRun) -> str:
    manifest_path = f"output/discovery/{run.source.slug}/manifest.jsonl"
    lines = [
        f"# {run.source.source_title}",
        "",
        f"Source: {run.source.resolution.normalized_url}",
        f"Language: {run.source.resolution.lang}",
        "Discovered: "
        f"{len(run.selected_candidates)} selected / {len(run.candidates)} total candidates",
        "",
        "## Selected People",
        "",
    ]

    for candidate in run.selected_candidates:
        lines.append(
            f"- [{candidate.title}]({candidate.url}) | depth={candidate.depth} | "
            f"reason={candidate.selection_reason or 'selected'}"
        )

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            f"`wiki2md batch {manifest_path} --output-dir output`",
            "",
        ]
    )
    return "\n".join(lines)


def _render_discovery_json(run: DiscoveryRun) -> str:
    payload = {
        "source_url": run.source.resolution.normalized_url,
        "source_title": run.source.source_title,
        "source_lang": run.source.resolution.lang,
        "discovery_method": "depth0-depth1",
        "expanded_pages": run.expanded_pages,
        "selected_count": len(run.selected_candidates),
        "configured_limits": {"max_people": run.max_people},
        "candidates": [candidate.model_dump(mode="json") for candidate in run.candidates],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_discovery_bundle(run: DiscoveryRun, *, output_root: Path) -> Path:
    bundle_dir = _bundle_dir(run, output_root)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    (bundle_dir / "manifest.jsonl").write_text(_render_manifest_jsonl(run), encoding="utf-8")
    (bundle_dir / "index.md").write_text(_render_index_markdown(run), encoding="utf-8")
    (bundle_dir / "discovery.json").write_text(_render_discovery_json(run), encoding="utf-8")

    return bundle_dir
