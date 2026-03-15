"""
테스트 쿼리 실행 + LangFuse 트레이스 분석 스크립트

사용법:
    cd <project_root>/backend
    python ../llm/scripts/run_test_queries.py

환경변수 (.env):
    OPENAI_API_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL
"""

from __future__ import annotations

import datetime
import os
import sys
import time

# backend, project root를 sys.path에 추가
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BACKEND_DIR)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from langgraph.checkpoint.memory import MemorySaver

from llm.agents import create_agent, run_agent

# ============================================================================
# 설정
# ============================================================================

QUERIES: list[tuple[str, str]] = [
    ("q1", "25살 강남 취준생 지원금 알려줘"),
    ("q2", "월세 지원 받을 수 있어?"),
    ("q3", "청년 창업 지원금 종류"),
]

LANGFUSE_WAIT_SECONDS = 5
LANGFUSE_LOOKBACK_MINUTES = 10


# ============================================================================
# 에이전트 실행
# ============================================================================

def run_queries() -> dict[str, dict]:
    agent = create_agent(checkpointer=MemorySaver())
    results = {}

    for thread_id, q in QUERIES:
        print(f"\n=== [{thread_id}] {q} ===")
        t0 = time.time()
        result = run_agent(agent, q, thread_id=thread_id)
        elapsed = time.time() - t0

        tool_names = [tc["name"] for tc in result["tool_calls"]]
        policy_count = len(result["response"].policies)

        print(f"도구 호출: {tool_names}")
        print(f"policies: {policy_count}개")
        print(f"로컬 latency: {elapsed:.1f}s")

        results[thread_id] = {
            "q": q,
            "elapsed": elapsed,
            "tool_calls": tool_names,
            "policy_count": policy_count,
            "error": result["error"],
        }

    return results


# ============================================================================
# LangFuse 트레이스 분석
# ============================================================================

def fetch_and_print_traces(cutoff: datetime.datetime) -> None:
    try:
        from langfuse import Langfuse
    except ImportError:
        print("\n[LangFuse] langfuse 패키지 없음 — 트레이스 분석 스킵")
        return

    if not (os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")):
        print("\n[LangFuse] 환경변수 없음 — 트레이스 분석 스킵")
        return

    print(f"\n[LangFuse] 트레이스 fetch 중... {LANGFUSE_WAIT_SECONDS}초 대기")
    time.sleep(LANGFUSE_WAIT_SECONDS)

    lf = Langfuse()
    lf.flush()

    recent = lf.api.trace.list(limit=30)
    matched = [t for t in recent.data if t.timestamp > cutoff]
    print(f"최근 {LANGFUSE_LOOKBACK_MINUTES}분 트레이스: {len(matched)}개\n")

    for t in matched:
        print(f"--- trace: {t.id[:8]}... | session: {t.session_id} | total: {t.latency:.1f}s ---")
        try:
            detail = lf.api.trace.get(t.id)
        except Exception as e:
            print(f"  (fetch 실패: {e})")
            continue

        # LLM 호출만 추출 (시간순)
        llm_calls = [
            o for o in detail.observations
            if o.name == "ChatOpenAI" and o.usage and o.start_time
        ]
        llm_calls.sort(key=lambda o: o.start_time)

        if llm_calls:
            print(f"  LLM 호출 {len(llm_calls)}회:")
            for i, obs in enumerate(llm_calls):
                u = obs.usage
                input_tok = getattr(u, "input", None) or "?"
                output_tok = getattr(u, "output", None) or "?"
                bar = "█" * min(int(obs.latency), 30)
                print(
                    f"    [{i+1}] {obs.latency:5.1f}s  "
                    f"in={input_tok}tok  out={output_tok}tok  {bar}"
                )
        else:
            # LLM 호출 없으면 전체 span top5
            spans = sorted(
                [o for o in detail.observations if o.latency and o.name],
                key=lambda o: o.latency,
                reverse=True,
            )
            for obs in spans[:5]:
                bar = "█" * min(int(obs.latency), 30)
                print(f"  {obs.name[:35]:<35} {obs.latency:5.1f}s  {bar}")

        print()


# ============================================================================
# 메인
# ============================================================================

if __name__ == "__main__":
    start_time = datetime.datetime.now(datetime.timezone.utc)
    cutoff = start_time - datetime.timedelta(minutes=1)  # 실행 직전부터

    print("=" * 60)
    print("복지나침반 테스트 쿼리 실행")
    print("=" * 60)

    results = run_queries()

    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)
    for thread_id, r in results.items():
        status = "❌ ERROR" if r["error"] else f"✅ {r['policy_count']}개"
        print(f"  [{thread_id}] {r['elapsed']:5.1f}s  {status}  도구: {r['tool_calls']}")

    fetch_and_print_traces(cutoff)
