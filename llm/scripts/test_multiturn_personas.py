"""
멀티턴 페르소나 종합 검증 스크립트 (BRAIN4-68)

에지케이스 3 + 정상케이스 2 = 5 페르소나

검증 항목:
  - user_info store 누적 상태 (매 턴 후 출력)
  - 시스템 프롬프트 주입 여부 ([현재 파악된 사용자 정보] 블록)
  - 나이/지역 재질문 감지 (false positive 최소화)
  - JSON 파싱 fallback 감지
  - LangFuse 트레이스: latency / input tok / output tok / prompt 주입 확인

사용법:
    cd <project_root>/backend
    # 기본 (WARNING 레벨)
    SEARCH_BACKEND=direct uv run python ../llm/scripts/test_multiturn_personas.py

    # store/prompt 주입 디버그
    SEARCH_BACKEND=direct LLM_AGENT_DEBUG=1 uv run python ../llm/scripts/test_multiturn_personas.py
"""

from __future__ import annotations

import logging
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
# 프로젝트 루트 .env 로드 (LANGFUSE_* 등)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=False)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# LLM_AGENT_DEBUG=1 이면 agent.py의 DEBUG 로그 stdout으로 출력
log_level = logging.DEBUG if os.getenv("LLM_AGENT_DEBUG") == "1" else logging.WARNING
logging.basicConfig(
    level=log_level,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)

from langgraph.checkpoint.memory import MemorySaver
from llm.agents import create_agent, run_agent
from llm.agents.agent import get_user_info

RUN_ID = f"p{int(time.time())}"


# ============================================================================
# 페르소나 정의
# ============================================================================

# ── 에지케이스 1: 나이 범위 초과 (40세) ─────────────────────────────────────
# 검증: 40세임을 인지하고 청년 정책 범위 밖 안내, 재질문 없음
PERSONA_OVER_AGE = {
    "label": "[에지1] 40세 나이 범위 초과",
    "tid": "over_age",
    "reask_check_from": 2,
    "turns": [
        "은평구 40세 문지훈이야",              # turn1: 나이·지역 제공
        "받을 수 있는 복지 있어?",              # turn2: → 재질문 없어야 함
        "취준생이야",                          # turn3
        "월세 지원은?",                        # turn4
    ],
}

# ── 에지케이스 2: 정보 수정 (지역 변경) ──────────────────────────────────────
# 검증: "마포구 → 관악구" 수정 후 turn3 검색이 관악구 기준으로 되는지
PERSONA_INFO_UPDATE = {
    "label": "[에지2] 지역 정보 수정",
    "tid": "info_update",
    "reask_check_from": 3,
    "turns": [
        "25살 마포구야",                        # turn1: 나이·지역 제공
        "아 마포가 아니라 관악구야 미안",         # turn2: 지역 수정 → store 업데이트 필요
        "취준생인데 주거 지원 받을 수 있어?",     # turn3: → 관악구 기준 검색 필요
    ],
}

# ── 에지케이스 3: 비정책 발화 사이에 정보 기억 ───────────────────────────────
# 검증: turn1에서 나이·지역 제공 후 무관한 발화 사이에도 정보 유지
PERSONA_OFFTRACK = {
    "label": "[에지3] 비정책 발화 사이 정보 기억",
    "tid": "offtrack",
    "reask_check_from": 4,
    "turns": [
        "29살 강서구야",                        # turn1: 나이·지역 제공
        "오늘 날씨 어때?",                      # turn2: 무관한 발화
        "치킨 추천해줘",                        # turn3: 무관한 발화
        "취준생인데 받을 수 있는 거 있어?",      # turn4: → 재질문 없어야 함
    ],
}

# ── 정상케이스 1: 완전 정보 단일 발화 ────────────────────────────────────────
# 검증: 나이·지역·소득 포함 단일 발화 → 즉시 정책 카드 반환
PERSONA_COMPLETE = {
    "label": "[정상1] 완전 정보 단일 발화",
    "tid": "complete",
    "reask_check_from": 0,
    "turns": [
        "27살 강남구 취준생이야 소득 없어 월세 지원 받고 싶어",
    ],
}

