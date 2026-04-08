import pytest

from wiki2md.errors import InvalidWikipediaUrlError, UnsupportedPageError
from wiki2md.urls import resolve_wikipedia_url


def test_resolve_english_article_url() -> None:
    result = resolve_wikipedia_url("https://en.wikipedia.org/wiki/Andrej_Karpathy")

    assert result.lang == "en"
    assert result.title == "Andrej_Karpathy"
    assert result.slug == "andrej-karpathy"
    assert result.normalized_url.endswith("/wiki/Andrej_Karpathy")


def test_resolve_chinese_article_url() -> None:
    result = resolve_wikipedia_url(
        "https://zh.wikipedia.org/wiki/%E8%89%BE%E4%BC%A6%C2%B7%E5%9B%BE%E7%81%B5"
    )

    assert result.lang == "zh"
    assert result.title == "艾伦·图灵"
    assert result.slug == "艾伦-图灵"


def test_resolve_chinese_article_url_normalizes_title_key() -> None:
    result = resolve_wikipedia_url(
        "https://zh.wikipedia.org/wiki/%E8%89%BE%E4%BC%A6%20%E5%9B%BE%E7%81%B5"
    )

    assert result.lang == "zh"
    assert result.title == "艾伦_图灵"
    assert result.slug == "艾伦-图灵"


def test_reject_non_wikipedia_host() -> None:
    with pytest.raises(InvalidWikipediaUrlError):
        resolve_wikipedia_url("https://example.com/wiki/Andrej_Karpathy")


def test_reject_unsupported_namespace() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://en.wikipedia.org/wiki/Category:Machine_learning")


def test_reject_list_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://en.wikipedia.org/wiki/List_of_computer_scientists")


def test_reject_timeline_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://en.wikipedia.org/wiki/Timeline_of_machine_learning")


def test_reject_disambiguation_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://en.wikipedia.org/wiki/Mercury_(disambiguation)")


def test_reject_chinese_unsupported_namespace() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/分类:机器学习")


def test_reject_traditional_chinese_unsupported_namespace() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/分類:機器學習")


def test_reject_chinese_help_namespace() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/帮助:目录")


def test_reject_traditional_chinese_help_namespace() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/幫助:目錄")


def test_reject_chinese_template_namespace() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/模板:信息框")


def test_reject_chinese_disambiguation_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/艾伦·图灵_(消歧义)")


def test_reject_traditional_chinese_disambiguation_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/艾倫·圖靈_(消歧義)")


def test_reject_chinese_list_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/机器学习列表")


def test_reject_chinese_timeline_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/机器学习时间线")


def test_reject_traditional_chinese_timeline_page() -> None:
    with pytest.raises(UnsupportedPageError):
        resolve_wikipedia_url("https://zh.wikipedia.org/wiki/機器學習時間線")
