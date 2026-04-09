from pathlib import Path

from wiki2md.document import Document, ParagraphBlock
from wiki2md.models import ConversionResult
from wiki2md.service import Wiki2MdService


class FakeClient:
    user_agent = "wiki2md-test-bot/0.1 (2136414704@qq.com)"

    def fetch_article(self, resolution):
        from wiki2md.models import FetchedArticle

        return FetchedArticle(
            resolution=resolution,
            canonical_title="Andrej Karpathy",
            pageid=12345,
            revid=67890,
            html="<html></html>",
            media=[],
        )


def test_convert_url_orchestrates_pipeline(monkeypatch, tmp_path: Path) -> None:
    service = Wiki2MdService(client=FakeClient(), output_root=tmp_path / "output")

    monkeypatch.setattr(
        "wiki2md.service.normalize_article",
        lambda article: Document(
            title="Andrej Karpathy",
            summary=["Andrej Karpathy is a computer scientist."],
            blocks=[ParagraphBlock(text="Karpathy worked at OpenAI.")],
            references=[],
        ),
    )
    monkeypatch.setattr("wiki2md.service.select_assets", lambda document, media: [])
    monkeypatch.setattr(
        "wiki2md.service.download_assets",
        lambda assets, destination, user_agent: None,
    )
    monkeypatch.setattr(
        "wiki2md.service.render_markdown",
        lambda document, metadata, asset_map: "# Andrej Karpathy\n",
    )

    result = service.convert_url(
        "https://en.wikipedia.org/wiki/Andrej_Karpathy",
        overwrite=False,
    )

    assert isinstance(result, ConversionResult)
    assert Path(result.article_path).exists()
    assert result.asset_count == 0
