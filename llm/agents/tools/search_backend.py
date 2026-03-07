"""Search backend adapters for the `search_policies` tool."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
import threading
from typing import Any, Protocol

from langchain_core.documents import Document
import requests

from .rewrite_query import rewrite_query_internal

DEFAULT_TOP_K = 10
MAX_TOP_K = 20
DEFAULT_MCP_HOST = "100.69.81.51"
DEFAULT_MCP_PORT = 8001
DEFAULT_MCP_TIMEOUT_SECONDS = 10.0
MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_CLIENT_NAME = "welfare-llm-agent"
MCP_CLIENT_VERSION = "0.1.0"
POLICY_FIELD_ALIASES = {
    "plcy_no": "policy_id",
    "region": "district",
    "min_age": "age_min",
    "max_age": "age_max",
}

logger = logging.getLogger(__name__)


@dataclass
class _MCPSharedSession:
    host: str
    port: int
    timeout_seconds: float
    session_id: str | None = None
    initialized: bool = False
    next_request_id: int = 1
    sse_response: requests.Response | None = None
    listener: threading.Thread | None = None
    session_ready: threading.Event = field(default_factory=threading.Event)
    stop_event: threading.Event = field(default_factory=threading.Event)
    request_lock: threading.Lock = field(default_factory=threading.Lock)
    responses_lock: threading.Lock = field(default_factory=threading.Lock)
    responses: dict[int, dict[str, Any]] = field(default_factory=dict)
    response_events: dict[int, threading.Event] = field(default_factory=dict)


def normalize_top_k(top_k: int) -> int:
    """Normalize top_k to the supported range."""
    try:
        parsed = int(top_k)
    except (TypeError, ValueError):
        parsed = DEFAULT_TOP_K
    return min(max(1, parsed), MAX_TOP_K)


def _parse_bool_env(name: str, default: bool) -> bool:
    """Parse a boolean environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _compose_full_text(title: str, description: str, support_content: str) -> str:
    parts = [title.strip(), description.strip(), support_content.strip()]
    return "\n\n".join(part for part in parts if part)


def _doc_to_policy(doc: Document) -> dict[str, Any]:
    """Convert a LangChain Document to MCP-canonical policy dict."""
    metadata = doc.metadata or {}
    title = metadata.get("plcyNm", "")
    description = (doc.page_content or "")[:1200]
    support_content = metadata.get("plcySprtCn", "")

    # earnMaxAmt: 정책 소득 상한(만원). 없으면 None.
    raw_earn_max = metadata.get("earnMaxAmt")
    try:
        income_max_val: int | None = int(raw_earn_max) if raw_earn_max is not None else None
    except (TypeError, ValueError):
        income_max_val = None

    return {
        "policy_id": (metadata.get("plcyNo") or "").strip(),
        "title": title,
        "description": description,
        "support_content": support_content,
        "apply_method": "",
        "apply_url": metadata.get("aplyUrlAddr", ""),
        "district": metadata.get("region", ""),
        "category": metadata.get("lclsfNm", ""),
        "subcategory": metadata.get("mclsfNm", ""),
        "age_min": metadata.get("minAge"),
        "age_max": metadata.get("maxAge"),
        "income_level": metadata.get("earnCndSeCd", ""),
        "income_max": income_max_val,
        "apply_start_date": None,
        "apply_end_date": None,
        "business_start_date": None,
        "business_end_date": None,
        "full_text": _compose_full_text(title, description, support_content),
        "retrieval_score": metadata.get("score"),
        "rerank_score": metadata.get("rerank_score"),
        "source": "direct_retriever",
    }