# ── 정상케이스 2: 멀티턴 정보 누적 ───────────────────────────────────────────
# 검증: 턴마다 정보 한 조각씩 제공 → 마지막 턴에서 누적된 정보로 검색
PERSONA_GRADUAL = {
    "label": "[정상2] 멀티턴 정보 누적",
    "tid": "gradual",
    "reask_check_from": 5,
    "turns": [
        "안녕",                               # turn1: 빈 정보
        "34살이야",                            # turn2: 나이 제공
        "노원구",                              # turn3: 지역 제공
        "소득 없어 취준생",                    # turn4: 고용·소득 제공
        "받을 수 있는 복지 있어?",             # turn5: → 재질문 없어야 함
    ],
}

# ── BRAIN4-72 케이스 1: 58년생 멀티턴 재요청 (가드레일 우회 시도) ────────────
# 검증: 모든 턴에서 search_policies 미호출, policies 0개
PERSONA_SCOPE_ADULT = {
    "label": "[BRAIN4-72-1] 58년생 서비스 범위 외 재요청",
    "tid": "scope_adult",
    "reask_check_from": 0,
    "scope_guard_check": True,     # 이 페르소나는 scope guard 검증
    "turns": [
        "58년 개띠 왕십리 사는 오명규 사장이다",       # turn1: 나이 범위 외 제공
        "연령대가 안 맞아도 받을 수 있는 게 있지 않나?",  # turn2: 재요청
        "당 찾아와",                                  # turn3: 강제 검색 시도
    ],
}

# ── BRAIN4-72 케이스 2: 12세 동일 턴 search_policies 호출 (스크린샷 재현) ───
# 검증: extract_info(age=12) → 같은 턴 search_policies 차단
PERSONA_SCOPE_CHILD = {
    "label": "[BRAIN4-72-2] 12세 동일 턴 정책 검색 차단",
    "tid": "scope_child",
    "reask_check_from": 0,
    "scope_guard_check": True,
    "turns": [
        "나는 12세 송정초등학교 짱 김하온이다",   # turn1: age=12 추출 → 즉시 차단 필요
        "내일 맞짱뜨러간다",                    # turn2
        "입자리를 구해야한다",                  # turn3: 이 턴에서 정책 카드 미노출이어야 함
    ],
}

ALL_PERSONAS = [
    PERSONA_OVER_AGE,
    PERSONA_INFO_UPDATE,
    PERSONA_OFFTRACK,
    PERSONA_COMPLETE,
    PERSONA_GRADUAL,
    PERSONA_SCOPE_ADULT,
    PERSONA_SCOPE_CHILD,
]

# 나이/지역을 직접 묻는 패턴만 re-ask로 판정 (false positive 최소화)
_REASK_PATTERNS = [
    "나이와 거주",
    "나이를 알려",
    "나이가 어떻게",
    "구를 알려주",
    "거주하시는 구",
    "어느 구에 사",
    "어떤 구에 사",
    "살고 계신 구",
    "거주 중인 구",
    "나이와 어느",
]


# ============================================================================
# 실행 & 수집
# ============================================================================

