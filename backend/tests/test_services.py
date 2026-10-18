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
    """Captures the payload and replays canned NDJSON lines / chat replies."""

    def __init__(self, lines=None, reply="fake reply"):
        self._lines = lines or []
        self._reply = reply
        self.payload = None
        self.url = None
        self.method = None

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, json=None):
        self.method, self.url, self.payload = method, url, json
        return _FakeStreamResponse(self._lines)

    async def post(self, url, json=None):
        self.method, self.url, self.payload = "POST", url, json
        return _FakePostResponse(self._reply)


class _FakePostResponse:
    def __init__(self, reply):
        self._reply = reply

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._reply}}


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


class TestLLMClientGenerate:
    @pytest.mark.asyncio
    async def test_generate_goes_through_chat_endpoint(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="the answer")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            out = await client.generate("What is a BST?")

        assert out == "the answer"
        assert fake.url.endswith("/api/chat")
        assert fake.payload["messages"] == [{"role": "user", "content": "What is a BST?"}]
        # callers' API is unchanged: one prompt in, text out

    @pytest.mark.asyncio
    async def test_generate_system_prompt_becomes_a_system_message(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="x")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q", system_prompt="be terse")

        assert fake.payload["messages"][0] == {"role": "system", "content": "be terse"}
        assert fake.payload["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_json_mode_sets_format(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply='{"a": 1}')
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q", json_mode=True)

        assert fake.payload["format"] == "json"

    @pytest.mark.asyncio
    async def test_json_mode_is_off_by_default(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="plain")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q")

        assert "format" not in fake.payload

    @pytest.mark.asyncio
    async def test_options_carry_num_ctx_and_temperature(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="x")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q")

        options = fake.payload["options"]
        assert options["num_ctx"] >= 8192
        assert options["temperature"] == 0.2
