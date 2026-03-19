"""
LangFuse 실제 연동 테스트 (real integration)

실행 조건:
- LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY 환경변수 필요
- OPENAI_API_KEY 환경변수 필요
- LANGFUSE_BASE_URL (없으면 cloud.langfuse.com 사용)

실행:
    pytest tests/integration_orchestrator/test_langfuse_real.py -v -m integration_live
"""
import os
import pytest
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
# handler 생성 (실제 키)
# ============================================================================

@skip_no_langfuse
@pytest.mark.integration_live
def test_real_handler_created():
    """실제 환경변수로 CallbackHandler가 생성되는지 확인."""
    from llm.services.langfuse_client import get_langfuse_handler

    handler = get_langfuse_handler(session_id="test-session", user_id="test-user")

    assert handler is not None
    print(f"\n✅ LangFuse handler 생성 성공: {type(handler).__name__}")


# ============================================================================
# agent 실행 + trace 전송
# ============================================================================

@skip_no_langfuse
@skip_no_openai
@pytest.mark.integration_live
def test_real_agent_run_with_langfuse():
    """실제 agent 실행 시 LangFuse에 trace가 전송되는지 확인."""
    from llm.agents.agent import create_agent, run_agent

    agent = create_agent(use_short_prompt=True)
    result = run_agent(agent, "안녕하세요!", thread_id="real-test-thread")

    assert result["error"] is None
    assert result["response"].message

    print(f"\n✅ Agent 응답: {result['response'].message[:100]}")
    print("👉 LangFuse UI에서 trace 확인하세요.")


@skip_no_langfuse
@pytest.mark.integration_live
def test_langfuse_trace_flushed():
    """handler flush 후 LangFuse SDK로 trace 존재 여부 확인."""
    from llm.services.langfuse_client import get_langfuse_handler

    session_id = "flush-test-session"
    handler = get_langfuse_handler(session_id=session_id)
    assert handler is not None

    # flush — 전송 대기 중인 이벤트를 즉시 전송 (v4: _langfuse_client)
    langfuse_client = getattr(handler, "_langfuse_client", None)
    assert langfuse_client is not None, "handler._langfuse_client 없음"
    langfuse_client.flush()
    print("\n✅ flush 완료 — LangFuse UI에서 trace 확인하세요.")