def run_persona(agent, persona: dict) -> list[dict]:
    label = persona["label"]
    raw_tid = persona["tid"]
    reask_from = persona["reask_check_from"]
    scope_guard_check = persona.get("scope_guard_check", False)
    turns = persona["turns"]
    thread_id = f"{RUN_ID}-{raw_tid}"

    print(f"\n{'='*60}")
    print(f"페르소나: {label}")
    print(f"thread_id: {thread_id}")
    print(f"{'='*60}")

    records: list[dict] = []

    for i, message in enumerate(turns, 1):
        print(f"\n--- [턴{i}] {message!r} ---")
        t0 = time.time()
        result = run_agent(agent, message, thread_id=thread_id)
        elapsed = time.time() - t0

        # store 상태 확인 (이번 턴 invoke 완료 후)
        store_state = get_user_info(thread_id)

        response = result["response"]
        raw_text = result["raw_text"]
        # scope_guard 페르소나는 거절 응답이 예상된 동작 → fallback으로 카운트하지 않음
        is_fallback = raw_text.strip() == response.message.strip() and not scope_guard_check
        tool_names = [tc["name"] for tc in result["tool_calls"]]
        is_reask = (
            reask_from > 0
            and i > reask_from
            and any(p in response.message for p in _REASK_PATTERNS)
        )
        # scope guard 위반: 범위 외 사용자임에도 search_policies 호출 또는 정책 카드 반환
        is_scope_violation = scope_guard_check and (
            "search_policies" in tool_names or len(response.policies) > 0
        )

        print(f"  latency    : {elapsed:.1f}s")
        print(f"  tools      : {tool_names}")
        print(f"  policies   : {len(response.policies)}개")
        print(f"  store      : {store_state}")
        print(f"  message    : {response.message[:200]!r}")

        if is_fallback:
            print("  ⚠️  FALLBACK — JSON 파싱 실패")
        else:
            print("  ✅ JSON 파싱 성공")

        if reask_from > 0 and i > reask_from:
            if is_reask:
                print("  🔴 재질문 감지 — 나이/지역을 다시 물어봄!")
            else:
                print("  ✅ 재질문 없음")

        if scope_guard_check:
            if is_scope_violation:
                print("  🔴 SCOPE GUARD 위반 — 범위 외 사용자에게 정책 결과 반환!")
            else:
                print("  ✅ SCOPE GUARD 정상 — 정책 검색/카드 차단")

        records.append({
            "persona": label,
            "turn": i,
            "tid": raw_tid,
            "thread_id": thread_id,
            "message": message,
            "latency": elapsed,
            "tools": tool_names,
            "policies": len(response.policies),
            "store": dict(store_state),
            "is_fallback": is_fallback,
            "is_reask": is_reask,
            "is_scope_violation": is_scope_violation,
        })

    return records


# ============================================================================
# 요약
# ============================================================================

def print_summary(all_records: list[dict]) -> None:
    print(f"\n{'='*60}")
    print("전체 결과 요약")
    print(f"{'='*60}")

    by_persona: dict[str, list[dict]] = {}
    for rec in all_records:
        by_persona.setdefault(rec["persona"], []).append(rec)

    print(f"\n  {'페르소나':<38} {'턴수':>4} {'fallback':>9} {'재질문':>7} {'scope위반':>9} {'avg_lat':>8}")
    print(f"  {'-'*38} {'-'*4} {'-'*9} {'-'*7} {'-'*9} {'-'*8}")

    for label, recs in by_persona.items():
        fallbacks  = sum(1 for r in recs if r["is_fallback"])
        reasks     = sum(1 for r in recs if r["is_reask"])
        violations = sum(1 for r in recs if r.get("is_scope_violation"))
        avg_lat    = sum(r["latency"] for r in recs) / len(recs)
        status = "✅" if fallbacks == 0 and reasks == 0 and violations == 0 else "🔴"
        print(
            f"  {status} {label:<36} {len(recs):>4}"
            f"  {fallbacks}/{len(recs):>2}      "
            f"  {reasks}/{len(recs):>2}"
            f"  {violations}/{len(recs):>2}      "
            f"  {avg_lat:>6.1f}s"
        )

    # 실패 상세
    failed = [r for recs in by_persona.values() for r in recs
              if r["is_fallback"] or r["is_reask"] or r.get("is_scope_violation")]
    if failed:
        print("\n  실패 상세:")
        for r in failed:
            tags = []
            if r["is_fallback"]: tags.append("FALLBACK")
            if r["is_reask"]: tags.append("재질문")
            if r.get("is_scope_violation"): tags.append("SCOPE위반")
            tag = " ".join(tags)
            print(f"    [{r['persona']} 턴{r['turn']}] {tag}: {r['message']!r}")
            print(f"      store: {r['store']}, tools: {r['tools']}, policies: {r['policies']}")


# ============================================================================
# LangFuse 트레이스 분석
# ============================================================================

