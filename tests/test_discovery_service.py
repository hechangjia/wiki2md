import json
from pathlib import Path

from wiki2md.discovery_service import run_discovery


class FakeDiscoveryClient:
    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent

    def __enter__(self) -> "FakeDiscoveryClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def fetch_html_url(self, url: str) -> str:
        html_by_url = {
            "https://en.wikipedia.org/wiki/Turing_Award": """
                <html><body>
                  <p>
                    <a href="/wiki/Association_for_Computing_Machinery">
                      Association for Computing Machinery
                    </a>
                    <a href="/wiki/Donald_Knuth">Donald Knuth</a>
                    <a href="/wiki/Alan_Turing">Alan Turing</a>
                    <a href="/wiki/ALGOL">ALGOL</a>
                  </p>
                </body></html>
            """
        }
        return html_by_url[url]

    def fetch_page_summary(self, url: str) -> dict[str, str]:
        return {
            "https://en.wikipedia.org/wiki/Association_for_Computing_Machinery": {
                "description": "International Society for Computing",
            },
            "https://en.wikipedia.org/wiki/Donald_Knuth": {
                "description": "American computer scientist and mathematician (born 1938)",
            },
            "https://en.wikipedia.org/wiki/Alan_Turing": {
                "description": "English computer scientist (1912–1954)",
            },
            "https://en.wikipedia.org/wiki/ALGOL": {
                "description": "Family of programming languages",
            },
        }[url]


def test_run_discovery_filters_manifest_to_people_using_summary_descriptions(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("wiki2md.discovery_service.MediaWikiClient", FakeDiscoveryClient)

    bundle_dir = run_discovery(
        "turing-award",
        output_root=tmp_path / "output",
        user_agent="wiki2md-test-bot/0.1 (2136414704@qq.com)",
    )

    rows = [
        json.loads(line)
        for line in (bundle_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert [row["slug"] for row in rows] == ["donald-knuth", "alan-turing"]
