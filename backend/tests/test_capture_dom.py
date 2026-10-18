"""DOM tests for extension/content.js capture logic.

Runs the real content script inside Chromium against fixture pages and
exercises getQuestionContext()/getPageText(). Skipped when a Playwright
browser is not installed, so `make test` still works without one.
"""
import json
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


@pytest.fixture
def stub_api():
    """Intercept the real request so we can assert on what was sent."""
    calls = []

    def _stub(page, response=None, path="**/api/extension/ask", status=200):
        payload = json.dumps(response or {"response": "stub reply"})

        def handler(route):
            calls.append({
                "url": route.request.url,
                "body": route.request.post_data_json,
            })
            route.fulfill(status=status, content_type="application/json", body=payload)

        page.route(path, handler)
        return calls

    return _stub


def test_mcq_action_sends_captured_stem_and_options(load_page, stub_api):
    page = load_page(MCQ_PAGE)
    calls = stub_api(page)
    page.evaluate("doAction('mcq-explain')")

    assert len(calls) == 1
    body = calls[0]["body"]
    assert calls[0]["url"].endswith("/api/extension/ask")
    assert body["action"] == "mcq-explain"
    assert body["options"] == ["Stack", "Queue", "Tree"]
    assert "Which data structure is FIFO?" in body["text"]
    assert body["context"]
    # Spec A step 4: no code context for MCQ
    assert "code_context" not in body


def test_result_shows_what_was_captured(load_page, stub_api):
    page = load_page(MCQ_PAGE)
    stub_api(page)
    page.evaluate("doAction('mcq-explain')")

    banner = page.inner_text(".alc-capture")
    assert "Using:" in banner
    assert "detected question" in banner


def test_preview_toggle_reveals_captured_text(load_page, stub_api):
    page = load_page(MCQ_PAGE)
    stub_api(page)
    page.evaluate("previewCapture = true")
    page.evaluate("doAction('mcq-explain')")

    preview = page.inner_text(".alc-capture-preview")
    assert "Which data structure is FIFO?" in preview
    assert "A. Stack" in preview


def test_coding_help_still_sends_code_context(browser, tmp_path, stub_api):
    html = """
    <html><head><title>Code page</title></head><body>
    <p>Implement two_sum(nums, target).</p>
    <pre><code class="language-python">def two_sum(nums, target):
    pass</code></pre>
    </body></html>
    """
    path = tmp_path / "code.html"
    path.write_text(html, encoding="utf-8")
    page = browser.new_page()
    page.goto(path.as_uri())
    page.add_script_tag(path=str(CONTENT_JS))

    calls = stub_api(page)
    page.evaluate("doAction('coding-help')")

    assert "two_sum" in calls[0]["body"]["code_context"]


def test_explain_action_never_sends_code_context(load_page, stub_api):
    page = load_page(PLAIN_PAGE)
    calls = stub_api(page)
    page.evaluate("doAction('explain')")

    assert "code_context" not in calls[0]["body"]


def test_model_failure_shows_retry_message(load_page, stub_api):
    page = load_page(MCQ_PAGE)
    stub_api(page, response={"detail": "Model failed, retry"}, status=502)
    page.evaluate("doAction('mcq-explain')")

    assert "Model failed, retry" in page.inner_text("#alc-content")


def test_question_fingerprint_tracks_detected_mcq(load_page):
    quiz = load_page(MCQ_PAGE)
    assert quiz.evaluate("questionFingerprint()").startswith("mcq:")

    plain = load_page(PLAIN_PAGE)
    assert plain.evaluate("questionFingerprint()") == ""


def test_widget_mutations_are_ignored(load_page):
    page = load_page(PLAIN_PAGE)
    assert page.evaluate(
        "isWidgetMutation({ target: document.getElementById('alc-toggle') })"
    ) is True
    assert page.evaluate(
        "isWidgetMutation({ target: document.body })"
    ) is False


def test_ordinary_page_change_keeps_chat_history(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        chatHistory = [{role: 'user', content: 'keep me'}];
        lastUrl = location.href;
        lastQuestionSignature = '';
    """)
    page.evaluate("checkPage()")

    assert page.evaluate("chatHistory.length") == 1
    assert page.evaluate("document.querySelectorAll('.alc-chat-notice').length") == 0


def test_detected_question_change_resets_chat_with_notice(load_page):
    page = load_page(MCQ_PAGE)
    page.evaluate("""
        chatHistory = [{role: 'user', content: 'stale'}];
        lastUrl = location.href;
        lastQuestionSignature = 'stale-signature';
    """)
    page.evaluate("checkPage()")

    assert page.evaluate("chatHistory.length") == 0
    assert "New question detected" in page.inner_text(".alc-chat-notice")


def test_url_change_resets_chat_with_notice(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        chatHistory = [{role: 'user', content: 'old page'}];
        lastUrl = 'https://example.com/somewhere-else';
    """)
    page.evaluate("checkPage()")

    assert page.evaluate("chatHistory.length") == 0
    assert "New page detected" in page.inner_text(".alc-chat-notice")