def _langfuse_api_get(path: str, params: dict | None = None) -> dict | None:
    """LangFuse v4 REST API GET 헬퍼. 인증 실패/네트워크 오류 시 None 반환."""
    import base64
    import json
    import urllib.parse
    import urllib.request

    pk   = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk   = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = (os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST") or "https://cloud.langfuse.com").rstrip("/")
    if not pk or not sk:
        return None

    creds   = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    url     = f"{host}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {creds}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return None


def analyze_langfuse(all_records: list[dict]) -> None:
    """LangFuse v4 REST API로 트레이스를 조회해 분석 결과를 출력한다."""
    if not (os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")):
        print("\n[LangFuse] 환경변수 미설정 — 분석 생략 (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY 확인)")
        return

    # v4 SDK flush
    try:
        from langfuse import get_client
        lf = get_client()
        lf.flush()
    except Exception:
        pass

    print(f"\n{'='*60}")
    print(f"LangFuse 트레이스 분석  (RUN_ID={RUN_ID})")
    print(f"{'='*60}")
    print("  트레이스 전송 대기 (5초)...")
    time.sleep(5)

    persona_stats: dict[str, dict] = {}

    print(f"\n  {'session_id (tail)':<32} {'턴':>3} {'n':>3} {'avg_lat':>8} {'avg_in':>7} {'avg_out':>8} {'주입률':>6}")
    print(f"  {'-'*32} {'-'*3} {'-'*3} {'-'*8} {'-'*7} {'-'*8} {'-'*6}")

    seen_tids: set[str] = set()
    for rec in all_records:
        tid     = rec["thread_id"]
        persona = rec["persona"]
        turn    = rec["turn"]
        if tid in seen_tids:
            continue
        seen_tids.add(tid)

        # GET /api/public/traces?sessionId=<tid>
        data = _langfuse_api_get("/api/public/traces", {"sessionId": tid, "limit": 50})
        if data is None:
            print(f"  [{tid[-30:]:<30}] API 조회 실패")
            continue

        traces = data.get("data", [])
        if not traces:
            print(f"  [{tid[-30:]:<30}] 트레이스 없음 (지연 또는 미전송)")
            continue

        n          = len(traces)
        total_lat  = sum((t.get("latency") or 0) / 1000 for t in traces)
        total_in   = sum(t.get("usage", {}).get("input",  0) or 0 for t in traces)
        total_out  = sum(t.get("usage", {}).get("output", 0) or 0 for t in traces)
        inj_count  = sum(1 for t in traces if _check_prompt_injection_v4(t))

        avg_lat = total_lat / n if n else 0
        avg_in  = total_in  // n if n else 0
        avg_out = total_out // n if n else 0
        inj_rate = f"{inj_count}/{n}"

        short_tid = tid[-32:]
        print(
            f"  {short_tid:<32} {turn:>3} {n:>3}"
            f"  {avg_lat:>6.1f}s"
            f"  {avg_in:>7}"
            f"  {avg_out:>8}"
            f"  {inj_rate:>6}"
        )

        s = persona_stats.setdefault(persona, {"lat": 0.0, "in": 0, "out": 0, "n": 0, "inj": 0, "sessions": 0})
        s["sessions"] += 1
        s["n"]    += n
        s["lat"]  += total_lat
        s["in"]   += total_in
        s["out"]  += total_out
        s["inj"]  += inj_count

    # 페르소나별 요약
    if persona_stats:
        print(f"\n  {'페르소나':<38} {'LLM호출':>6} {'총lat':>7} {'총in':>7} {'총out':>8} {'주입수':>6}")
        print(f"  {'-'*38} {'-'*6} {'-'*7} {'-'*7} {'-'*8} {'-'*6}")
        for label, s in persona_stats.items():
            print(
                f"  {label:<38} {s['n']:>6}"
                f"  {s['lat']:>5.1f}s"
                f"  {s['in']:>7}"
                f"  {s['out']:>8}"
                f"  {s['inj']:>4}/{s['n']}"
            )
    else:
        print("\n  트레이스를 가져오지 못했습니다. LangFuse 대시보드에서 직접 확인하세요.")
        print(f"  세션 ID 목록:")
        for rec in all_records:
            if rec["turn"] == 1:
                print(f"    - {rec['thread_id']}")


def _check_prompt_injection_v4(trace: dict) -> bool:
    """트레이스 dict에서 [현재 파악된 사용자 정보] 블록 존재 여부 확인."""
    try:
        return "[현재 파악된 사용자 정보]" in str(trace.get("input", ""))
    except Exception:
        return False


# ============================================================================
# main
# ============================================================================

def main():
    all_records: list[dict] = []

    for persona in ALL_PERSONAS:
        agent = create_agent(checkpointer=MemorySaver())
        all_records += run_persona(agent, persona)

    print_summary(all_records)
    analyze_langfuse(all_records)


if __name__ == "__main__":
    main()
