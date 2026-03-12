"""
LangFuse 풀 파이프라인 trace 확인용 End-to-End 테스트

목적:
    mock 없이 실제 PostgreSQL + ChromaDB + OpenAI + LangFuse로
    전체 도구 호출 체인을 UI에서 시각적으로 확인

전제조건:
    - 로컬 PostgreSQL 실행 중 + 정책 데이터 seed 완료
    - ChromaDB 컬렉션 빌드 완료 (DirectSearchBackend 사용)
    - .env에 DB 연결 + OPENAI + LANGFUSE 환경변수 모두 설정

실행:
    pytest tests/integration_live/test_langfuse_e2e.py -v -s -m integration_live

주의:
    - 실제 API 비용 발생 (3개 테스트 예상: ~$0.01 이내)
    - CI에서 돌리지 않음 (로컬 전용)
"""
from __future__ import annotations

import os
import sys
import time
import pytest
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ============================================================================
# 전제조건 체크
# ============================================================================

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


def _setup_django() -> bool:
    """Django 초기화. 실패 시 False 반환."""
    try:
        backend_path = str(Path(__file__).resolve().parents[2] / "backend")
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django
        django.setup()
        return True
    except Exception:
        return False


DJANGO_AVAILABLE = _setup_django()

skip_no_django = pytest.mark.skipif(
    not DJANGO_AVAILABLE,
    reason="Django 초기화 실패 — 로컬 PostgreSQL + seed 완료 후 실행",
)


# ============================================================================
# 실제 policy_fetcher (Django ORM)
# ============================================================================

def _fetch_policies(policy_ids: list[str] | None) -> list[dict]:
    """Django ORM으로 실제 DB에서 정책 조회."""
    from policies.models import Policy

    queryset = Policy.objects.all()
    if policy_ids:
        queryset = queryset.filter(policy_id__in=policy_ids)

    return list(
        queryset.values(
            "policy_id", "title", "category", "description",
            "support_content", "apply_url", "apply_end_date",
            "age_min", "age_max", "income_level", "income_max", "district",
        )
    )


# ============================================================================
# 헬퍼
# ============================================================================

def _flush_langfuse() -> None:
    try:
        from langfuse import get_client
        get_client().flush()
    except Exception:
        pass


# ============================================================================
# 테스트
# ============================================================================

@skip_no_langfuse
@skip_no_openai
@skip_no_django
@pytest.mark.integration_live
def test_e2e_simple_eligibility_check():
    """
    extract_info → search_policies(실제 검색) → check_eligibility → 응답 생성

    쿼리: 나이/지역/취업 관심사 포함
    LangFuse: 전체 도구 호출 체인 + 각 단계 토큰/레이턴시 확인
    """
    session_id = "e2e-simple-001"

    from llm.agents.agent import create_agent, run_agent

    t0 = time.time()
    agent = create_agent(use_short_prompt=True, policy_fetcher=_fetch_policies, max_iterations=10)
    result = run_agent(
        agent,
        "저 25살이고 강남구에 살아요. 취업 준비 중인데 지원받을 수 있는 거 있을까요?",
        thread_id=session_id,
    )
    elapsed = time.time() - t0

    _flush_langfuse()

    assert result["error"] is None
    assert result["response"].message.strip() != ""

    print(f"\n⏱ 소요시간: {elapsed:.1f}s")
    print(f"✅ 응답: {result['response'].message[:100]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")


@skip_no_langfuse
@skip_no_openai
@skip_no_django
@pytest.mark.integration_live
def test_e2e_housing_support():
    """
    주거 카테고리 정책 검색 + 자격 판단

    쿼리: 주거 관련 일상어 + 나이/지역
    assert: 응답에 정책명이 1개 이상 포함
    """
    session_id = "e2e-housing-002"

    from llm.agents.agent import create_agent, run_agent

    t0 = time.time()
    agent = create_agent(use_short_prompt=True, policy_fetcher=_fetch_policies, max_iterations=10)
    result = run_agent(
        agent,
        "월세 좀 도와주는 거 없나? 나 27살이고 관악구 살아",
        thread_id=session_id,
    )
    elapsed = time.time() - t0

    _flush_langfuse()

    assert result["error"] is None
    assert result["response"].message.strip() != ""

    print(f"\n⏱ 소요시간: {elapsed:.1f}s")
    print(f"✅ 응답: {result['response'].message[:100]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")


@skip_no_langfuse
@skip_no_openai
@skip_no_django
@pytest.mark.integration_live
def test_e2e_complex_multi_need():
    """
    전체 체인 — 복합 needs (주거 + 취업) trajectory

    쿼리: 나이/지역/소득/복합 관심사 포함
    기대: extract_info에서 needs 2개 추출 → 검색 → 자격 판단 → 종합 응답
    LangFuse: 도구 호출 횟수/순서 확인 (가장 복잡한 trajectory)
    """
    session_id = "e2e-multi-003"

    from llm.agents.agent import create_agent, run_agent

    t0 = time.time()
    agent = create_agent(use_short_prompt=True, policy_fetcher=_fetch_policies, max_iterations=10)
    result = run_agent(
        agent,
        "28살 마포구 사는데 알바하면서 월 150만원 벌어요. 주거 지원이랑 취업 지원 둘 다 알려주세요",
        thread_id=session_id,
    )
    elapsed = time.time() - t0

    _flush_langfuse()

    assert result["error"] is None
    assert result["response"].message.strip() != ""

    print(f"\n⏱ 소요시간: {elapsed:.1f}s")
    print(f"✅ 응답: {result['response'].message[:100]}")
    print(f"🔧 호출된 도구: {[tc['name'] for tc in result['tool_calls']]}")
    print(f"👉 LangFuse UI에서 session '{session_id}' 확인하세요.")
