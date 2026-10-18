import json
from unittest.mock import patch


def _sse_events(text: str) -> list:
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            payload = line[len("data: "):]
            events.append(payload if payload == "[DONE]" else json.loads(payload))
    return events


def _stream_from(chunks, captured=None):
    async def _gen(messages):
        if captured is not None:
            captured["messages"] = messages
        for c in chunks:
            yield c
    return _gen


def test_page_ask_streams_deltas(client):
    captured = {}
    with patch(
        "app.api.routes.page.llm_client.chat_stream",
        _stream_from(["Hel", "lo"], captured),
    ):
        resp = client.post("/api/page/ask", json={
            "question": "What is this page about?",
            "page_text": "Binary search runs in O(log n).",
            "title": "Searching",
        })

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _sse_events(resp.text)
    assert events[0] == {"delta": "Hel"}
    assert events[1] == {"delta": "lo"}
    assert events[-1] == "[DONE]"

    system = captured["messages"][0]
    assert system["role"] == "system"
    assert "page content" in system["content"].lower()
    assert "Binary search runs in O(log n)." in system["content"]
    assert captured["messages"][-1]["content"] == "What is this page about?"


def test_page_ask_selection_takes_precedence(client):
    captured = {}
    with patch(
        "app.api.routes.page.llm_client.chat_stream",
        _stream_from(["ok"], captured),
    ):
        resp = client.post("/api/page/ask", json={
            "question": "Explain this",
            "page_text": "The whole page text.",
            "selection": "Selected snippet only.",
        })

    assert resp.status_code == 200
    system = captured["messages"][0]["content"]
    assert "Selected snippet only." in system
    assert "The whole page text." not in system


def test_page_ask_caches_page_text_by_hash(client):
    captured = {}
    with patch(
        "app.api.routes.page.llm_client.chat_stream",
        _stream_from(["ok"], captured),
    ):
        client.post("/api/page/ask", json={
            "question": "q1",
            "page_text": "Cached page body.",
            "page_hash": "hash-abc",
        })
        client.post("/api/page/ask", json={
            "question": "q2",
            "page_hash": "hash-abc",
        })

    system = captured["messages"][0]["content"]
    assert "Cached page body." in system


def test_page_ask_trims_history_to_six_turns(client):
    captured = {}
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i}"}
        for i in range(20)
    ]
    with patch(
        "app.api.routes.page.llm_client.chat_stream",
        _stream_from(["ok"], captured),
    ):
        client.post("/api/page/ask", json={
            "question": "latest",
            "page_text": "text",
            "history": history,
        })

    messages = captured["messages"]
    # system + 6 history turns + final user question
    assert len(messages) == 8
    assert messages[1]["content"] == "turn 14"


def test_page_ask_reports_errors_and_closes_stream(client):
    async def _boom(messages):
        yield "partial"
        raise RuntimeError("ollama exploded")

    with patch("app.api.routes.page.llm_client.chat_stream", _boom):
        resp = client.post("/api/page/ask", json={"question": "hi", "page_text": "t"})

    assert resp.status_code == 200
    events = _sse_events(resp.text)
    assert {"delta": "partial"} in events
    assert any(isinstance(e, dict) and "error" in e for e in events)
    assert events[-1] == "[DONE]"
