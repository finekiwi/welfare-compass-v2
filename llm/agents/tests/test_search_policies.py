"""Tests for search backend adapter and search_policies tool."""

from __future__ import annotations

import os
import importlib
import json
import time
from unittest.mock import Mock, patch

import pytest
from langchain_core.documents import Document
import requests


def _make_doc(idx: int = 1) -> Document:
    return Document(
        page_content=f"정책 본문 {idx}",
        metadata={
            "plcyNo": f"P{idx}",
            "plcyNm": f"정책{idx}",
            "plcySprtCn": f"지원내용{idx}",
            "minAge": 19,
            "maxAge": 39,
            "region": "서울특별시",
            "earnCndSeCd": "0043001",
            "aplyYmd": "20240101~20261231",
            "aplyUrlAddr": f"https://example.com/{idx}",
            "lclsfNm": "주거",
            "mclsfNm": "월세",
            "score": 0.91,
            "rerank_score": 0.87,
        },
    )


class TestBackendSelector:
    def test_get_search_backend_default_direct(self, monkeypatch):
        monkeypatch.delenv("SEARCH_BACKEND", raising=False)

        from llm.agents.tools.search_backend import DirectSearchBackend, get_search_backend

        backend = get_search_backend()
        assert isinstance(backend, DirectSearchBackend)

    def test_get_search_backend_mcp(self, monkeypatch):
        monkeypatch.setenv("SEARCH_BACKEND", "mcp")

        from llm.agents.tools.search_backend import MCPSearchBackend, get_search_backend

        backend = get_search_backend()
        assert isinstance(backend, MCPSearchBackend)

    def test_all_tools_excludes_rewrite_query(self):
        from llm.agents.tools import ALL_TOOLS

        tool_names = [getattr(tool, "name", "") for tool in ALL_TOOLS]
        assert "rewrite_query" not in tool_names


class TestDirectSearchBackend:
    def test_empty_query_returns_no_results(self):
        from llm.agents.tools.search_backend import DirectSearchBackend

        backend = DirectSearchBackend(use_reranker=True)
        result = backend.search("   ", top_k=5)

        assert result["result_count"] == 0
        assert result["policies"] == []

    @patch("llm.agents.tools.search_backend.rewrite_query_internal", return_value="청년 주거 지원")
    def test_reranker_on_path(self, _mock_rewrite):
        from llm.agents.tools.search_backend import DirectSearchBackend

        backend = DirectSearchBackend(use_reranker=True)

        with patch.object(backend, "_search_with_bge", return_value=[_make_doc(1)]) as mock_bge, patch.object(
            backend,
            "_search_without_reranker",
            return_value=[],
        ) as mock_no_rerank:
            result = backend.search("월세 지원", top_k=3)

        mock_bge.assert_called_once_with(query="청년 주거 지원", top_k=3)
        mock_no_rerank.assert_not_called()
        assert result["result_count"] == 1
        assert result["policies"][0]["policy_id"] == "P1"

    @patch("llm.agents.tools.search_backend.rewrite_query_internal", return_value="청년 취업 지원")
    def test_reranker_off_path(self, _mock_rewrite):
        from llm.agents.tools.search_backend import DirectSearchBackend

        backend = DirectSearchBackend(use_reranker=False)

        with patch.object(backend, "_search_without_reranker", return_value=[_make_doc(2)]) as mock_no_rerank, patch.object(
            backend,
            "_search_with_bge",
            return_value=[],
        ) as mock_bge:
            result = backend.search("취업 지원", top_k=2)

        mock_no_rerank.assert_called_once_with(query="청년 취업 지원", top_k=2)
        mock_bge.assert_not_called()
        assert result["result_count"] == 1
        assert result["policies"][0]["title"] == "정책2"

    @patch("llm.agents.tools.search_backend.rewrite_query_internal", return_value="청년 주거")
    def test_top_k_is_clamped(self, _mock_rewrite):
        from llm.agents.tools.search_backend import DirectSearchBackend

        backend = DirectSearchBackend(use_reranker=True)
        docs = [_make_doc(i) for i in range(1, 35)]

        with patch.object(backend, "_search_with_bge", return_value=docs):
            result = backend.search("월세", top_k=999)

        assert result["result_count"] == 20
        assert len(result["policies"]) == 20

    def test_use_reranker_from_env(self, monkeypatch):
        from llm.agents.tools.search_backend import DirectSearchBackend

        monkeypatch.setenv("USE_RERANKER", "0")
        backend_off = DirectSearchBackend()
        assert backend_off.use_reranker is False

        monkeypatch.setenv("USE_RERANKER", "1")
        backend_on = DirectSearchBackend()
        assert backend_on.use_reranker is True


