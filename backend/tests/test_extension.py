from unittest.mock import patch


def test_extension_explain(client):
    with patch("app.api.routes.extension.llm_client.generate", return_value="A clear explanation."):
        resp = client.post("/api/extension/ask", json={
            "action": "explain",
            "text": "What is a binary search tree?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "explanation" in data["response"]


def test_extension_quick_ask(client):
    with patch("app.api.routes.extension.llm_client.generate", return_value="Great question!"):
        resp = client.post("/api/extension/ask", json={
            "action": "quick-ask",
            "text": "What is recursion?",
        })
        assert resp.status_code == 200
        assert resp.json()["response"] == "Great question!"


def test_extension_chat(client):
    with patch("app.api.routes.extension.llm_client.chat", return_value="That's a great question about loops."):
        resp = client.post("/api/extension/ask", json={
            "action": "chat",
            "text": "Explain for loops",
            "messages": [{"role": "user", "content": "Explain for loops"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "loops" in data["response"]


def test_extension_unknown_action(client):
    resp = client.post("/api/extension/ask", json={
        "action": "unknown-action",
        "text": "test",
    })
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_extension_generate_notes(client):
    with patch("app.api.routes.extension.llm_client.generate", return_value="SUMMARY: Test summary"):
        resp = client.post("/api/extension/ask", json={
            "action": "generate-notes",
            "title": "Lesson 1",
            "text": "Course content here",
        })
        assert resp.status_code == 200
        assert "response" in resp.json()


def test_extension_chat_with_code_context(client):
    starter = "def two_sum(nums, target):\n    pass"
    with patch("app.api.routes.extension.llm_client.chat") as mock_chat:
        mock_chat.return_value = "def two_sum(nums, target):\n    ..."
        resp = client.post("/api/extension/ask", json={
            "action": "chat",
            "text": "write the code for this problem",
            "messages": [{"role": "user", "content": "write the code for this problem"}],
            "page_context": "Given an array of integers, return indices of the two numbers that add up to target.",
            "code_context": "=== Code block 1 ===\ndef two_sum(nums, target):\n    pass",
            "code_intent": True,
        })
        assert resp.status_code == 200
        assert "response" in resp.json()
        system_msg = mock_chat.call_args.args[0][0]["content"]
        assert starter in system_msg
        assert "function name" in system_msg
        assert "Code block" in system_msg


def test_extension_chat_multiple_code_blocks(client):
    blocks = "=== Code block 1 ===\ndef q1(arr):\n    pass\n\n=== Code block 2 ===\ndef q2(s):\n    pass"
    with patch("app.api.routes.extension.llm_client.chat") as mock_chat:
        mock_chat.return_value = "def q2(s):\n    ..."
        resp = client.post("/api/extension/ask", json={
            "action": "chat",
            "text": "give me code for question 2",
            "messages": [{"role": "user", "content": "give me code for question 2"}],
            "code_context": blocks,
            "code_intent": True,
        })
        assert resp.status_code == 200
        system_msg = mock_chat.call_args.args[0][0]["content"]
        assert "=== Code block 2 ===" in system_msg
        assert "matches the question" in system_msg


def test_extension_coding_help_with_code(client):
    starter = "class Solution:\n    def twoSum(self, nums, target):\n        pass"
    with patch("app.api.routes.extension.llm_client.generate") as mock_gen:
        mock_gen.return_value = "```python\nclass Solution:\n    def twoSum(self, nums, target):\n        ...\n```"
        resp = client.post("/api/extension/ask", json={
            "action": "coding-help",
            "text": "Given an array nums and a target, return indices of the two numbers that sum to target.",
            "code_context": starter,
        })
        assert resp.status_code == 200
        assert "response" in resp.json()
        prompt = mock_gen.call_args.args[0]
        assert starter in prompt
        assert "function name" in prompt
