"""DOM tests for extension/content.js capture logic.

Runs the real content script inside Chromium against fixture pages and
exercises getQuestionContext()/getPageText(). Skipped when a Playwright
browser is not installed, so `make test` still works without one.
"""
import pathlib

import pytest

CONTENT_JS = pathlib.Path(__file__).resolve().parents[2] / "extension" / "content.js"

playwright_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_api.sync_playwright


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            instance = p.chromium.launch()
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"chromium unavailable: {exc}")
        yield instance
        instance.close()


@pytest.fixture
def load_page(browser, tmp_path):
    def _load(html: str):
        path = tmp_path / "fixture.html"
        path.write_text(html, encoding="utf-8")
        page = browser.new_page()
        page.goto(path.as_uri())
        page.add_script_tag(path=str(CONTENT_JS))
        return page
    return _load


MCQ_PAGE = """
<html><head><title>Quiz page</title></head><body>
<nav>Site navigation</nav>
<div class="quiz">
  <p class="stem">Which data structure is FIFO?</p>
  <div class="options">
    <label><input type="radio" name="q1" value="a"> A. Stack</label>
    <label><input type="radio" name="q1" value="b"> B. Queue</label>
    <label><input type="radio" name="q1" value="c"> C. Tree</label>
  </div>
</div>
<footer>Footer junk</footer>
</body></html>
"""

PLAIN_PAGE = """
<html><head><title>Lesson page</title></head><body>
<nav>Site navigation</nav>
<main>
  <h1>Recursion</h1>
  <p id="para">Recursion is when a function calls itself with a smaller input.</p>
</main>
<footer>Footer junk</footer>
</body></html>
"""


def test_detects_mcq_group_with_stem_and_options(load_page):
    page = load_page(MCQ_PAGE)
    ctx = page.evaluate("getQuestionContext()")

    assert ctx["source"] == "mcq"
    assert ctx["label"] == "detected question"
    assert ctx["options"] == ["Stack", "Queue", "Tree"]
    assert "Which data structure is FIFO?" in ctx["question_text"]
    assert ctx["page_title"] == "Quiz page"


def test_selection_wins_over_mcq(load_page):
    page = load_page(MCQ_PAGE)
    page.evaluate("""
        const range = document.createRange();
        range.selectNodeContents(document.querySelector('.stem'));
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    """)
    ctx = page.evaluate("getQuestionContext()")

    assert ctx["source"] == "selection"
    assert ctx["options"] == []


def test_cached_selection_survives_collapse(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        const range = document.createRange();
        range.selectNodeContents(document.querySelector('#para'));
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('mouseup'));
        sel.removeAllRanges();
    """)
    ctx = page.evaluate("getQuestionContext()")

    assert ctx["source"] == "selection"
    assert "calls itself" in ctx["question_text"]


def test_stale_selection_is_ignored(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        const range = document.createRange();
        range.selectNodeContents(document.querySelector('#para'));
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('mouseup'));
        sel.removeAllRanges();
        lastSelection.ts = Date.now() - 5 * 60 * 1000;
    """)
    ctx = page.evaluate("getQuestionContext()")

    assert ctx["source"] == "visible"


def test_falls_back_to_visible_text(load_page):
    page = load_page(PLAIN_PAGE)
    ctx = page.evaluate("getQuestionContext()")

    assert ctx["source"] == "visible"
    assert ctx["label"] == "visible text"
    assert "Recursion is when a function calls itself" in ctx["question_text"]
    assert "Site navigation" not in ctx["question_text"]
    assert "Footer junk" not in ctx["question_text"]


def test_get_page_text_excludes_widget_and_chrome(load_page):
    page = load_page(PLAIN_PAGE)
    text = page.evaluate("getPageText()")

    assert "Recursion is when a function calls itself" in text
    assert "ALC Copilot" not in text
    assert "Site navigation" not in text
    assert "Footer junk" not in text


def test_context_lengths_are_capped(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        document.querySelector('#para').textContent = 'x '.repeat(5000);
    """)
    ctx = page.evaluate("getQuestionContext()")

    assert len(ctx["question_text"]) <= 2000
    assert len(ctx["context_text"]) <= 4000


@pytest.mark.parametrize("raw,expected", [
    ("A. Stack", "Stack"),
    ("B) Queue", "Queue"),
    ("(c) Tree", "Tree"),
    ("1. Array", "Array"),
    ("No marker here", "No marker here"),
])
def test_strip_option_marker(load_page, raw, expected):
    page = load_page(PLAIN_PAGE)
    assert page.evaluate("raw => stripOptionMarker(raw)", raw) == expected
