"""
멀티턴 대화 품질 검증 스크립트

검증 항목:
  1. JSON 파싱 fallback 발생 여부
  2. 사용자 정보(나이/지역) 재질문 여부 (BRAIN4-68 검증)
  3. LangFuse 트레이스 자동 분석 (latency, 토큰, LLM 호출 수)

사용법:
    cd <project_root>/backend
    SEARCH_BACKEND=direct uv run python ../llm/scripts/debug_parse_fallback.py
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=False)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)

from langgraph.checkpoint.memory import MemorySaver
from llm.agents import create_agent, run_agent

# ============================================================================
# 이번 실행 고유 ID — LangFuse 트레이스 분리 식별용
# ============================================================================

RUN_ID = f"dbg-{int(time.time())}"


# ============================================================================
# 시나리오 정의
# ============================================================================

# 스크린샷 재현: 39세 멀티턴
# 확인 포인트: LLM이 JSON 앞뒤에 자연어를 붙여 fallback 유발하는지
MULTITURN_39 = [
    ("fallback_test", "다른 미국다이로 39살 래퍼 문지훈이야"),
    ("fallback_test", "한국나이로는 40살인데?"),
    ("fallback_test", "은평구 짱이야"),
    ("fallback_test", "나이 얘기했잖아"),
    ("fallback_test", "소득은 그럭저럭이야"),
    ("fallback_test", "그런건 없어 대중없이 벌거든"),
]

# 스크린샷 재현: 40세 문지훈 멀티턴 (BRAIN4-68 검증)
# 확인 포인트: 턴3 이후 나이/지역 재질문 없어야 함
MULTITURN_MUNJIHUN = [
    ("munjihun", "은평구 짱 40세 문제훈이다"),
    ("munjihun", "아니 문지훈이다"),
    ("munjihun", "40세인데 받을수 있어?"),
    ("munjihun", "뭐 문제있어?"),
    ("munjihun", "정기석 데려와봐"),
    ("munjihun", "정기석이 누군데"),
    ("munjihun", "나는 어떤걸 받을수있어"),  # ← 재질문 발생 포인트
    ("munjihun", "말해줬잖아"),
]

# 스크린샷 재현: 동대문구 22세 취준생 멀티턴 (BRAIN4-68 검증)
# 확인 포인트:
#   턴3 "동대문구 22세" 이후 → 새 정보 반영한 검색 결과 나와야 함
#   턴4 "취준생" → 나이/구 재질문 없어야 함 (이미 턴3에서 파악)
MULTITURN_DONGGDAEMUN = [
    ("donggdaemun", "주거 정책 알려줘"),
    ("donggdaemun", "취준생"),
    ("donggdaemun", "동대문구 22세"),   # ← 정보 제공, 검색 결과 바뀌어야 함
    ("donggdaemun", "취준생"),          # ← 재질문 발생 포인트 (버그 재현)
]

# 단턴 케이스
SINGLE_TURN_CASES = [
    ("st1", "39살 은평구 사는데 받을 수 있는 정책 알려줘"),
    ("st2", "19살 강남구 소득 없음"),
]

_REASK_KEYWORDS = ["나이", "거주", "구를 알려", "알려주시면", "말씀해 주시면"]


# ============================================================================
# 실행 & 결과 수집
# ============================================================================

def run_scenario(
    agent,
    turns: list[tuple[str, str]],
    label: str,
    *,
    reask_check_from: int = 0,
) -> list[dict]:
    """
    Args:
        reask_check_from: 이 인덱스(1-based) 이후 턴부터 재질문 감지 활성화.

    Returns:
        각 턴의 결과 dict 리스트 (LangFuse 분석용 thread_id 포함).
    """
    print(f"\n{'='*60}")
    print(f"시나리오: {label}")
    print(f"{'='*60}")

    records: list[dict] = []

    for i, (raw_tid, message) in enumerate(turns, 1):
        thread_id = f"{RUN_ID}-{raw_tid}"  # 이번 실행 고유 prefix
        print(f"\n--- [턴 {i}] {message!r} ---")
        t0 = time.time()
        result = run_agent(agent, message, thread_id=thread_id)
        elapsed = time.time() - t0

        response = result["response"]
        raw_text = result["raw_text"]
        is_fallback = raw_text.strip() == response.message.strip()
        is_reask = (
            reask_check_from > 0
            and i > reask_check_from
            and any(kw in response.message for kw in _REASK_KEYWORDS)
        )

        print(f"  latency    : {elapsed:.1f}s")
        print(f"  도구 호출  : {[tc['name'] for tc in result['tool_calls']]}")
        print(f"  policies   : {len(response.policies)}개")
        print(f"  raw_text[:150] : {raw_text[:150]!r}")
        print(f"  message[:150]  : {response.message[:150]!r}")

        if is_fallback:
            print(f"  ⚠️  FALLBACK — message == raw_text")
            print(f"  raw_text 전체:\n{raw_text}\n")
        else:
            print(f"  ✅ 파싱 성공")

        if is_reask:
            print(f"  🔴 재질문 감지 — 이미 파악된 정보를 다시 물어봄!")

        records.append({
            "scenario": label,
            "turn": i,
            "message": message,
            "thread_id": thread_id,
            "latency": elapsed,
            "tool_calls": [tc["name"] for tc in result["tool_calls"]],
            "policies": len(response.policies),
            "is_fallback": is_fallback,
            "is_reask": is_reask,
        })

    return records


# ============================================================================
# LangFuse 트레이스 분석
# ============================================================================

def analyze_langfuse(all_records: list[dict]) -> None:
    """실행 완료 후 LangFuse API로 트레이스를 조회해 분석 결과를 출력한다."""
    try:
        from langfuse import Langfuse
    except ImportError:
        print("\n[LangFuse] langfuse 패키지 없음 — 분석 생략")
        return

    if not (os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")):
        print("\n[LangFuse] 환경변수 미설정 — 분석 생략")
        return

    print(f"\n{'='*60}")
    print("LangFuse 트레이스 분석")
    print(f"RUN_ID: {RUN_ID}")
    print(f"{'='*60}")

    # LangFuse 클라이언트 플러시 (비동기 전송 완료 대기)
    try:
        lf = Langfuse()
        lf.flush()
    except Exception as e:
        print(f"  flush 실패: {e}")
        return

    # 트레이스가 API에 반영되기까지 잠시 대기
    print("  트레이스 전송 대기 중... (5초)")
    time.sleep(5)

    # thread_id → 시나리오명 매핑
    tid_to_scenario: dict[str, str] = {}
    for rec in all_records:
        tid_to_scenario[rec["thread_id"]] = f"{rec['scenario']} 턴{rec['turn']}"

    # 고유 thread_id 목록
    unique_tids = list(dict.fromkeys(r["thread_id"] for r in all_records))

    scenario_stats: dict[str, dict] = {}  # scenario → {latency, input_tok, output_tok, llm_calls}

    for tid in unique_tids:
        scenario_label = tid_to_scenario.get(tid, tid)
        try:
            traces_page = lf.fetch_traces(session_id=tid, limit=5)
            traces = traces_page.data if hasattr(traces_page, "data") else []
        except Exception as e:
            print(f"  [{scenario_label}] 조회 실패: {e}")
            continue

        if not traces:
            print(f"  [{scenario_label}] 트레이스 없음 (LangFuse 비활성화 또는 지연)")
            continue

        for trace in traces:
            usage = getattr(trace, "usage", None)
            input_tok  = getattr(usage, "input",  None) if usage else None
            output_tok = getattr(usage, "output", None) if usage else None
            latency_ms = getattr(trace, "latency", None)
            latency_s  = f"{latency_ms/1000:.1f}s" if latency_ms else "?"

            print(
                f"  [{scenario_label}]  latency={latency_s}"
                f"  in={input_tok}tok  out={output_tok}tok"
            )

            # 시나리오별 합산
            scen_key = scenario_label.rsplit(" 턴", 1)[0]
            s = scenario_stats.setdefault(scen_key, {"latency": 0.0, "input": 0, "output": 0, "calls": 0})
            s["calls"] += 1
            if latency_ms:
                s["latency"] += latency_ms / 1000
            if input_tok:
                s["input"] += input_tok
            if output_tok:
                s["output"] += output_tok

    # 시나리오별 요약
    if scenario_stats:
        print(f"\n  {'시나리오':<35} {'LLM호출':>6} {'총latency':>10} {'총input':>8} {'총output':>9}")
        print(f"  {'-'*35} {'-'*6} {'-'*10} {'-'*8} {'-'*9}")
        for scen, s in scenario_stats.items():
            print(
                f"  {scen:<35} {s['calls']:>6}"
                f"  {s['latency']:>8.1f}s"
                f"  {s['input']:>7}tok"
                f"  {s['output']:>8}tok"
            )


# ============================================================================
# 요약 출력
# ============================================================================

def print_summary(all_records: list[dict]) -> None:
    print(f"\n{'='*60}")
    print("전체 결과 요약")
    print(f"{'='*60}")

    by_scenario: dict[str, list[dict]] = {}
    for rec in all_records:
        by_scenario.setdefault(rec["scenario"], []).append(rec)

    for scen, recs in by_scenario.items():
        fallbacks = [r for r in recs if r["is_fallback"]]
        reasks    = [r for r in recs if r["is_reask"]]
        avg_lat   = sum(r["latency"] for r in recs) / len(recs)
        status = "✅" if not fallbacks and not reasks else "🔴"
        print(
            f"  {status} {scen:<35}"
            f" fallback={len(fallbacks)}/{len(recs)}"
            f" 재질문={len(reasks)}/{len(recs)}"
            f" avg_lat={avg_lat:.1f}s"
        )
        for r in fallbacks:
            print(f"      ↳ fallback: 턴{r['turn']} {r['message']!r}")
        for r in reasks:
            print(f"      ↳ 재질문:  턴{r['turn']} {r['message']!r}")


# ============================================================================
# main
# ============================================================================

def main():
    all_records: list[dict] = []

    # --- 시나리오 1: 39세 멀티턴 fallback 검증 ---
    agent1 = create_agent(checkpointer=MemorySaver())
    all_records += run_scenario(agent1, MULTITURN_39, "39세 멀티턴 (JSON fallback 검증)")

    # --- 시나리오 2: 40세 문지훈 (BRAIN4-68 사용자 정보 유지 검증) ---
    agent2 = create_agent(checkpointer=MemorySaver())
    all_records += run_scenario(
        agent2, MULTITURN_MUNJIHUN,
        "40세 문지훈 멀티턴 (BRAIN4-68 검증)",
        reask_check_from=3,
    )

    # --- 시나리오 3: 동대문구 22세 취준생 (BRAIN4-68 정보 업데이트 검증) ---
    agent3 = create_agent(checkpointer=MemorySaver())
    all_records += run_scenario(
        agent3, MULTITURN_DONGGDAEMUN,
        "동대문구 22세 취준생 멀티턴 (BRAIN4-68 검증)",
        reask_check_from=3,
    )

    # --- 시나리오 4: 단턴 케이스 ---
    agent4 = create_agent(checkpointer=MemorySaver())
    for raw_tid, message in SINGLE_TURN_CASES:
        all_records += run_scenario(agent4, [(raw_tid, message)], f"단턴: {message}")

    # --- 요약 ---
    print_summary(all_records)

    # --- LangFuse 트레이스 분석 ---
    analyze_langfuse(all_records)


if __name__ == "__main__":
    main()
