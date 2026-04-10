from pathlib import Path

import pytest

from wiki2md.errors import WriteError
from wiki2md.output_paths import (
    canonical_people_relative_output_dir,
    ensure_canonical_people_output_dir,
)


def test_canonical_people_relative_output_dir_uses_people_root() -> None:
    assert canonical_people_relative_output_dir("andrej-karpathy") == Path(
        "people/andrej-karpathy"
    )


def test_ensure_canonical_people_output_dir_migrates_single_legacy_directory(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    legacy_dir = output_root / "person" / "default" / "andrej-karpathy"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "article.md").write_text("# Legacy\n", encoding="utf-8")

    final_dir = ensure_canonical_people_output_dir(
        output_root,
        Path("people/andrej-karpathy"),
    )

    assert final_dir == output_root / "people" / "andrej-karpathy"
    assert final_dir.exists()
    assert (final_dir / "article.md").read_text(encoding="utf-8") == "# Legacy\n"
    assert not legacy_dir.exists()


def test_ensure_canonical_people_output_dir_rejects_multiple_legacy_directories(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    (output_root / "person" / "default" / "andrej-karpathy").mkdir(parents=True)
    (output_root / "person" / "people-ai" / "andrej-karpathy").mkdir(parents=True)

    with pytest.raises(WriteError, match="Multiple legacy output directories"):
        ensure_canonical_people_output_dir(
            output_root,
            Path("people/andrej-karpathy"),
        )
