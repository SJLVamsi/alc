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


# --- patch 2: capture correctness ----------------------------------------

STYLED_MCQ = """
<html><head><title>Styled quiz</title></head><body>
<div class="quiz">
  <p class="stem">Which data structure is FIFO?</p>
  <label class="opt"><input type="radio" name="q1" value="a" style="display:none"> A. Stack</label>
  <label class="opt"><input type="radio" name="q1" value="b" style="display:none"> B. Queue</label>
</div>
</body></html>
"""

PARTLY_HIDDEN_MCQ = """
<html><head><title>Partly hidden</title></head><body>
<div class="quiz">
  <p class="stem">Which data structure is FIFO?</p>
  <label class="opt"><input type="radio" name="q1" value="a" style="display:none"> A. Stack</label>
  <label class="opt"><input type="radio" name="q1" value="b" style="display:none"> B. Queue</label>
  <label class="opt" style="display:none"><input type="radio" name="q1" value="c"> C. Hidden answer</label>
</div>
</body></html>
"""

HIDDEN_ANSWER_PAGE = """
<html><head><title>Lesson</title></head><body>
<main>
  <h1>Recursion</h1>
  <p id="visible">Recursion calls itself with a smaller input.</p>
  <div style="display:none">Correct answer: B</div>
  <div style="visibility:hidden">Also hidden: C</div>
</main>
</body></html>
"""


def test_hidden_input_with_visible_label_is_detected(load_page):
    page = load_page(STYLED_MCQ)
    ctx = page.evaluate("getQuestionContext()")

    assert ctx["source"] == "mcq"
    assert ctx["options"] == ["Stack", "Queue"]


def test_hidden_option_is_dropped(load_page):
    page = load_page(PARTLY_HIDDEN_MCQ)
    ctx = page.evaluate("getQuestionContext()")

    assert ctx["source"] == "mcq"
    assert ctx["options"] == ["Stack", "Queue"]
    assert "Hidden answer" not in ctx["question_text"]


def test_hidden_text_is_excluded_from_page_text(load_page):
    page = load_page(HIDDEN_ANSWER_PAGE)
    text = page.evaluate("getPageText()")

    assert "Recursion calls itself" in text
    assert "Correct answer" not in text
    assert "Also hidden" not in text


def test_widget_text_is_excluded_from_page_text(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        document.getElementById('alc-widget')
          .insertAdjacentHTML('beforeend', '<span>WIDGET_SENTINEL_XYZ</span>');
    """)
    text = page.evaluate("getPageText()")

    assert "WIDGET_SENTINEL_XYZ" not in text
    assert "Recursion is when a function calls itself" in text


def test_widget_text_is_excluded_from_viewport_text(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        document.getElementById('alc-widget')
          .insertAdjacentHTML('beforeend', '<span>WIDGET_SENTINEL_XYZ</span>');
    """)
    assert "WIDGET_SENTINEL_XYZ" not in page.evaluate("viewportText(3000)")


def test_widget_options_are_not_detected(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        document.getElementById('alc-widget').insertAdjacentHTML('beforeend', `
          <div class="options">
            <span class="option">A. nope</span>
            <span class="option">B. nope</span>
          </div>`);
    """)
    assert page.evaluate("detectMCQGroup()") is None


def test_selection_inside_widget_is_rejected(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        const range = document.createRange();
        range.selectNodeContents(document.getElementById('alc-widget'));
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('mouseup'));
    """)

    assert page.evaluate("currentSelection()") == ""
    assert page.evaluate("getQuestionContext().then(c => c.source)") == "visible"


def test_widget_selection_does_not_overwrite_a_real_one(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        const sel = window.getSelection();
        const real = document.createRange();
        real.selectNodeContents(document.querySelector('#para'));
        sel.removeAllRanges();
        sel.addRange(real);
        document.dispatchEvent(new Event('mouseup'));

        const fake = document.createRange();
        fake.selectNodeContents(document.getElementById('alc-widget'));
        sel.removeAllRanges();
        sel.addRange(fake);
        document.dispatchEvent(new Event('mouseup'));
    """)

    assert "calls itself" in page.evaluate("currentSelection()")


def test_option_group_off_to_the_right_is_not_detected(load_page):
    page = load_page(MCQ_PAGE)
    page.evaluate("""
        const quiz = document.querySelector('.quiz');
        quiz.style.position = 'absolute';
        quiz.style.left = (window.innerWidth + 800) + 'px';
        quiz.style.top = '40px';
    """)

    assert page.evaluate("detectMCQGroup()") is None


def test_offscreen_right_element_is_not_in_viewport(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        const d = document.createElement('div');
        d.id = 'offscreen';
        d.textContent = 'OFFSCREEN RIGHT';
        d.style.position = 'absolute';
        d.style.left = (window.innerWidth + 500) + 'px';
        d.style.top = '50px';
        document.body.appendChild(d);
    """)

    assert page.evaluate("inViewport(document.getElementById('offscreen'))") is False
    assert "OFFSCREEN RIGHT" not in page.evaluate("viewportText(3000)")


