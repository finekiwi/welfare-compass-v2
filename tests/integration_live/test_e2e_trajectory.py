"""
End-to-End trajectory 테스트 (실제 MCP 서버 + 실제 DB)

목적:
    mock 없이 실제 MCP 검색 서버 + 실제 OpenAI API + 실제 LangFuse로
    전체 도구 호출 체인을 UI에서 시각적으로 확인

실행 전 .env 설정:
    SEARCH_BACKEND=mcp
    MCP_HOST=100.69.81.51
    MCP_PORT=8001
    OPENAI_API_KEY=...
    LANGFUSE_SECRET_KEY=...
    LANGFUSE_PUBLIC_KEY=...

실행:
    pytest tests/integration_live/test_e2e_trajectory.py -v -s -m integration_live
"""
import os
import pytest
from unittest.mock import patch
from dotenv import load_dotenv

load_dotenv()

LANGFUSE_KEYS_PRESENT = bool(
    os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")
)
OPENAI_KEY_PRESENT = bool(os.getenv("OPENAI_API_KEY"))
MCP_BACKEND = (os.getenv("SEARCH_BACKEND") or "").strip().lower() == "mcp"

skip_no_langfuse = pytest.mark.skipif(
    not LANGFUSE_KEYS_PRESENT,
    reason="LANGFUSE_SECRET_KEY / LANGFUSE_PUBLIC_KEY 환경변수 없음",
)
skip_no_openai = pytest.mark.skipif(
    not OPENAI_KEY_PRESENT,
    reason="OPENAI_API_KEY 환경변수 없음",
)
skip_no_mcp = pytest.mark.skipif(
    not MCP_BACKEND,
    reason="SEARCH_BACKEND=mcp 환경변수 없음 — .env에 SEARCH_BACKEND=mcp 추가 후 실행",
)


def _flush_langfuse(handler):
    client = getattr(handler, "_langfuse_client", None)
    if client and hasattr(client, "flush"):
        client.flush()


# ============================================================================
# 테스트
# ============================================================================

@skip_no_langfuse
@skip_no_openai
@skip_no_mcp
@pytest.mark.integration_live
def test_e2e_info_extraction():
    """
    extract_info → check_eligibility 체인 (실제 DB)

    쿼리: 나이/지역 포함 → extract_info 호출 후 check_eligibility
    """
    session_id = "e2e-extract-001"

    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()

    from llm.agents.agent import create_agent, run_agent

    with patch("llm.agents.agent.get_langfuse_handler", return_value=handler):
        agent = create_agent(use_short_prompt=True)
        result = run_agent(
            agent,
            "저 25살이고 강남구에 살아요. 취업 준비 중인데 지원받을 수 있는 거 있을까요?",
            thread_id=session_id,
        )

    _flush_langfuse(handler)

    assert result["error"] is None
    print(f"\n✅ 응답: {result['response'].message[:150]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")


@skip_no_langfuse
@skip_no_openai
@skip_no_mcp
@pytest.mark.integration_live
def test_e2e_search_chain():
    """
    extract_info → search_policies → check_eligibility 체인 (실제 MCP 검색)

    쿼리: 주거 지원 관련 일상어 → 실제 MCP 서버로 검색
    """
    session_id = "e2e-search-002"

    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()

    from llm.agents.agent import create_agent, run_agent

    with patch("llm.agents.agent.get_langfuse_handler", return_value=handler):
        agent = create_agent(use_short_prompt=True)
        result = run_agent(
            agent,
            "월세 좀 도와주는 거 없나",
            thread_id=session_id,
        )

    _flush_langfuse(handler)

    assert result["error"] is None
    print(f"\n✅ 응답: {result['response'].message[:150]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")


@skip_no_langfuse
@skip_no_openai
@skip_no_mcp
@pytest.mark.integration_live
def test_e2e_multi_tool_chain():
    """
    전체 도구 체인 (실제 MCP 검색 + 실제 자격 판정)

    쿼리: 나이/지역/소득/복합 관심사 → 전체 체인 유도
    LangFuse에서 전체 trajectory + 최종 응답 생성 확인
    """
    session_id = "e2e-multi-003"

    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()

    from llm.agents.agent import create_agent, run_agent

    with patch("llm.agents.agent.get_langfuse_handler", return_value=handler):
        agent = create_agent(use_short_prompt=True)
        result = run_agent(
            agent,
            "28살 마포구 사는데 편의점 알바로 월 80만원 정도 벌어요. 주거 지원이랑 취업 지원 둘 다 알려주세요",
            thread_id=session_id,
        )

    _flush_langfuse(handler)

    assert result["error"] is None
    print(f"\n✅ 응답: {result['response'].message[:200]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")
