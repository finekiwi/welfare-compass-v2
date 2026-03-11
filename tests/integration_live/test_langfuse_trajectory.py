"""
LangFuse trajectory 확인용 integration_live 테스트

목적:
    실제 OpenAI API + 실제 LangFuse 전송으로 도구 호출 체인(trajectory)을 UI에서 시각적으로 확인

실행:
    pytest tests/integration_live/test_langfuse_trajectory.py -v -s -m integration_live

주의:
    - OPENAI_API_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY 환경변수 필요
    - DB/ChromaDB 의존성 없음 (search_policies는 mock)
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()

LANGFUSE_KEYS_PRESENT = bool(
    os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")
)
OPENAI_KEY_PRESENT = bool(os.getenv("OPENAI_API_KEY"))

skip_no_langfuse = pytest.mark.skipif(
    not LANGFUSE_KEYS_PRESENT,
    reason="LANGFUSE_SECRET_KEY / LANGFUSE_PUBLIC_KEY 환경변수 없음",
)
skip_no_openai = pytest.mark.skipif(
    not OPENAI_KEY_PRESENT,
    reason="OPENAI_API_KEY 환경변수 없음",
)

# ============================================================================
# Mock 데이터
# ============================================================================

MOCK_POLICIES = [
    {
        "policy_id": "MOCK-001",
        "title": "청년 월세 지원",
        "description": "만 19~34세 청년에게 월 최대 20만원 월세 지원",
        "category": "주거",
        "district": "서울시 전체",
        "age_min": 19,
        "age_max": 34,
        "apply_url": "https://youth.seoul.go.kr",
    },
    {
        "policy_id": "MOCK-002",
        "title": "청년 취업 장려금",
        "description": "취업 준비 청년에게 최대 300만원 지원",
        "category": "취업",
        "district": "서울시 전체",
        "age_min": 18,
        "age_max": 39,
        "apply_url": "https://job.seoul.go.kr",
    },
    {
        "policy_id": "MOCK-003",
        "title": "청년 주거 안정 보증금 대출",
        "description": "중위소득 150% 이하 청년 대상 보증금 대출 지원",
        "category": "주거",
        "district": "서울시 전체",
        "age_min": 19,
        "age_max": 39,
        "apply_url": "https://housing.seoul.go.kr",
    },
]

MOCK_SEARCH_RESULT = {
    "policies": MOCK_POLICIES,
    "original_query": "mock query",
    "rewritten_query": "mock query",
    "result_count": len(MOCK_POLICIES),
}

MOCK_EMPTY_RESULT = {
    "policies": [],
    "original_query": "mock query",
    "rewritten_query": "mock query",
    "result_count": 0,
}


def _mock_policy_fetcher(policy_ids):
    """check_eligibility용 mock fetcher — MOCK_POLICIES 반환."""
    return MOCK_POLICIES


def _make_mock_backend(search_result: dict):
    """search_policies용 mock backend 생성."""
    backend = MagicMock()
    backend.search.return_value = search_result
    return backend


def _flush_langfuse(handler):
    """LangFuse 대기 중인 이벤트 즉시 전송."""
    client = getattr(handler, "_langfuse_client", None)
    if client and hasattr(client, "flush"):
        client.flush()


# ============================================================================
# 테스트
# ============================================================================

@skip_no_langfuse
@skip_no_openai
@pytest.mark.integration_live
def test_trajectory_info_extraction():
    """
    extract_info 호출 trajectory 확인

    쿼리: 나이/지역/관심사 포함 → 오케스트레이터가 extract_info 호출
    search_policies: 빈 결과 반환 (DB 불필요)
    LangFuse에서 extract_info 호출 trace 확인 목적
    """
    session_id = "trajectory-extract-001"

    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()

    from llm.agents.agent import create_agent, run_agent

    mock_backend = _make_mock_backend(MOCK_EMPTY_RESULT)

    with patch("llm.agents.agent.get_langfuse_handler", return_value=handler), \
         patch("llm.agents.tools.search_policies.get_search_backend", return_value=mock_backend):

        agent = create_agent(use_short_prompt=True, policy_fetcher=_mock_policy_fetcher)
        result = run_agent(
            agent,
            "저 25살이고 강남구에 살아요. 취업 준비 중인데 지원받을 수 있는 거 있을까요?",
            thread_id=session_id,
        )

    _flush_langfuse(handler)

    assert result["error"] is None
    print(f"\n✅ 응답: {result['response'].message[:100]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")


@skip_no_langfuse
@skip_no_openai
@pytest.mark.integration_live
def test_trajectory_search_chain():
    """
    extract_info → search_policies 호출 체인 trajectory 확인

    쿼리: 주거 지원 관련 일상어 → extract_info 후 search_policies 호출 유도
    search_policies: 빈 결과 반환 (DB 불필요)
    LangFuse에서 두 도구가 순서대로 호출되는 trace 확인 목적
    """
    session_id = "trajectory-search-002"

    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()

    from llm.agents.agent import create_agent, run_agent

    mock_backend = _make_mock_backend(MOCK_EMPTY_RESULT)

    with patch("llm.agents.agent.get_langfuse_handler", return_value=handler), \
         patch("llm.agents.tools.search_policies.get_search_backend", return_value=mock_backend):

        agent = create_agent(use_short_prompt=True, policy_fetcher=_mock_policy_fetcher)
        result = run_agent(
            agent,
            "월세 좀 도와주는 거 없나",
            thread_id=session_id,
        )

    _flush_langfuse(handler)

    assert result["error"] is None
    print(f"\n✅ 응답: {result['response'].message[:100]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")


@skip_no_langfuse
@skip_no_openai
@pytest.mark.integration_live
def test_trajectory_multi_tool_chain():
    """
    extract_info → search_policies → check_eligibility 전체 체인 trajectory 확인

    쿼리: 나이/지역/소득/복합 관심사 포함 → 전체 도구 체인 유도
    search_policies: mock 정책 3개 반환
    check_eligibility: mock fetcher로 적합/부적합 결과 반환
    LangFuse에서 전체 도구 호출 체인 + 최종 응답 생성 trace 확인 목적
    """
    session_id = "trajectory-multi-003"

    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()

    from llm.agents.agent import create_agent, run_agent

    mock_backend = _make_mock_backend(MOCK_SEARCH_RESULT)

    with patch("llm.agents.agent.get_langfuse_handler", return_value=handler), \
         patch("llm.agents.tools.search_policies.get_search_backend", return_value=mock_backend):

        agent = create_agent(use_short_prompt=True, policy_fetcher=_mock_policy_fetcher)
        result = run_agent(
            agent,
            "28살 마포구 사는데 편의점 알바로 월 80만원 정도 벌어요. 주거 지원이랑 취업 지원 둘 다 알려주세요",
            thread_id=session_id,
        )

    _flush_langfuse(handler)

    assert result["error"] is None
    print(f"\n✅ 응답: {result['response'].message[:150]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")