class _FakeSSEStreamResponse:
    def __init__(self, lines: list[str], keep_open: bool = False) -> None:
        self.lines = lines
        self.keep_open = keep_open
        self.closed = False

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        for line in self.lines:
            yield line.encode("utf-8")
        while self.keep_open and not self.closed:
            time.sleep(0.01)

    def close(self) -> None:
        self.closed = True


def _build_sse_lines(messages: list[dict]) -> list[str]:
    lines = [
        "event: endpoint",
        "data: /messages/?session_id=test-session",
        "",
    ]
    for message in messages:
        lines.extend(
            [
                "event: message",
                f"data: {json.dumps(message, ensure_ascii=False)}",
                "",
            ]
        )
    return lines


class TestMCPSearchBackend:
    @pytest.fixture(autouse=True)
    def _cleanup_shared_sessions(self):
        from llm.agents.tools.search_backend import MCPSearchBackend

        def _cleanup():
            with MCPSearchBackend._shared_sessions_lock:
                sessions = list(MCPSearchBackend._shared_sessions.values())
                MCPSearchBackend._shared_sessions.clear()

            for session in sessions:
                session.stop_event.set()
                if session.sse_response is not None:
                    session.sse_response.close()
                if session.listener is not None:
                    session.listener.join(timeout=0.1)

        _cleanup()
        yield
        _cleanup()

    def test_search_successfully_parses_mcp_response(self):
        from llm.agents.tools.search_backend import MCPSearchBackend

        init_message = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}
        call_payload = {
            "original_query": "청년 월세 지원",
            "rewritten_query": "청년 월세 지원 주거 보조금",
            "result_count": 1,
            "policies": [
                {
                    "policy_id": "P100",
                    "title": "청년월세지원",
                    "description": "월세 지원",
                    "support_content": "최대 20만원",
                    "age_min": 19,
                    "age_max": 34,
                    "district": "서울특별시",
                    "category": "주거",
                    "source": "postgres",
                }
            ],
        }
        call_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [{"type": "text", "text": json.dumps(call_payload, ensure_ascii=False)}],
                "isError": False,
            },
        }
        fake_sse = _FakeSSEStreamResponse(_build_sse_lines([init_message, call_message]))

        mock_post_response = Mock()
        mock_post_response.raise_for_status = Mock()

        with patch("llm.agents.tools.search_backend.requests.get", return_value=fake_sse), patch(
            "llm.agents.tools.search_backend.requests.post",
            return_value=mock_post_response,
        ) as mock_post:
            backend = MCPSearchBackend(timeout_seconds=0.5)
            result = backend.search("청년 월세 지원", top_k=5)

        assert result["result_count"] == 1
        assert result["original_query"] == "청년 월세 지원"
        assert result["rewritten_query"] == "청년 월세 지원 주거 보조금"
        assert result["policies"][0]["policy_id"] == "P100"

        methods = [call.kwargs["json"]["method"] for call in mock_post.call_args_list]
        assert methods == ["initialize", "notifications/initialized", "tools/call"]
        assert mock_post.call_args_list[2].kwargs["json"]["params"]["arguments"]["top_k"] == 5

    def test_search_reuses_sse_session_for_multiple_calls(self):
        from llm.agents.tools.search_backend import MCPSearchBackend

        init_message = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}
        call_message_1 = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "original_query": "월세 지원",
                                "rewritten_query": "청년 월세 지원",
                                "result_count": 1,
                                "policies": [{"policy_id": "P1", "title": "정책1"}],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
        }
        call_message_2 = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "original_query": "주거 지원",
                                "rewritten_query": "청년 주거 지원",
                                "result_count": 1,
                                "policies": [{"policy_id": "P2", "title": "정책2"}],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
        }
        fake_sse = _FakeSSEStreamResponse(
            _build_sse_lines([init_message, call_message_1, call_message_2]),
            keep_open=True,
        )

        mock_post_response = Mock()
        mock_post_response.raise_for_status = Mock()

        with patch("llm.agents.tools.search_backend.requests.get", return_value=fake_sse) as mock_get, patch(
            "llm.agents.tools.search_backend.requests.post",
            return_value=mock_post_response,
        ) as mock_post:
            backend = MCPSearchBackend(timeout_seconds=0.5)
            result_1 = backend.search("월세 지원", top_k=2)
            result_2 = backend.search("주거 지원", top_k=2)

        assert result_1["policies"][0]["policy_id"] == "P1"
        assert result_2["policies"][0]["policy_id"] == "P2"
        assert mock_get.call_count == 1

        methods = [call.kwargs["json"]["method"] for call in mock_post.call_args_list]
        assert methods == ["initialize", "notifications/initialized", "tools/call", "tools/call"]

    def test_search_returns_empty_on_sse_connection_failure(self):
        from llm.agents.tools.search_backend import MCPSearchBackend

        with patch(
            "llm.agents.tools.search_backend.requests.get",
            side_effect=requests.RequestException("connection failed"),
        ):
            backend = MCPSearchBackend(timeout_seconds=0.5)
            result = backend.search("월세 지원", top_k=3)

        assert result["result_count"] == 0
        assert result["policies"] == []

    def test_search_parses_split_text_chunks(self):
        from llm.agents.tools.search_backend import MCPSearchBackend

        init_message = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}
        split_call_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": '{"original_query":"월세 지원","rewritten_query":"청년 월세 지원","result_count":1,"policies":',
                    },
                    {"type": "text", "text": '[{"policy_id":"P100","title":"청년월세지원"}]}'},
                ]
            },
        }
        fake_sse = _FakeSSEStreamResponse(_build_sse_lines([init_message, split_call_message]))

        mock_post_response = Mock()
        mock_post_response.raise_for_status = Mock()

        with patch("llm.agents.tools.search_backend.requests.get", return_value=fake_sse), patch(
            "llm.agents.tools.search_backend.requests.post",
            return_value=mock_post_response,
        ):
            backend = MCPSearchBackend(timeout_seconds=0.5)
            result = backend.search("월세 지원", top_k=3)

        assert result["result_count"] == 1
        assert result["policies"][0]["policy_id"] == "P100"

    def test_search_returns_empty_on_timeout(self):
        from llm.agents.tools.search_backend import MCPSearchBackend

        init_message = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}
        fake_sse = _FakeSSEStreamResponse(_build_sse_lines([init_message]))

        mock_post_response = Mock()
        mock_post_response.raise_for_status = Mock()

        with patch("llm.agents.tools.search_backend.requests.get", return_value=fake_sse), patch(
            "llm.agents.tools.search_backend.requests.post",
            return_value=mock_post_response,
        ):
            backend = MCPSearchBackend(timeout_seconds=0.2)
            result = backend.search("월세 지원", top_k=3)

        assert result["result_count"] == 0
        assert result["policies"] == []

    def test_search_returns_empty_on_invalid_tool_payload_json(self):
        from llm.agents.tools.search_backend import MCPSearchBackend

        init_message = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}
        invalid_call_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"content": [{"type": "text", "text": "{invalid-json"}]},
        }
        fake_sse = _FakeSSEStreamResponse(_build_sse_lines([init_message, invalid_call_message]))

        mock_post_response = Mock()
        mock_post_response.raise_for_status = Mock()

        with patch("llm.agents.tools.search_backend.requests.get", return_value=fake_sse), patch(
            "llm.agents.tools.search_backend.requests.post",
            return_value=mock_post_response,
        ):
            backend = MCPSearchBackend(timeout_seconds=0.5)
            result = backend.search("월세 지원", top_k=3)

        assert result["result_count"] == 0
        assert result["policies"] == []


