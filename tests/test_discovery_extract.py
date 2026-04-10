import importlib

import pytest


def _load_discovery_extract():
    try:
        return importlib.import_module("wiki2md.discovery_extract")
    except ModuleNotFoundError as exc:
        pytest.fail(str(exc))


def test_extract_person_candidates_collects_from_prose_lists_and_tables() -> None:
    discovery_extract = _load_discovery_extract()

    html = """
    <html>
      <body>
        <p>
          The first laureates included
          <a href="/wiki/John_von_Neumann">John von Neumann</a>
          and <a href="/wiki/Alan_Turing">Alan Turing</a>.
        </p>
        <ul>
          <li><a href="/wiki/Grace_Hopper">Grace Hopper</a></li>
        </ul>
        <table>
          <tr><td><a href="/wiki/Donald_Knuth">Donald Knuth</a></td></tr>
        </table>
      </body>
    </html>
    """

    candidates = discovery_extract.extract_person_candidates(
        html,
        source_url="https://en.wikipedia.org/wiki/Turing_Award",
        depth=0,
    )

    assert [candidate.slug for candidate in candidates] == [
        "john-von-neumann",
        "alan-turing",
        "grace-hopper",
        "donald-knuth",
    ]
    assert all(candidate.depth == 0 for candidate in candidates)


def test_extract_person_candidates_excludes_namespaces_fragments_and_non_person_noise() -> None:
    discovery_extract = _load_discovery_extract()

    html = """
    <html>
      <body>
        <p>
          <a href="/wiki/Mathematics">Mathematics</a>
          <a href="/wiki/Bell_Labs">Bell Labs</a>
          <a href="/wiki/Main_Page">Main page</a>
          <a href="/wiki/Portal:Current_events">Current events</a>
          <a href="/wiki/JSTOR_(identifier)">JSTOR (identifier)</a>
          <a href="https://zh.wikipedia.org/wiki/%E5%9B%BE%E7%81%B5%E5%A5%96">中文</a>
          <a href="/wiki/John_Bardeen">John Bardeen</a>
          <a href="/wiki/Category:Physics">Physics category</a>
          <a href="/wiki/Talk:John_Bardeen">Talk</a>
          <a href="#cite_note-1">[1]</a>
          <a href="/wiki/Help:Contents">Help</a>
          <a href="/wiki/Special:Random">Random</a>
          <a href="/wiki/File:Portrait.jpg">portrait</a>
          <a href="/wiki/Jane_Doe">v</a>
        </p>
      </body>
    </html>
    """

    candidates = discovery_extract.extract_person_candidates(
        html,
        source_url="https://en.wikipedia.org/wiki/Nobel_Prize_in_Physics",
        depth=0,
    )

    assert [candidate.slug for candidate in candidates] == ["john-bardeen"]


def test_extract_expansion_links_keeps_relevant_list_pages_and_filters_template_noise() -> None:
    discovery_extract = _load_discovery_extract()

    html = """
    <html>
      <body>
        <p>
          <a href="/wiki/List_of_Turing_Award_laureates">List of Turing Award laureates</a>
          <a href="/wiki/Laureates_by_year">Laureates by year</a>
          <a href="/wiki/Turing_Award#Recipients">Recipients</a>
          <a href="/wiki/Template:Turing_Award">Template</a>
          <a href="/wiki/Category:Computer_science_awards">Category</a>
        </p>
      </body>
    </html>
    """

    links = discovery_extract.extract_expansion_links(
        html,
        source_url="https://en.wikipedia.org/wiki/Turing_Award",
    )

    assert links == [
        "https://en.wikipedia.org/wiki/List_of_Turing_Award_laureates",
        "https://en.wikipedia.org/wiki/Laureates_by_year",
    ]
