"""Integration tests for the streaming chat UI in extension/content.js.

Drives the real content script in Chromium, intercepts /api/page/ask with
Playwright routing, and asserts on both the DOM and the request payloads.
Skipped when no Playwright browser is available.
"""
import json
import pathlib

import pytest

CONTENT_JS = pathlib.Path(__file__).resolve().parents[2] / "extension" / "content.js"

playwright_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_api.sync_playwright

PAGE = """
<html><head><title>Lesson</title></head><body>
<main>
  <h1>Recursion</h1>
  <p id="para">Recursion is when a function calls itself.</p>
</main>
<pre><code class="language-python">def two_sum(nums, target):
    pass</code></pre>
</body></html>
"""

SSE_OK = 'data: {"delta": "ok"}\n\ndata: [DONE]\n\n'


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
def page(browser, tmp_path):
    path = tmp_path / "chat.html"
    path.write_text(PAGE, encoding="utf-8")
    pg = browser.new_page()
    pg.goto(path.as_uri())
    pg.add_script_tag(path=str(CONTENT_JS))
    pg.evaluate("""
        document.getElementById('alc-panel').classList.add('open');
        switchTab('chat');
    """)
    yield pg
    pg.close()


def _sse_body(events):
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"


def _stub_stream(page, events, calls=None):
    body = _sse_body(events)

    def handler(route):
        if calls is not None:
            calls.append(route.request.post_data_json)
        route.fulfill(status=200, content_type="text/event-stream", body=body)

    page.route("**/api/page/ask", handler)
    return calls


def _ask(page, question="hi"):
    page.fill("#alc-chat-input", question)
    page.evaluate("sendChatMessage()")


# --- 3.1 SSE parsing ------------------------------------------------------

def test_sse_parser_reassembles_fragmented_events(page):
    chunks = page.evaluate(r"""() => {
        const seen = [];
        const parser = createSseParser(c => seen.push(c));
        parser.push('data: {"delta":"Hel');
        parser.push('lo"}\n\ndata: {"del');
        parser.push('ta":" world"}\n\n');
        parser.flush();
        return seen;
    }""")

    assert len(chunks) == 2
    assert json.loads(chunks[0].split("data:", 1)[1])["delta"] == "Hello"
    assert json.loads(chunks[1].split("data:", 1)[1])["delta"] == " world"


def test_sse_parser_holds_an_incomplete_event_until_terminator(page):
    chunks = page.evaluate(r"""() => {
        const seen = [];
        const parser = createSseParser(c => seen.push(c));
        parser.push('data: {"delta":"partial"}');
        const before = seen.length;
        parser.push('\n\n');
        return { before, after: seen.length };
    }""")

    assert chunks["before"] == 0
    assert chunks["after"] == 1


def test_two_deltas_update_a_single_message_node(page):
    _stub_stream(page, [{"delta": "Hello"}, {"delta": " world"}])
    _ask(page)

    rows = page.eval_on_selector_all(".alc-msg-assistant", "els => els.length")
    text = page.eval_on_selector(".alc-msg-assistant", "el => el.textContent.trim()")
    assert rows == 1
    assert "Hello world" in text


# --- 3.2 stop / lock / abort ---------------------------------------------

def test_send_is_locked_while_streaming(page):
    page.evaluate("streaming = true; setStreaming(true)")
    assert page.eval_on_selector("#alc-chat-send", "el => el.disabled") is True

    before = page.eval_on_selector_all(".alc-msg-user", "els => els.length")
    _ask(page)
    after = page.eval_on_selector_all(".alc-msg-user", "els => els.length")
    assert after == before


def test_stop_aborts_and_restores_the_controls(page):
    state = page.evaluate("""() => {
        setStreaming(true);
        const before = streamRunId;
        stopStreaming();
        return {
            before,
            after: streamRunId,
            streaming,
            sendDisabled: document.getElementById('alc-chat-send').disabled,
            stopDisplay: document.getElementById('alc-chat-stop').style.display,
        };
    }""")

    assert state["after"] == state["before"] + 1
    assert state["streaming"] is False
    assert state["sendDisabled"] is False
    assert state["stopDisplay"] == "none"


def test_late_deltas_are_blocked_after_stop(page):
    current = page.evaluate("""() => {
        streamRunId = 10;
        stopStreaming();
        return isStreamCurrent(10);
    }""")
    assert current is False


def test_url_change_aborts_the_stream_and_clears_the_chat(page):
    state = page.evaluate("""() => {
        chatHistory = [{role: 'user', content: 'old'}];
        lastUrl = 'https://example.com/other';
        setStreaming(true);
        const before = streamRunId;
        checkPage();
        return {
            before,
            after: streamRunId,
            streaming,
            messages: document.querySelectorAll('.alc-msg').length,
            notice: (document.querySelector('.alc-chat-notice') || {}).textContent || '',
        };
    }""")

    assert state["after"] > state["before"]
    assert state["streaming"] is False
    assert state["messages"] == 0
    assert "New page" in state["notice"]


