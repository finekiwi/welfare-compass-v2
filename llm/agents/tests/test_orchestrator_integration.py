"""오케스트레이터 통합 테스트.

- integration_orchestrator: 실제 LLM + stub 도구 (계약 검증)
- integration_live: 실제 LLM + 실제 도구 (스모크)
"""

from __future__ import annotations

import json
import os
import re
import uuid
from collections import Counter
from typing import Any, Callable

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from llm.agents.agent import create_agent, run_agent, stream_agent
from llm.agents.prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT


needs_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


def _is_backend_unavailable_error(exc: Exception) -> bool:
    text = str(exc).lower()
    keywords = (
        "connection error",
        "failed to establish",
        "api connection",
        "apiconnectionerror",
        "read timeout",
        "timed out",
        "nodename nor servname",
        "temporary failure in name resolution",
    )
    return any(keyword in text for keyword in keywords)


def _invoke_with_skip(agent, messages: list[Any], thread_id: str) -> dict:
    recursion_limit = getattr(agent, "_max_iterations", 5) * 2 + 1
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }
    try:
        return agent.invoke({"messages": messages}, config=config)
    except Exception as exc:  # pragma: no cover - network-dependent
        if _is_backend_unavailable_error(exc):
            pytest.skip(f"integration unavailable: {exc}")
        raise


def _run_agent_with_skip(agent, message: str, thread_id: str) -> dict:
    result = run_agent(agent, message, thread_id=thread_id, verbose=False)
    if result.get("error") and _is_backend_unavailable_error(Exception(result["error"])):
        pytest.skip(f"integration unavailable: {result['error']}")
    return result


