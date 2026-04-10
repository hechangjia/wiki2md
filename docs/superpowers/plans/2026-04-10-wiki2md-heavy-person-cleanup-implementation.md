# wiki2md Heavy Person Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten normalization so heavyweight person pages keep article body content while dropping remaining template/navigation residue such as orphan date lines and template-control fragments.

**Architecture:** Keep all behavior changes inside `src/wiki2md/normalize.py`, where HTML candidate blocks are admitted into the document model. Extend the existing structural cleanup with a small set of conservative block-level noise predicates, and lock the behavior down with focused normalization tests plus a live `Elon_Musk` smoke pass.

**Tech Stack:** Python 3.12+, `BeautifulSoup4`, `pytest`, `ruff`, `uv`

---

## File Structure

- `src/wiki2md/normalize.py`: add lightweight block-noise predicates and apply them before paragraphs/lists are appended to `Document`
- `tests/test_normalize.py`: add regressions for orphan date paragraphs, template-control fragments, and preserve-body behavior

### Task 1: Add Failing Regressions For Heavyweight-Page Noise

**Files:**
- Modify: `tests/test_normalize.py`

- [ ] **Step 1: Write the failing test for orphan date-like paragraphs**

Add this test near the existing sidebar regression:

```python
def test_normalize_article_skips_orphan_date_paragraphs() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Elon_Musk",
            normalized_url="https://en.wikipedia.org/wiki/Elon_Musk",
            lang="en",
            title="Elon_Musk",
            slug="elon-musk",
        ),
        canonical_title="Elon Musk",
        html="""
        <html>
          <body>
            <section data-mw-section-id="0">
              <p>Elon Musk is a businessman and entrepreneur.</p>
              <h2>X Corp.</h2>
              <p>April 14, 2022</p>
              <p>Musk offered to acquire Twitter in 2022.</p>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["Elon Musk is a businessman and entrepreneur."]
    assert document.blocks == [
        HeadingBlock(level=2, text="X Corp."),
        ParagraphBlock(text="Musk offered to acquire Twitter in 2022."),
    ]
```

- [ ] **Step 2: Write the failing test for template-control fragments**

Add a second regression that keeps real appendix links but drops template control items:

```python
def test_normalize_article_skips_template_control_fragments() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Elon_Musk",
            normalized_url="https://en.wikipedia.org/wiki/Elon_Musk",
            lang="en",
            title="Elon_Musk",
            slug="elon-musk",
        ),
        canonical_title="Elon Musk",
        html="""
        <html>
          <body>
            <section data-mw-section-id="0">
              <p>Elon Musk is a businessman and entrepreneur.</p>
              <ul>
                <li>v</li>
                <li>t</li>
                <li>e</li>
              </ul>
              <h2>External links</h2>
              <ul>
                <li><a href="https://example.com/profile">Official profile</a></li>
              </ul>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.summary == ["Elon Musk is a businessman and entrepreneur."]
    assert document.blocks == [
        HeadingBlock(level=2, text="External links"),
        ListBlock(
            ordered=False,
            items=[
                ListItem(
                    text="Official profile",
                    href="https://example.com/profile",
                )
            ],
        ),
    ]
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
uv run pytest \
  tests/test_normalize.py::test_normalize_article_skips_orphan_date_paragraphs \
  tests/test_normalize.py::test_normalize_article_skips_template_control_fragments \
  -q
```

Expected: FAIL because `normalize_article()` still treats the date paragraph as normal prose and the `v/t/e` list as a normal list.

- [ ] **Step 4: Commit the failing-test checkpoint**

```bash
git add tests/test_normalize.py
git commit -m "test: cover heavyweight person template noise"
```

### Task 2: Implement Conservative Noise Predicates In Normalization

**Files:**
- Modify: `src/wiki2md/normalize.py`
- Modify: `tests/test_normalize.py`

- [ ] **Step 1: Add helper predicates for heavy-page noise**

Insert focused helpers near the existing text-cleaning helpers:

