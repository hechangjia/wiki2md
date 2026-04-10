from pathlib import Path

from wiki2md.errors import WriteError
from wiki2md.writer import normalize_relative_output_dir


def canonical_people_relative_output_dir(slug: str) -> Path:
    return normalize_relative_output_dir(Path("people") / slug)


def _legacy_people_candidates(output_root: Path, slug: str) -> list[Path]:
    legacy_root = output_root / "person"
    if not legacy_root.exists():
        return []
    return sorted(
        candidate for candidate in legacy_root.glob(f"*/{slug}") if candidate.is_dir()
    )


def ensure_canonical_people_output_dir(output_root: Path, relative_output_dir: Path) -> Path:
    relative_output_dir = normalize_relative_output_dir(relative_output_dir)
    final_dir = output_root / relative_output_dir

    if relative_output_dir.parts[:1] != ("people",):
        return final_dir
    if final_dir.exists():
        return final_dir

    slug = relative_output_dir.name
    legacy_candidates = _legacy_people_candidates(output_root, slug)
    if not legacy_candidates:
        return final_dir
    if len(legacy_candidates) > 1:
        candidates = ", ".join(
            str(path.relative_to(output_root)) for path in legacy_candidates
        )
        raise WriteError(
            f"Multiple legacy output directories found for slug '{slug}': {candidates}"
        )

    legacy_dir = legacy_candidates[0]
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    legacy_dir.replace(final_dir)

    legacy_parent = legacy_dir.parent
    if legacy_parent.exists() and not any(legacy_parent.iterdir()):
        legacy_parent.rmdir()

    legacy_root = output_root / "person"
    if legacy_root.exists() and not any(legacy_root.iterdir()):
        legacy_root.rmdir()

    return final_dir