class TestSearchPoliciesTool:
    def test_format_no_results(self):
        from llm.agents.tools.search_policies import _format_for_orchestrator

        text = _format_for_orchestrator(
            {
                "original_query": "월세",
                "rewritten_query": "청년 월세",
                "result_count": 0,
                "policies": [],
            }
        )
        assert text == "검색 결과 없음"

    def test_search_policies_formats_backend_result(self, monkeypatch):
        from llm.agents.tools.search_policies import search_policies
        search_module = importlib.import_module("llm.agents.tools.search_policies")

        class DummyBackend:
            def __init__(self):
                self.calls = []

            def search(self, query: str, top_k: int = 10):
                self.calls.append((query, top_k))
                return {
                    "original_query": query,
                    "rewritten_query": "청년 월세 지원",
                    "result_count": 1,
                    "policies": [
                        {
                            "policy_id": "P100",
                            "title": "청년월세지원",
                            "description": "월세를 지원합니다",
                            "category": "주거",
                            "district": "서울특별시",
                            "age_min": 19,
                            "age_max": 39,
                            "apply_url": "https://example.com/p100",
                        }
                    ],
                }

        backend = DummyBackend()
        monkeypatch.setattr(search_module, "get_search_backend", lambda: backend)

        result = search_policies.invoke({"query": "월세", "top_k": 100})

        assert "검색 결과: 1건" in result
        assert "청년월세지원" in result
        assert "https://example.com/p100" in result
        assert backend.calls[0] == ("월세", 20)

    def test_search_policies_returns_no_result_message(self, monkeypatch):
        from llm.agents.tools.search_policies import search_policies
        search_module = importlib.import_module("llm.agents.tools.search_policies")

        class DummyBackend:
            def search(self, query: str, top_k: int = 10):
                return {
                    "original_query": query,
                    "rewritten_query": query,
                    "result_count": 0,
                    "policies": [],
                }

        monkeypatch.setattr(search_module, "get_search_backend", lambda: DummyBackend())

        result = search_policies.invoke({"query": "없는 정책", "top_k": 5})
        assert result == "검색 결과 없음"