# --- 3.3 offline / markdown / chips / placeholder -------------------------

def test_offline_state_shows_the_start_command(page):
    page.route("**/api/page/ask", lambda route: route.abort())
    _ask(page)

    text = page.inner_text(".alc-bubble-error")
    assert "Backend offline" in text
    assert "cd alc && make backend" in text


def test_markdown_renders_headings_lists_and_code(page):
    _stub_stream(page, [
        {"delta": "## Title\n"},
        {"delta": "- one\n- two\n"},
        {"delta": "```python\nx = 1\n```"},
    ])
    _ask(page)

    assert page.eval_on_selector(".alc-bubble-assistant h4", "el => el.textContent") == "Title"
    assert page.eval_on_selector_all(".alc-bubble-assistant li", "els => els.length") == 2
    assert page.eval_on_selector_all(".alc-copy", "els => els.length") == 1
    assert page.eval_on_selector(".alc-code code", "el => el.textContent").strip() == "x = 1"


def test_markdown_escapes_model_html(page):
    html = page.evaluate("""() => renderMarkdown('<img src=x onerror=alert(1)> **bold**')""")

    assert "<img" not in html
    assert "&lt;img" in html
    assert "<strong>bold</strong>" in html


def test_chip_prefills_the_question(page):
    page.click(".alc-chip[data-q='Summarize this page']")
    assert page.input_value("#alc-chat-input") == "Summarize this page"


def test_placeholder_is_a_real_marker_and_is_removed_on_send(page):
    assert page.eval_on_selector_all(".alc-chat-placeholder", "els => els.length") == 1
    assert page.eval_on_selector(
        ".alc-chat-placeholder", "el => el.dataset.placeholder"
    ) == "1"

    _stub_stream(page, [{"delta": "ok"}])
    _ask(page)

    assert page.eval_on_selector_all(".alc-chat-placeholder", "els => els.length") == 0


# --- 3.4 context caching / selection -------------------------------------

def test_cache_expiry_makes_the_extension_resend_the_page(page):
    calls = []

    def handler(route):
        calls.append(route.request.post_data_json)
        if len(calls) == 1:
            route.fulfill(
                status=409,
                content_type="application/json",
                body=json.dumps({"detail": "page context missing"}),
            )
        else:
            route.fulfill(status=200, content_type="text/event-stream", body=SSE_OK)

    page.route("**/api/page/ask", handler)
    # pretend we already sent this page version, so the first request is hash-only
    page.evaluate("lastPageVersion = computePageVersion()")
    _ask(page)

    assert len(calls) == 2
    assert "page_text" not in calls[0]
    assert calls[0]["page_hash"]
    assert "page_text" in calls[1]


def test_page_body_is_sent_only_for_new_versions(page):
    calls = []
    _stub_stream(page, [{"delta": "ok"}], calls)

    _ask(page, "first")
    _ask(page, "second")

    assert len(calls) == 2
    assert "page_text" in calls[0]
    assert "page_text" not in calls[1]
    assert calls[1]["page_hash"] == calls[0]["page_hash"]


def test_valid_selection_is_sent_instead_of_the_page_body(page):
    page.evaluate("""
        const range = document.createRange();
        range.selectNodeContents(document.querySelector('#para'));
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('mouseup'));
        sel.removeAllRanges();
    """)
    calls = []
    _stub_stream(page, [{"delta": "ok"}], calls)
    _ask(page)

    assert "calls itself" in calls[0]["selection"]
    assert "page_text" not in calls[0]


# --- 3.5 code intent ----------------------------------------------------

def test_code_intent_sends_bounded_code_context(page):
    calls = []
    _stub_stream(page, [{"delta": "ok"}], calls)
    _ask(page, "write the code for this problem")

    assert calls[0]["code_intent"] is True
    assert "two_sum" in calls[0]["code_context"]
    assert len(calls[0]["code_context"]) <= 15000


def test_plain_question_sends_no_code_context(page):
    calls = []
    _stub_stream(page, [{"delta": "ok"}], calls)
    _ask(page, "what is recursion?")

    assert "code_context" not in calls[0]
    assert "code_intent" not in calls[0]


# --- history bounds -----------------------------------------------------

def test_history_is_bounded_by_size_not_just_count(page):
    result = page.evaluate("""() => {
        chatHistory = Array.from({length: 40}, (_, i) => ({
            role: i % 2 ? 'assistant' : 'user',
            content: 'x'.repeat(4000),
        }));
        const bounded = boundedChatHistory();
        return {
            count: bounded.length,
            chars: bounded.reduce((a, m) => a + m.content.length, 0),
        };
    }""")

    assert result["count"] <= 12
    assert result["chars"] <= 8000


def test_history_drops_non_conversation_roles(page):
    roles = page.evaluate("""() => {
        chatHistory = [
            {role: 'system', content: 'evil'},
            {role: 'tool', content: 'noise'},
            {role: 'user', content: 'real'},
        ];
        return boundedChatHistory().map(m => m.role);
    }""")

    assert roles == ["user"]
