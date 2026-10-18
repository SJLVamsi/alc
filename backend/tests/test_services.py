import json
from unittest.mock import patch

import pytest

from app.services.note_generator import NoteGenerator
from app.services.flashcard_generator import FlashcardService


@pytest.mark.asyncio
async def test_note_generator_fallback():
    gen = NoteGenerator()
    result = gen._fallback_notes("Test Lesson", "Short content")
    assert "summary" in result
    assert result["summary"] is not None


def test_flashcard_intervals():
    service = FlashcardService()
    assert service.calculate_next_review(5) == 60
    assert service.calculate_next_review(0) == 1
    assert service.calculate_next_review(3) == 14


def test_flashcard_intervals_default():
    service = FlashcardService()
    assert service.calculate_next_review(3, current_interval=1) == 14


class TestCodingAssistant:
    def test_fallback_explanation(self):
        from app.services.coding_assistant import CodingAssistant
        ca = CodingAssistant()
        result = ca._fallback_explanation("Test problem")
        assert "explanation" in result
        assert "algorithms" in result
        assert "data_structures" in result

    def test_fallback_review(self):
        from app.services.coding_assistant import CodingAssistant
        ca = CodingAssistant()
        result = ca._fallback_review()
        assert "feedback" in result
        assert result["time_complexity"] == "O(n)"


class TestMCQExplainer:
    def test_fallback_explanation(self):
        from app.services.mcq_explainer import MCQExplainer
        mcq = MCQExplainer()
        result = mcq._fallback_explanation("Test question", [
            {"label": "A", "text": "Option A"},
            {"label": "B", "text": "Option B"},
        ])
        assert len(result["options"]) == 2
        assert result["suggested_answer"] == "A"


class TestKnowledgeBase:
    def test_dashboard_stats_empty(self, db_session):
        from app.services.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        stats = kb.get_dashboard_stats(db_session)
        assert stats.lessons_completed == 0
        assert stats.total_lessons > 0
        assert stats.study_time_minutes == 0.0


class _FakeStreamResponse:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeAsyncClient:
    """Captures the payload and replays canned NDJSON lines."""

    def __init__(self, lines):
        self._lines = lines
        self.payload = None

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, json=None):
        self.payload = json
        return _FakeStreamResponse(self._lines)


class TestLLMClientStreaming:
    @pytest.mark.asyncio
    async def test_chat_stream_yields_deltas(self):
        from app.services.llm_client import LLMClient

        lines = [
            json.dumps({"message": {"content": "Hel"}, "done": False}),
            "",
            json.dumps({"message": {"content": "lo"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]
        fake = _FakeAsyncClient(lines)

        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            chunks = [
                c async for c in client.chat_stream([{"role": "user", "content": "hi"}])
            ]

        assert chunks == ["Hel", "lo"]

    @pytest.mark.asyncio
    async def test_chat_stream_sets_num_ctx(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient([json.dumps({"message": {"content": "x"}, "done": True})])

        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            [c async for c in client.chat_stream([{"role": "user", "content": "hi"}])]

        assert fake.payload["stream"] is True
        assert fake.payload["options"]["num_ctx"] >= 8192

    @pytest.mark.asyncio
    async def test_chat_stream_ignores_malformed_lines(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(["not json", json.dumps({"message": {"content": "ok"}, "done": True})])

        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            chunks = [c async for c in client.chat_stream([{"role": "user", "content": "hi"}])]

        assert chunks == ["ok"]