```python
_MONTH_NAMES = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_TEMPLATE_CONTROL_TEXTS = {"v", "t", "e", "vte"}


def _looks_like_orphan_date(text: str) -> bool:
    normalized = " ".join(text.split()).casefold()
    if not normalized:
        return False
    if "," not in normalized:
        return False
    return any(normalized.startswith(f"{month} ") for month in _MONTH_NAMES)


def _is_template_control_text(text: str) -> bool:
    normalized = re.sub(r"\\s+", "", text).casefold()
    return normalized in _TEMPLATE_CONTROL_TEXTS
```

- [ ] **Step 2: Add paragraph/list admission guards**

Apply the helpers at the point where blocks are appended:

```python
        if node.name == "p":
            text = _clean_prose_text(node)
            if not text or _looks_like_orphan_date(text):
                continue
            if in_lead:
                document.summary.append(text)
            else:
                document.blocks.append(ParagraphBlock(text=text))
```

```python
        elif node.name in {"ul", "ol"} and "references" not in (node.get("class") or []):
            items = []
            for item in node.find_all("li", recursive=False):
                text = _clean_prose_text(item)
                if not text or _is_template_control_text(text):
                    continue
                items.append(
                    ListItem(
                        text=text,
                        href=_extract_list_item_href(item, article, preserve_list_links),
                    )
                )
            if items:
                document.blocks.append(ListBlock(ordered=node.name == "ol", items=items))
```

- [ ] **Step 3: Add a preserve-body regression for ordinary short list items**

Extend `tests/test_normalize.py` with one small protection case so the cleanup does not overreach:

```python
def test_normalize_article_preserves_short_real_list_items() -> None:
    article = FetchedArticle(
        resolution=UrlResolution(
            source_url="https://en.wikipedia.org/wiki/Example",
            normalized_url="https://en.wikipedia.org/wiki/Example",
            lang="en",
            title="Example",
            slug="example",
        ),
        canonical_title="Example",
        html="""
        <html>
          <body>
            <section data-mw-section-id="0">
              <p>Example lead.</p>
              <h2>Career</h2>
              <ul>
                <li>AI</li>
                <li>EVs</li>
              </ul>
            </section>
          </body>
        </html>
        """,
        media=[],
    )

    document = normalize_article(article)

    assert document.blocks == [
        HeadingBlock(level=2, text="Career"),
        ListBlock(
            ordered=False,
            items=[ListItem(text="AI"), ListItem(text="EVs")],
        ),
    ]
```

- [ ] **Step 4: Run the focused normalization suite**

Run:

```bash
uv run pytest tests/test_normalize.py -q
```

Expected: PASS, including the new heavyweight-noise regressions and the short-real-list protection case.

- [ ] **Step 5: Commit the implementation**

```bash
git add src/wiki2md/normalize.py tests/test_normalize.py
git commit -m "fix: filter heavyweight person template residue"
```

### Task 3: Verify End-To-End Behavior On Elon Musk And Project Baselines

**Files:**
- Modify: none

- [ ] **Step 1: Re-run the full automated verification suite**

Run:

```bash
uv run pytest -q
uv run ruff check .
```

Expected:

```text
all tests pass
All checks passed!
```

- [ ] **Step 2: Run a live smoke conversion for `Elon_Musk`**

Run:

```bash
uv run wiki2md convert "https://en.wikipedia.org/wiki/Elon_Musk" --output-dir /tmp/wiki2md-heavy-cleanup --overwrite
```

Expected output path:

```text
/tmp/wiki2md-heavy-cleanup/people/elon-musk/article.md
```

- [ ] **Step 3: Inspect the emitted article for the known noisy fragments**

Run:

```bash
rg -n "Awards and honors|Business career|Texas Institute|^April 14, 2022$|^July 13, 2024$|^December 16, 2022$|^- v$|^- t$|^- e$" \
  /tmp/wiki2md-heavy-cleanup/people/elon-musk/article.md
```

Expected:

```text
no matches for the known template residue patterns
```

- [ ] **Step 4: Commit the verified finish**

```bash
git status --short
```

Expected:

```text
working tree clean
```

No new commit is required in this step if the previous task commit already contains the final code and tests.