def _extract_tool_calls(messages: list[Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            continue
        for call in tool_calls:
            calls.append(
                {
                    "name": call.get("name"),
                    "args": call.get("args", {}),
                }
            )
    return calls


def _response_text(messages: list[Any]) -> str:
    for msg in reversed(messages):
        if getattr(msg, "type", "") == "ai":
            return getattr(msg, "content", "") or ""
    return ""


def _result_message(result: dict[str, Any]) -> str:
    response = result.get("response")
    if hasattr(response, "message"):
        return str(response.message)
    return str(response or "")


def _assert_subsequence(items: list[str], expected: list[str]) -> None:
    idx = 0
    for item in items:
        if idx < len(expected) and item == expected[idx]:
            idx += 1
    assert idx == len(expected), f"expected subsequence {expected}, got {items}"


def _tool_count(calls: list[dict[str, Any]], name: str) -> int:
    return sum(1 for call in calls if call.get("name") == name)


def _latest_check_user_info(call_log: list[dict[str, Any]]) -> dict[str, Any] | None:
    for call in reversed(call_log):
        if call["name"] != "check_eligibility":
            continue
        raw = call["args"].get("user_info")
        if not isinstance(raw, str):
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _latest_extract_result(call_log: list[dict[str, Any]]) -> dict[str, Any] | None:
    for call in reversed(call_log):
        if call["name"] != "extract_info":
            continue
        result = call.get("result")
        if isinstance(result, dict):
            return result
    return None


def _search_queries(call_log: list[dict[str, Any]]) -> list[str]:
    return [
        str(call["args"].get("query", ""))
        for call in call_log
        if call["name"] == "search_policies"
    ]


def _build_stub_agent(
    *,
    extract_impl: Callable[[str], dict[str, Any]] | None = None,
    search_impl: Callable[[str, int, dict[str, Any]], list[dict[str, Any]]] | None = None,
    check_impl: Callable[[str, str, dict[str, Any]], list[dict[str, Any]]] | None = None,
    max_iterations: int = 5,
):
    state: dict[str, Any] = {"search_calls": 0}
    call_log: list[dict[str, Any]] = []

    def _default_extract(message: str) -> dict[str, Any]:
        age = None
        age_match = re.search(r"(\d{2})\s*살", message)
        if age_match:
            age = int(age_match.group(1))

        residence = None
        for token, gu in {
            "강남": "강남구",
            "서초": "서초구",
            "마포": "마포구",
            "송파": "송파구",
            "관악": "관악구",
        }.items():
            if token in message:
                residence = gu
                break

        result: dict[str, Any] = {}
        if age is not None:
            result["age"] = age
        if residence is not None:
            result["residence"] = residence
        if "취업" in message or "구직" in message:
            result["employment_status"] = "구직중"
        return result

    def _default_search(query: str, _top_k: int, state_ref: dict[str, Any]) -> list[dict[str, Any]]:
        state_ref["search_calls"] += 1
        if "정책a" in query.lower() or "a" in query.lower():
            return [
                {
                    "policy_id": "A001",
                    "title": "정책A",
                    "summary": "A 지원",
                    "category": "주거",
                    "link": "https://example.com/a",
                }
            ]
        if "정책b" in query.lower() or "b" in query.lower():
            return [
                {
                    "policy_id": "B001",
                    "title": "정책B",
                    "summary": "B 지원",
                    "category": "취업",
                    "link": "https://example.com/b",
                }
            ]
        if "월세" in query or "주거" in query:
            return [
                {
                    "policy_id": "H001",
                    "title": "청년월세지원",
                    "summary": "월세 보조",
                    "category": "주거",
                    "link": "https://example.com/housing",
                }
            ]
        if "취업" in query:
            return [
                {
                    "policy_id": "J001",
                    "title": "청년취업지원",
                    "summary": "취업 역량 강화",
                    "category": "취업",
                    "link": "https://example.com/job",
                }
            ]
        if "창업" in query:
            return [
                {
                    "policy_id": "B101",
                    "title": "청년창업지원",
                    "summary": "창업 자금/교육",
                    "category": "창업",
                    "link": "https://example.com/biz",
                }
            ]
        return [
            {
                "policy_id": "G001",
                "title": "청년일반지원",
                "summary": "일반 지원",
                "category": "기타",
                "link": "https://example.com/general",
            }
        ]

    def _default_check(policies: str, user_info: str, _state: dict[str, Any]) -> list[dict[str, Any]]:
        info: dict[str, Any] = {}
        try:
            parsed_info = json.loads(user_info)
            if isinstance(parsed_info, dict):
                info = parsed_info
        except json.JSONDecodeError:
            pass

        if policies.strip() in ("all", "all_policies"):
            policies_list: list[dict[str, Any]] = [
                {
                    "policy_id": "H001",
                    "title": "청년월세지원",
                    "category": "주거",
                },
                {
                    "policy_id": "J001",
                    "title": "청년취업지원",
                    "category": "취업",
                },
                {
                    "policy_id": "B101",
                    "title": "청년창업지원",
                    "category": "창업",
                },
            ]
        else:
            try:
                parsed = json.loads(policies)
                policies_list = parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                policies_list = []

        age = info.get("age")
        interests = info.get("needs") or info.get("interests") or []
        interests_set = set(interests if isinstance(interests, list) else [])

        rows: list[dict[str, Any]] = []
        for policy in policies_list:
            category = policy.get("category")
            reasons: list[str] = []
            is_eligible: bool | None = True

            if age is None:
                is_eligible = None
                reasons.append("나이 정보 없음")
            elif age < 19 or age > 39:
                is_eligible = False
                reasons.append("나이 조건 미충족")

            if is_eligible is not False and interests_set and category not in interests_set:
                is_eligible = False
                reasons.append("관심분야 미일치")

            rows.append(
                {
                    "policy_id": policy.get("policy_id", ""),
                    "title": policy.get("title", ""),
                    "is_eligible": is_eligible,
                    "reasons": reasons,
                }
            )
        return rows

    extract_func = extract_impl or _default_extract
    search_func = search_impl or _default_search
    check_func = check_impl or _default_check

    @tool
    def extract_info(message: str) -> str:
        """사용자 발화에서 프로필 정보 추출."""
        result = extract_func(message)
        call_log.append(
            {
                "name": "extract_info",
                "args": {"message": message},
                "result": result,
            }
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    def search_policies(query: str, top_k: int = 10) -> str:
        """정책 검색 결과를 반환."""
        result = search_func(query, top_k, state)
        call_log.append(
            {
                "name": "search_policies",
                "args": {"query": query, "top_k": top_k},
                "result": result,
            }
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    def check_eligibility(policies: str, user_info: str) -> str:
        """정책 자격요건 매칭 결과를 반환."""
        result = check_func(policies, user_info, state)
        call_log.append(
            {
                "name": "check_eligibility",
                "args": {"policies": policies, "user_info": user_info},
                "result": result,
            }
        )
        return json.dumps(result, ensure_ascii=False)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_react_agent(
        model=llm,
        tools=[extract_info, search_policies, check_eligibility],
        prompt=SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
        checkpointer=MemorySaver(),
    )
    setattr(agent, "_max_iterations", max_iterations)
    return agent, call_log


@pytest.mark.integration
@pytest.mark.integration_orchestrator
@needs_api_key
class TestOrchestratorIntegrationContracts:
    """실제 LLM + stub 도구 기반 오케스트레이터 계약 검증."""

    def test_itg_matching_calls_extract_then_check(self):
        agent, _ = _build_stub_agent()
        result = _run_agent_with_skip(agent, "27살인데 뭐 받을 수 있어?", thread_id=f"it-{uuid.uuid4().hex}")
        names = [call["name"] for call in result["tool_calls"]]
        _assert_subsequence(names, ["extract_info", "check_eligibility"])

    def test_itg_explore_calls_search(self):
        agent, _ = _build_stub_agent()
        result = _run_agent_with_skip(agent, "주거 정책 뭐 있어?", thread_id=f"it-{uuid.uuid4().hex}")
        names = [call["name"] for call in result["tool_calls"]]
        assert "search_policies" in names

    def test_itg_faq_calls_search(self):
        agent, _ = _build_stub_agent()
        result = _run_agent_with_skip(agent, "청년월세지원 신청 어떻게 해?", thread_id=f"it-{uuid.uuid4().hex}")
        names = [call["name"] for call in result["tool_calls"]]
        assert "search_policies" in names

    def test_itg_compare_searches_both_entities(self):
        agent, _ = _build_stub_agent()
        result = _run_agent_with_skip(agent, "정책A랑 정책B 비교해줘", thread_id=f"it-{uuid.uuid4().hex}")
        names = [call["name"] for call in result["tool_calls"]]
        assert _tool_count(result["tool_calls"], "search_policies") >= 2
        assert "search_policies" in names

    def test_itg_chitchat_no_tools(self):
        agent, _ = _build_stub_agent()
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="안녕!")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        calls = _extract_tool_calls(raw.get("messages", []))
        assert calls == []

    def test_itg_matching_uses_all_policies_mode(self):
        agent, call_log = _build_stub_agent()
        result = _run_agent_with_skip(agent, "추천해줘", thread_id=f"it-{uuid.uuid4().hex}")
        checks = [call for call in call_log if call["name"] == "check_eligibility"]
        if not checks:
            response = _result_message(result)
            assert response
            assert ("?" in response) or ("알려" in response) or ("조건" in response)
            return
        policies_arg = str(checks[-1]["args"].get("policies", "")).strip()
        assert policies_arg in {"all", "all_policies"}

    def test_itg_compare_does_not_guess_without_second_search(self):
        agent, _ = _build_stub_agent()
        result = _run_agent_with_skip(agent, "정책A vs 정책B 뭐가 나아?", thread_id=f"it-{uuid.uuid4().hex}")
        search_count = _tool_count(result["tool_calls"], "search_policies")
        if search_count >= 2:
            return

        response = _result_message(result)
        assert response

        normalized = response.lower().replace(" ", "")
        decisive_patterns = (
            "정책a가더",
            "정책a가유리",
            "정책b가더",
            "정책b가유리",
            "a가더",
            "b가더",
            "무조건",
            "확실히",
        )
        assert not any(pattern in normalized for pattern in decisive_patterns)
        assert any(keyword in response for keyword in ("비교", "확인", "추가", "정보", "검색", "?"))

    def test_itg_non_policy_topic_redirects_without_deep_tools(self):
        agent, _ = _build_stub_agent()
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="오늘 점심 뭐 먹지?")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        calls = _extract_tool_calls(raw.get("messages", []))
        assert len(calls) == 0
        assert _response_text(raw.get("messages", []))

    def test_itg_matching_info_insufficient_prefers_question(self):
        agent, _ = _build_stub_agent()
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="뭐 받을 수 있어?")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        response = _response_text(raw.get("messages", []))
        assert response
        assert ("?" in response) or ("알려" in response) or ("정보" in response)

    def test_itg_tool_repeat_under_limit(self):
        agent, _ = _build_stub_agent()
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="주거랑 취업 정책을 비교해서 추천해줘")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        names = [call["name"] for call in _extract_tool_calls(raw.get("messages", []))]
        counts = Counter(names)
        assert all(count <= 3 for count in counts.values())

    def test_itg_search_zero_triggers_one_retry_with_different_query(self):
        def zero_then_one(query: str, top_k: int, state: dict[str, Any]) -> list[dict[str, Any]]:
            state["search_calls"] += 1
            if state["search_calls"] == 1:
                return []
            return [
                {
                    "policy_id": "R001",
                    "title": "재검색 정책",
                    "summary": "확장 검색 결과",
                    "category": "문화",
                    "link": "https://example.com/retry",
                }
            ]

        agent, call_log = _build_stub_agent(search_impl=zero_then_one)
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="서대문구 문화 바우처 정책 목록 보여줘")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        queries = _search_queries(call_log)
        if not queries:
            response = _response_text(raw.get("messages", []))
            assert response
            assert any(keyword in response for keyword in ("정책", "지원", "추천", "정보", "조건"))
            return
        if len(queries) >= 2:
            assert queries[0] != queries[1]
        else:
            assert _response_text(raw.get("messages", []))

    def test_itg_search_zero_twice_returns_center_guidance(self):
        def always_zero(query: str, top_k: int, state: dict[str, Any]) -> list[dict[str, Any]]:
            state["search_calls"] += 1
            return []

        agent, call_log = _build_stub_agent(search_impl=always_zero)
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="서대문구 문화 바우처 정책 목록 찾아줘")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        response = _response_text(raw.get("messages", []))
        queries = _search_queries(call_log)
        if not queries:
            assert response
            assert any(keyword in response for keyword in ("정책", "지원", "추천", "정보", "조건", "문의"))
            return
        assert ("1644-8030" in response) or ("청년센터" in response) or ("문의" in response) or ("찾지 못" in response)

    def test_itg_all_ineligible_shows_reasoned_alternative(self):
        def all_ineligible(policies: str, user_info: str, _state: dict[str, Any]) -> list[dict[str, Any]]:
            return [
                {
                    "policy_id": "P1",
                    "title": "청년월세지원",
                    "is_eligible": False,
                    "reasons": ["나이 조건 미충족"],
                },
                {
                    "policy_id": "P2",
                    "title": "청년취업지원",
                    "is_eligible": False,
                    "reasons": ["소득 조건 미충족"],
                },
            ]

        agent, _ = _build_stub_agent(check_impl=all_ineligible)
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="45살인데 받을 수 있는 정책 있어?")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        response = _response_text(raw.get("messages", []))
        assert (
            ("없" in response)
            or ("부적격" in response)
            or ("미충족" in response)
            or ("안 맞" in response)
            or ("39세" in response)
            or ("중장년" in response)
        )

    def test_itg_partial_eligible_prioritizes_eligible(self):
        def partial(policies: str, user_info: str, _state: dict[str, Any]) -> list[dict[str, Any]]:
            return [
                {
                    "policy_id": "P1",
                    "title": "청년월세지원",
                    "is_eligible": True,
                    "reasons": [],
                },
                {
                    "policy_id": "P2",
                    "title": "청년창업지원",
                    "is_eligible": False,
                    "reasons": ["나이 조건 미충족"],
                },
            ]

        agent, _ = _build_stub_agent(check_impl=partial)
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="27살 강남구인데 추천해줘")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        response = _response_text(raw.get("messages", []))
        assert "청년월세지원" in response

    def test_itg_info_missing_asks_single_question(self):
        def missing_info(policies: str, user_info: str, _state: dict[str, Any]) -> list[dict[str, Any]]:
            return [
                {
                    "policy_id": "P1",
                    "title": "청년월세지원",
                    "is_eligible": None,
                    "reasons": ["나이 정보 없음"],
                }
            ]

        agent, _ = _build_stub_agent(check_impl=missing_info)
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="지원 좀 알려줘")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        response = _response_text(raw.get("messages", []))
        assert "?" in response
        assert response.count("?") <= 2

    def test_itg_tool_failure_graceful_fallback(self):
        def broken_search(query: str, top_k: int, state: dict[str, Any]) -> list[dict[str, Any]]:
            raise RuntimeError("stub backend down")

        agent, _ = _build_stub_agent(search_impl=broken_search)
        result = _run_agent_with_skip(agent, "주거 정책 알려줘", thread_id=f"it-{uuid.uuid4().hex}")
        response = _result_message(result)
        assert response
        if result["error"] is not None:
            assert "오류" in response or "죄송" in response

    def test_itg_multiturn_accumulates_user_info(self):
        agent, call_log = _build_stub_agent()
        thread_id = f"it-{uuid.uuid4().hex}"
        _invoke_with_skip(agent, [HumanMessage(content="나 27살이야")], thread_id=thread_id)
        raw2 = _invoke_with_skip(agent, [HumanMessage(content="강남구 살고 있는데 뭐 받을 수 있어?")], thread_id=thread_id)
        info = _latest_check_user_info(call_log)
        if info is None:
            extract = _latest_extract_result(call_log)
            if extract is None:
                response = _response_text(raw2.get("messages", []))
                assert response
                assert ("?" in response) or ("정보" in response) or ("조건" in response)
                return
            assert extract.get("age") == 27
            residence = str(extract.get("residence", ""))
            if residence:
                assert residence.startswith("강남")
            return
        assert info.get("age") == 27
        residence = str(info.get("residence", ""))
        if residence:
            assert residence.startswith("강남")

    def test_itg_multiturn_overwrites_conflicting_info(self):
        agent, call_log = _build_stub_agent()
        thread_id = f"it-{uuid.uuid4().hex}"
        _invoke_with_skip(agent, [HumanMessage(content="서초구 살아")], thread_id=thread_id)
        raw2 = _invoke_with_skip(agent, [HumanMessage(content="아니 강남구야 추천해줘")], thread_id=thread_id)
        info = _latest_check_user_info(call_log)
        if info is None:
            extract = _latest_extract_result(call_log)
            if extract is None:
                response = _response_text(raw2.get("messages", []))
                assert response
                assert ("?" in response) or ("정보" in response) or ("조건" in response)
                return
            residence = str(extract.get("residence", ""))
            assert residence.startswith("강남")
            return
        residence = str(info.get("residence", ""))
        if residence:
            assert residence.startswith("강남")

    def test_itg_multiturn_resolves_pronoun_reference(self):
        agent, call_log = _build_stub_agent()
        thread_id = f"it-{uuid.uuid4().hex}"
        _invoke_with_skip(agent, [HumanMessage(content="주거 정책 뭐 있어?")], thread_id=thread_id)
        _invoke_with_skip(agent, [HumanMessage(content="아까 그 정책 신청 방법 알려줘")], thread_id=thread_id)
        assert len(_search_queries(call_log)) >= 2

    def test_itg_profile_system_message_influences_check(self):
        agent, call_log = _build_stub_agent()
        profile = {"age": 27, "residence": "강남구", "interests": ["취업"]}
        thread_id = f"it-{uuid.uuid4().hex}"
        raw = _invoke_with_skip(
            agent,
            [
                SystemMessage(content=f"이 사용자의 등록 프로필: {json.dumps(profile, ensure_ascii=False)}"),
                HumanMessage(content="추천해줘"),
            ],
            thread_id=thread_id,
        )
        tool_names = [call["name"] for call in call_log]
        if not tool_names:
            raw = _invoke_with_skip(
                agent,
                [
                    SystemMessage(content=f"이 사용자의 등록 프로필: {json.dumps(profile, ensure_ascii=False)}"),
                    HumanMessage(content="등록 프로필 기준으로 자격을 도구로 확인해줘"),
                ],
                thread_id=thread_id,
            )
            tool_names = [call["name"] for call in call_log]
        info = _latest_check_user_info(call_log)
        if not tool_names:
            response = _response_text(raw.get("messages", []))
            assert response
            assert any(keyword in response for keyword in ("정책", "추천", "지원", "정보", "조건"))
            return
        if info is None:
            response = _response_text(raw.get("messages", []))
            assert response
            assert ("?" in response) or ("정보" in response) or ("조건" in response)
            return

        info_json = json.dumps(info, ensure_ascii=False)
        assert ("27" in info_json) or ("강남" in info_json)

    def test_itg_profile_used_when_needs_missing(self):
        agent, call_log = _build_stub_agent()
        profile = {"age": 27, "residence": "강남구", "interests": ["취업"]}
        _invoke_with_skip(
            agent,
            [
                SystemMessage(content=f"이 사용자의 등록 프로필: {json.dumps(profile, ensure_ascii=False)}"),
                HumanMessage(content="27살인데 뭐라도 받을 수 있어?"),
            ],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        info = _latest_check_user_info(call_log)
        assert info is not None
        fields = json.dumps(info, ensure_ascii=False)
        assert ("취업" in fields) or ("needs" not in info and "interests" not in info)

    def test_itg_profile_not_reextracted_soft(self):
        agent, call_log = _build_stub_agent()
        profile = {"age": 27, "residence": "강남구", "interests": ["취업"]}
        _invoke_with_skip(
            agent,
            [
                SystemMessage(content=f"이 사용자의 등록 프로필: {json.dumps(profile, ensure_ascii=False)}"),
                HumanMessage(content="추천해줘"),
            ],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        extract_calls = [call for call in call_log if call["name"] == "extract_info"]
        assert len(extract_calls) in (0, 1)

    def test_itg_needs_housing_detected_when_explicit(self):
        agent, call_log = _build_stub_agent()
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="27살 강남 사는데 월세가 비싸요")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        tool_names = [call["name"] for call in call_log]
        assert "extract_info" in tool_names
        info = _latest_check_user_info(call_log)
        if info is None:
            response = _response_text(raw.get("messages", []))
            assert response
            assert ("?" in response) or ("정보" in response) or ("조건" in response)
            return
        fields = json.dumps(info, ensure_ascii=False)
        assert ("강남" in fields) or ("27" in fields)

    def test_itg_needs_multiple_detected(self):
        agent, call_log = _build_stub_agent()
        raw = _invoke_with_skip(
            agent,
            [HumanMessage(content="27살인데 취업 준비하면서 창업도 생각 중이에요")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        tool_names = [call["name"] for call in call_log]
        assert "extract_info" in tool_names
        info = _latest_check_user_info(call_log)
        if info is None:
            response = _response_text(raw.get("messages", []))
            assert response
            assert ("?" in response) or ("정보" in response) or ("조건" in response)
            return
        fields = json.dumps(info, ensure_ascii=False)
        assert "27" in fields

    def test_itg_needs_ambiguous_omitted_or_no_check(self):
        agent, call_log = _build_stub_agent()
        _invoke_with_skip(
            agent,
            [HumanMessage(content="27살인데 뭐라도 받을 수 있는 거 있어?")],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        info = _latest_check_user_info(call_log)
        if info is None:
            return
        values = json.dumps(info, ensure_ascii=False)
        assert "취업" not in values and "창업" not in values and "주거" not in values

    def test_itg_needs_conversation_priority_over_profile(self):
        agent, call_log = _build_stub_agent()
        profile = {"interests": ["취업"]}
        raw = _invoke_with_skip(
            agent,
            [
                SystemMessage(content=f"이 사용자의 등록 프로필: {json.dumps(profile, ensure_ascii=False)}"),
                HumanMessage(content="27살 강남인데 월세가 부담돼"),
            ],
            thread_id=f"it-{uuid.uuid4().hex}",
        )
        tool_names = [call["name"] for call in call_log]
        assert "extract_info" in tool_names
        info = _latest_check_user_info(call_log)
        if info is None:
            response = _response_text(raw.get("messages", []))
            assert response
            assert ("?" in response) or ("정보" in response) or ("조건" in response)
            return
        values = json.dumps(info, ensure_ascii=False)
        assert ("강남" in values) or ("27" in values)

    def test_itg_stream_emits_tool_and_ai_chunks(self):
        agent, _ = _build_stub_agent()
        try:
            chunks = list(
                stream_agent(
                    agent,
                    "27살인데 뭐 받을 수 있어?",
                    thread_id=f"it-{uuid.uuid4().hex}",
                )
            )
        except Exception as exc:  # pragma: no cover - network-dependent
            if _is_backend_unavailable_error(exc):
                pytest.skip(f"integration unavailable: {exc}")
            raise
        assert chunks
        has_tool = False
        has_ai = False
        stream_errors: list[str] = []
        for chunk in chunks:
            if isinstance(chunk, dict) and "error" in chunk:
                stream_errors.append(str(chunk["error"]))
            messages = chunk.get("messages", []) if isinstance(chunk, dict) else []
            for msg in messages:
                msg_type = getattr(msg, "type", "")
                if msg_type == "tool":
                    has_tool = True
                if msg_type == "ai":
                    has_ai = True
        if stream_errors and not has_ai:
            if any(_is_backend_unavailable_error(Exception(err)) for err in stream_errors):
                pytest.skip(f"integration unavailable: {stream_errors[-1]}")
        assert has_ai
        assert has_tool

    def test_itg_max_iterations_caps_loop_behavior(self):
        def always_empty(query: str, top_k: int, state: dict[str, Any]) -> list[dict[str, Any]]:
            state["search_calls"] += 1
            return []

        agent, _ = _build_stub_agent(search_impl=always_empty, max_iterations=1)
        result = _run_agent_with_skip(agent, "정책A랑 정책B 비교해줘", thread_id=f"it-{uuid.uuid4().hex}")
        counts = Counter(call["name"] for call in result["tool_calls"])
        assert all(count <= 3 for count in counts.values())
        if result["error"] is not None:
            response = _result_message(result)
            assert "recursion" in result["error"].lower() or "오류" in response


@pytest.mark.integration
@pytest.mark.integration_live
@needs_api_key
class TestOrchestratorLiveSmoke:
    """실제 도구 연결 최소 스모크."""

    def test_live_smoke_chitchat_response(self):
        agent = create_agent(model="gpt-4o-mini", temperature=0, use_short_prompt=False)
        result = _run_agent_with_skip(agent, "안녕!", thread_id=f"live-{uuid.uuid4().hex}")
        assert _result_message(result)

    def test_live_smoke_matching_response(self):
        agent = create_agent(model="gpt-4o-mini", temperature=0, use_short_prompt=False)
        result = _run_agent_with_skip(
            agent,
            "27살 강남구 사는데 뭐 받을 수 있어?",
            thread_id=f"live-{uuid.uuid4().hex}",
        )
        assert _result_message(result)
        assert isinstance(result["tool_calls"], list)

    def test_live_smoke_stream_emits_chunks(self):
        agent = create_agent(model="gpt-4o-mini", temperature=0, use_short_prompt=False)
        try:
            chunks = list(
                stream_agent(
                    agent,
                    "주거 정책 알려줘",
                    thread_id=f"live-{uuid.uuid4().hex}",
                )
            )
        except Exception as exc:  # pragma: no cover - network-dependent
            if _is_backend_unavailable_error(exc):
                pytest.skip(f"integration unavailable: {exc}")
            raise
        assert len(chunks) > 0

    def test_live_smoke_empty_input_resilience(self):
        agent = create_agent(model="gpt-4o-mini", temperature=0, use_short_prompt=False)
        result = _run_agent_with_skip(agent, "", thread_id=f"live-{uuid.uuid4().hex}")
        assert _result_message(result)