needs_openai_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)

needs_chroma_db = pytest.mark.skipif(
    not os.path.exists("data/chroma_db"),
    reason="local Chroma DB not found",
)

needs_mcp_integration = pytest.mark.skipif(
    os.getenv("RUN_MCP_INTEGRATION", "").lower() not in {"1", "true", "yes", "on"},
    reason="RUN_MCP_INTEGRATION=1 not set",
)


@pytest.mark.integration
@needs_openai_key
@needs_chroma_db
def test_integration_direct_backend_calls_local_ensemble(monkeypatch):
    """Integration test: run direct backend against local ensemble stack."""
    from llm.agents.tools.search_backend import DirectSearchBackend

    # Keep integration focused on retriever path, not LLM rewrite quality.
    monkeypatch.setenv("USE_RERANKER", "0")

    with patch("llm.agents.tools.search_backend.rewrite_query_internal", return_value="청년 월세 지원"):
        backend = DirectSearchBackend()
        result = backend.search("월세 지원", top_k=2)

    assert isinstance(result, dict)
    assert result["original_query"] == "월세 지원"
    assert "policies" in result
    assert result["result_count"] >= 1
    assert result["result_count"] <= 2


@pytest.mark.integration
@needs_mcp_integration
def test_integration_mcp_backend_calls_remote_server():
    """Integration test: run MCP backend against remote SSE server."""
    from llm.agents.tools.search_backend import MCPSearchBackend

    backend = MCPSearchBackend(timeout_seconds=10.0)
    result = backend.search("청년 월세 지원", top_k=2)

    assert isinstance(result, dict)
    assert result["original_query"] == "청년 월세 지원"
    assert "policies" in result
    assert result["result_count"] >= 1
    assert len(result["policies"]) >= 1