def _normalize_policy_to_canonical(policy: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy policy aliases to canonical field names."""
    normalized = dict(policy)
    for alias, canonical in POLICY_FIELD_ALIASES.items():
        if canonical not in normalized and alias in normalized:
            normalized[canonical] = normalized[alias]
        normalized.pop(alias, None)
    return normalized


def _filter_by_income_max(
    policies: list[dict[str, Any]], user_income: int | None
) -> list[dict[str, Any]]:
    """Remove policies whose income_max is below the user's income threshold.

    Policies without an income_max value are always retained (fail-open).
    이는 earnCndSeCd='0043003'(기타) 등 earnMaxAmt가 없는 정책이
    자연스럽게 통과하는 구조.
    """
    if user_income is None:
        return policies
    return [
        p for p in policies
        if not p.get("income_max") or p["income_max"] >= user_income
    ]


class SearchBackend(Protocol):
    """Search backend protocol for adapter switching."""

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        income_max: int | None = None,
    ) -> dict[str, Any]:
        """Run policy search and return normalized result payload."""


class DirectSearchBackend:
    """Local search backend using retriever modules directly."""

    def __init__(self, use_reranker: bool | None = None) -> None:
        self.use_reranker = (
            _parse_bool_env("USE_RERANKER", True)
            if use_reranker is None
            else use_reranker
        )

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        income_max: int | None = None,
    ) -> dict[str, Any]:
        """Search policies with local retrievers."""
        original_query = (query or "").strip()
        if not original_query:
            return {
                "original_query": "",
                "rewritten_query": "",
                "result_count": 0,
                "policies": [],
            }

        normalized_top_k = normalize_top_k(top_k)
        rewritten_query = (rewrite_query_internal(original_query) or "").strip() or original_query
        docs = self._search_docs(query=rewritten_query, top_k=normalized_top_k)
        policies = [_normalize_policy_to_canonical(_doc_to_policy(doc)) for doc in docs][
            :normalized_top_k
        ]
        policies = _filter_by_income_max(policies, income_max)

        return {
            "original_query": original_query,
            "rewritten_query": rewritten_query,
            "result_count": len(policies),
            "policies": policies,
        }

    def _search_docs(self, query: str, top_k: int) -> list[Document]:
        if self.use_reranker:
            return self._search_with_bge(query=query, top_k=top_k)
        return self._search_without_reranker(query=query, top_k=top_k)

    def _search_with_bge(self, query: str, top_k: int) -> list[Document]:
        try:
            from llm.embeddings.ensemble_retriever_bge import ensemble_search_with_bge

            docs = ensemble_search_with_bge(
                query=query,
                top_k=top_k,
                return_metadata=False,
                verbose=False,
            )
            return list(docs or [])
        except Exception:
            logger.error("DirectSearchBackend BGE search failed", exc_info=True)
            return []

    def _search_without_reranker(self, query: str, top_k: int) -> list[Document]:
        try:
            from llm.embeddings.ensemble_retriever import ensemble_search

            docs = ensemble_search(
                query=query,
                k=top_k,
                use_reranker=False,
                verbose=False,
            )
            return list(docs or [])
        except Exception:
            logger.error("DirectSearchBackend non-reranked search failed", exc_info=True)
            return []


class MCPSearchBackend:
    """MCP search adapter via SSE transport."""

    _shared_sessions: dict[tuple[str, int], _MCPSharedSession] = {}
    _shared_sessions_lock = threading.Lock()

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout_seconds: float = DEFAULT_MCP_TIMEOUT_SECONDS,
    ) -> None:
        self.host = (host or os.getenv("MCP_HOST") or DEFAULT_MCP_HOST).strip()
        self.port = self._parse_port(port)
        self.timeout_seconds = max(float(timeout_seconds), 0.1)

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        income_max: int | None = None,
    ) -> dict[str, Any]:
        """Search policies through MCP server and return canonical payload."""
        original_query = (query or "").strip()
        if not original_query:
            return self._empty_result("")

        normalized_top_k = normalize_top_k(top_k)
        session = self._get_or_create_session()
        if session is None:
            return self._empty_result(original_query)

        with session.request_lock:
            if not self._ensure_initialized(session):
                self._invalidate_shared_session(session)
                return self._empty_result(original_query)

            message_url = self._messages_url(session)
            call_request_id, call_event = self._reserve_request_id(session)
            call_payload = {
                "jsonrpc": "2.0",
                "id": call_request_id,
                "method": "tools/call",
                "params": {
                    "name": "search_policies",
                    "arguments": {
                        "query": original_query,
                        "top_k": normalized_top_k,
                    },
                },
            }
            if not self._post_json(message_url, call_payload):
                self._clear_request_waiter(session, call_request_id)
                self._invalidate_shared_session(session)
                return self._empty_result(original_query)

            call_result = self._wait_for_response(
                session=session,
                request_id=call_request_id,
                response_event=call_event,
            )
            if not isinstance(call_result, dict):
                logger.error("MCPSearchBackend tools/call response timed out")
                self._invalidate_shared_session(session)
                return self._empty_result(original_query)
            if call_result.get("error"):
                logger.error(
                    "MCPSearchBackend tools/call error: %s",
                    call_result.get("error"),
                )
                return self._empty_result(original_query)

            parsed = self._parse_call_result(call_result, fallback_query=original_query)
            if parsed is None:
                return self._empty_result(original_query)

            policies = parsed.get("policies")
            if not isinstance(policies, list):
                logger.error("MCPSearchBackend invalid payload: policies is not a list")
                return self._empty_result(original_query)
            normalized_policies = [
                _normalize_policy_to_canonical(policy)
                for policy in policies
                if isinstance(policy, dict)
            ][:normalized_top_k]
            normalized_policies = _filter_by_income_max(normalized_policies, income_max)

            result_count = len(normalized_policies)

            return {
                "original_query": str(parsed.get("original_query") or original_query),
                "rewritten_query": str(parsed.get("rewritten_query") or original_query),
                "result_count": result_count,
                "policies": normalized_policies,
            }

    @property
    def _session_key(self) -> tuple[str, int]:
        return self.host, self.port

    def _sse_url(self, session: _MCPSharedSession) -> str:
        return f"http://{session.host}:{session.port}/sse"

    def _messages_url(self, session: _MCPSharedSession) -> str:
        return f"http://{session.host}:{session.port}/messages/?session_id={session.session_id}"

    def _parse_port(self, value: int | None) -> int:
        if value is not None:
            return int(value)
        raw = os.getenv("MCP_PORT")
        if raw is None:
            return DEFAULT_MCP_PORT
        try:
            return int(raw)
        except ValueError:
            logger.warning("Invalid MCP_PORT=%s. Falling back to %s", raw, DEFAULT_MCP_PORT)
            return DEFAULT_MCP_PORT

    def _get_or_create_session(self) -> _MCPSharedSession | None:
        with self._shared_sessions_lock:
            session = self._shared_sessions.get(self._session_key)
            if session is not None and self._is_session_healthy(session):
                return session

        created = self._create_session()
        if created is None:
            return None

        with self._shared_sessions_lock:
            existing = self._shared_sessions.get(self._session_key)
            if existing is not None and self._is_session_healthy(existing):
                self._close_session(created)
                return existing
            self._shared_sessions[self._session_key] = created
            return created

    def _create_session(self) -> _MCPSharedSession | None:
        session = _MCPSharedSession(
            host=self.host,
            port=self.port,
            timeout_seconds=self.timeout_seconds,
        )

        try:
            session.sse_response = requests.get(
                self._sse_url(session),
                stream=True,
                timeout=(3, session.timeout_seconds),
            )
            session.sse_response.raise_for_status()
        except requests.RequestException:
            logger.error("MCPSearchBackend SSE connection failed", exc_info=True)
            return None

        session.listener = threading.Thread(
            target=self._consume_sse,
            args=(session,),
            daemon=True,
        )
        session.listener.start()

        if not session.session_ready.wait(timeout=session.timeout_seconds):
            logger.error("MCPSearchBackend session_id wait timed out")
            self._close_session(session)
            return None
        if not session.session_id:
            logger.error("MCPSearchBackend session_id missing")
            self._close_session(session)
            return None
        return session

    def _is_session_healthy(self, session: _MCPSharedSession) -> bool:
        return (
            not session.stop_event.is_set()
            and session.session_ready.is_set()
            and bool(session.session_id)
            and session.sse_response is not None
            and session.listener is not None
            and session.listener.is_alive()
        )

    def _consume_sse(self, session: _MCPSharedSession) -> None:
        response = session.sse_response
        if response is None:
            return

        try:
            for raw_line in response.iter_lines():
                if session.stop_event.is_set():
                    break
                if not raw_line:
                    continue

                decoded = raw_line.decode("utf-8", errors="ignore").strip()
                if not decoded.startswith("data:"):
                    continue
                data = decoded[5:].strip()
                if not data:
                    continue

                session_id = self._extract_session_id(data)
                if session_id and session.session_id is None:
                    session.session_id = session_id
                    session.session_ready.set()
                    continue

                if not data.startswith("{"):
                    continue

                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    logger.debug("MCPSearchBackend ignored non-JSON SSE data: %s", data[:120])
                    continue
                if not isinstance(payload, dict):
                    continue

                response_id = payload.get("id")
                if response_id is None:
                    continue
                try:
                    normalized_id = int(response_id)
                except (TypeError, ValueError):
                    continue

                with session.responses_lock:
                    session.responses[normalized_id] = payload
                    response_event = session.response_events.get(normalized_id)
                    if response_event is not None:
                        response_event.set()
        except requests.RequestException:
            logger.error("MCPSearchBackend SSE stream read failed", exc_info=True)
        except Exception:
            logger.error("MCPSearchBackend SSE stream loop failed", exc_info=True)

    def _extract_session_id(self, data: str) -> str | None:
        marker = "session_id="
        if marker not in data:
            return None
        session_id = data.split(marker, 1)[1].strip()
        if not session_id:
            return None
        return session_id

    def _post_json(self, url: str, payload: dict[str, Any]) -> bool:
        try:
            response = requests.post(url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            return True
        except requests.Timeout:
            logger.error("MCPSearchBackend request timed out: %s", payload.get("method"))
            return False
        except requests.RequestException:
            logger.error(
                "MCPSearchBackend POST failed: %s",
                payload.get("method"),
                exc_info=True,
            )
            return False

    def _reserve_request_id(self, session: _MCPSharedSession) -> tuple[int, threading.Event]:
        with session.responses_lock:
            request_id = session.next_request_id
            session.next_request_id += 1
            response_event = threading.Event()
            session.response_events[request_id] = response_event
            cached = session.responses.get(request_id)
            if cached is not None:
                response_event.set()
            return request_id, response_event

    def _clear_request_waiter(self, session: _MCPSharedSession, request_id: int) -> None:
        with session.responses_lock:
            session.response_events.pop(request_id, None)

    def _wait_for_response(
        self,
        session: _MCPSharedSession,
        request_id: int,
        response_event: threading.Event,
    ) -> dict[str, Any] | None:
        with session.responses_lock:
            cached = session.responses.pop(request_id, None)
            if isinstance(cached, dict):
                session.response_events.pop(request_id, None)
                return cached

        if not response_event.wait(timeout=session.timeout_seconds):
            self._clear_request_waiter(session, request_id)
            return None

        with session.responses_lock:
            payload = session.responses.pop(request_id, None)
            session.response_events.pop(request_id, None)
        if isinstance(payload, dict):
            return payload
        return None

    def _ensure_initialized(self, session: _MCPSharedSession) -> bool:
        if session.initialized:
            return True
        if not session.session_id:
            return False

        message_url = self._messages_url(session)
        initialize_request_id, initialize_event = self._reserve_request_id(session)
        initialize_payload = {
            "jsonrpc": "2.0",
            "id": initialize_request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": MCP_CLIENT_NAME,
                    "version": MCP_CLIENT_VERSION,
                },
            },
        }
        if not self._post_json(message_url, initialize_payload):
            self._clear_request_waiter(session, initialize_request_id)
            return False

        initialize_result = self._wait_for_response(
            session=session,
            request_id=initialize_request_id,
            response_event=initialize_event,
        )
        if not isinstance(initialize_result, dict):
            logger.error("MCPSearchBackend initialize response timed out")
            return False
        if initialize_result.get("error"):
            logger.error(
                "MCPSearchBackend initialize error: %s",
                initialize_result.get("error"),
            )
            return False

        if not self._post_json(
            message_url,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        ):
            return False

        session.initialized = True
        return True

    def _close_session(self, session: _MCPSharedSession) -> None:
        session.stop_event.set()
        if session.sse_response is not None:
            session.sse_response.close()
        if session.listener is not None:
            session.listener.join(timeout=0.2)
        with session.responses_lock:
            session.response_events.clear()
            session.responses.clear()
        session.initialized = False

    def _invalidate_shared_session(self, session: _MCPSharedSession) -> None:
        with self._shared_sessions_lock:
            pooled = self._shared_sessions.get(self._session_key)
            if pooled is session:
                self._shared_sessions.pop(self._session_key, None)
        self._close_session(session)

    def _parse_call_result(
        self,
        call_result: dict[str, Any],
        fallback_query: str,
    ) -> dict[str, Any] | None:
        result = call_result.get("result")
        if not isinstance(result, dict):
            logger.error("MCPSearchBackend invalid tools/call result format")
            return None

        content = result.get("content")
        if not isinstance(content, list):
            logger.error("MCPSearchBackend invalid tools/call content")
            return None

        text_chunks: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                text_chunks.append(text.strip())

        if not text_chunks:
            logger.error("MCPSearchBackend tools/call content text missing")
            return None

        parsed: Any = None

        # 1) 일반 케이스: 첫 번째 text가 JSON 문자열 전체.
        try:
            parsed = json.loads(text_chunks[0])
        except json.JSONDecodeError:
            parsed = None

        # 2) 청크가 여러 개인 경우: 각 청크 자체가 독립 JSON일 수 있음.
        if parsed is None and len(text_chunks) > 1:
            for chunk in text_chunks:
                try:
                    candidate = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict):
                    parsed = candidate
                    break

        # 3) 분할 전송 대비: 구분자 없이 결합 후 파싱.
        if parsed is None:
            joined = "".join(text_chunks)
            try:
                parsed = json.loads(joined)
            except json.JSONDecodeError:
                parsed = None

        # 4) 최후 fallback: 개행 결합 후 파싱.
        if parsed is None:
            raw_payload = "\n".join(text_chunks)
            try:
                parsed = json.loads(raw_payload)
            except json.JSONDecodeError:
                logger.error("MCPSearchBackend tools/call payload parse failed", exc_info=True)
                return None

        if not isinstance(parsed, dict):
            logger.error("MCPSearchBackend tools/call payload is not an object")
            return None

        parsed.setdefault("original_query", fallback_query)
        parsed.setdefault("rewritten_query", fallback_query)
        parsed.setdefault("policies", [])
        return parsed

    def _empty_result(self, query: str) -> dict[str, Any]:
        return {
            "original_query": query,
            "rewritten_query": query,
            "result_count": 0,
            "policies": [],
        }


def get_search_backend() -> SearchBackend:
    """Resolve backend from SEARCH_BACKEND env (default: direct)."""
    backend_name = (os.getenv("SEARCH_BACKEND") or "direct").strip().lower()

    if backend_name == "mcp":
        return MCPSearchBackend()
    if backend_name != "direct":
        logger.warning("Unknown SEARCH_BACKEND=%s. Falling back to direct.", backend_name)
    return DirectSearchBackend()