def test_relative_offscreen_left_element_is_not_in_viewport(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        const d = document.createElement('div');
        d.id = 'farleft';
        d.textContent = 'FAR LEFT';
        d.style.position = 'absolute';
        d.style.left = '-9999px';
        d.style.top = '50px';
        document.body.appendChild(d);
    """)

    assert page.evaluate("inViewport(document.getElementById('farleft'))") is False


def _long_page(paragraphs=400):
    body = "\n".join(
        f"<p>Paragraph {i} explains recursion and iteration in some detail.</p>"
        for i in range(paragraphs)
    )
    return (
        "<html><head><title>Long lesson</title></head><body>"
        f"<main><h1>Recursion</h1>{body}</main></body></html>"
    )


def test_mcq_explain_without_options_sends_full_page_text(load_page, stub_api):
    page = load_page(_long_page())
    calls = stub_api(page)
    page.evaluate("doAction('mcq-explain')")

    body = calls[0]["body"]
    assert "options" not in body
    # far beyond the 4000-char viewport budget, up to the 60000 cap
    assert len(body["context"]) > 4000
    assert "Paragraph 399" in body["context"]


def test_explain_still_uses_the_short_viewport_budget(load_page, stub_api):
    page = load_page(_long_page())
    calls = stub_api(page)
    page.evaluate("doAction('explain')")

    assert len(calls[0]["body"]["context"]) <= 4000


# --- patch 2: watcher correctness ----------------------------------------

def _select_para(page, selector="#para"):
    page.evaluate(
        """sel => {
            const range = document.createRange();
            range.selectNodeContents(document.querySelector(sel));
            const s = window.getSelection();
            s.removeAllRanges();
            s.addRange(range);
            document.dispatchEvent(new Event('mouseup'));
        }""",
        selector,
    )


def test_fingerprint_ignores_selection(load_page):
    page = load_page(MCQ_PAGE)
    before = page.evaluate("questionFingerprint()")
    _select_para(page, ".stem")
    after = page.evaluate("questionFingerprint()")

    assert before.startswith("mcq:")
    assert before == after


def test_chat_survives_selection_change_and_expiry(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("""
        chatHistory = [{role: 'user', content: 'keep me'}];
        lastUrl = location.href;
        lastQuestionSignature = questionFingerprint();
    """)

    _select_para(page)
    page.evaluate("checkPage()")
    assert page.evaluate("chatHistory.length") == 1

    # selection ages out
    page.evaluate("lastSelection.ts = 0; checkPage()")
    assert page.evaluate("chatHistory.length") == 1
    assert page.evaluate("document.querySelectorAll('.alc-chat-notice').length") == 0


def test_old_selection_does_not_cross_urls(load_page):
    page = load_page(PLAIN_PAGE)
    _select_para(page)
    page.evaluate("window.getSelection().removeAllRanges()")
    assert page.evaluate("currentSelection()") != ""

    page.evaluate("lastUrl = 'https://example.com/elsewhere'; checkPage()")

    assert page.evaluate("currentSelection()") == ""
    assert page.evaluate("lastSelection.text") == ""


def test_existing_mcq_does_not_reset_on_first_ordinary_mutation(load_page):
    page = load_page(MCQ_PAGE)
    # the watcher seeded the signature when it started
    assert page.evaluate("lastQuestionSignature").startswith("mcq:")

    page.evaluate("chatHistory = [{role: 'user', content: 'keep me'}]")
    page.evaluate("checkPage()")

    assert page.evaluate("chatHistory.length") == 1
    assert page.evaluate("document.querySelectorAll('.alc-chat-notice').length") == 0


def test_question_change_while_typing_is_deferred_not_lost(load_page):
    page = load_page(MCQ_PAGE)
    typing = page.evaluate("""() => {
        chatHistory = [{role: 'user', content: 'keep me'}];
        lastUrl = location.href;
        lastQuestionSignature = 'stale-signature';
        document.getElementById('alc-panel').classList.add('open');
        switchTab('chat');
        const input = document.getElementById('alc-chat-input');
        input.focus();
        input.value = 'half typed';
        return document.activeElement === input;
    }""")
    if not typing:
        pytest.skip("could not focus the chat input in this environment")

    page.evaluate("checkPage()")

    # deferred: the transition is still pending, nothing was thrown away
    assert page.evaluate("chatHistory.length") == 1
    assert page.evaluate("lastQuestionSignature") == "stale-signature"

    page.evaluate("""
        const input = document.getElementById('alc-chat-input');
        input.value = '';
        input.blur();
    """)
    page.evaluate("checkPage()")

    assert page.evaluate("chatHistory.length") == 0
    assert "New question detected" in page.inner_text(".alc-chat-notice")


def test_watch_deadline_forces_a_check_despite_mutation_churn(load_page):
    page = load_page(MCQ_PAGE)
    page.evaluate("""
        chatHistory = [{role: 'user', content: 'stale'}];
        lastUrl = location.href;
        lastQuestionSignature = 'stale-signature';
        mutationTimer = null;
        watchFirstMutationAt = Date.now() - 10000;
    """)
    page.evaluate("scheduleCheck()")

    # past the max delay it runs at once instead of parking on another timer
    assert page.evaluate("mutationTimer") is None
    assert page.evaluate("watchFirstMutationAt") == 0
    assert page.evaluate("chatHistory.length") == 0


def test_fresh_mutation_schedules_a_debounced_check(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("mutationTimer = null; watchFirstMutationAt = 0;")
    page.evaluate("scheduleCheck()")
    assert page.evaluate("mutationTimer !== null") is True

    page.evaluate("clearTimeout(mutationTimer); mutationTimer = null; watchFirstMutationAt = 0;")


def test_widget_mutations_do_not_schedule_a_check(load_page):
    page = load_page(PLAIN_PAGE)
    page.evaluate("mutationTimer = null; watchFirstMutationAt = 0;")
    page.evaluate("""
        const widget = document.getElementById('alc-widget');
        widget.setAttribute('data-twitch', Date.now());
        widget.appendChild(document.createElement('span'));
    """)
    assert page.evaluate("mutationTimer") is None


def test_mcq_explain_without_options_prefers_full_page_over_viewport(load_page, stub_api):
    page = load_page(_long_page(120))
    calls = stub_api(page)
    page.evaluate("doAction('mcq-explain')")

    body = calls[0]["body"]
    assert "options" not in body
    assert "Paragraph 119" in body["context"]





