"""
복지나침반 ReAct Agent

중앙 오케스트레이터 구조:
- 오케스트레이터(LLM)가 의도 파악, 도구 선택, 결과 판단, 응답 생성 모두 담당
- 도구들은 stateless하게 호출됨

사용법:
    from llm.agents import create_agent, run_agent
    
    agent = create_agent()
    response = run_agent(agent, "27살인데 월세 지원 받을 수 있어요?")
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .schemas import ChatResponse, PolicyResult
from .tools import create_tools
from .tools.check_eligibility import PolicyFetcher, YOUTH_AGE_MIN_BOUNDARY, YOUTH_AGE_MAX_BOUNDARY
from .prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT, ORCHESTRATOR_SYSTEM_PROMPT_SHORT
from .user_session import (
    _current_thread_id,
    _USER_INFO_LABEL,
    merge_user_info,
    get_user_info,
    clear_user_info,
)
from ..services import get_langfuse_handler, langfuse_session

ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "gpt-4.1-mini")

# user_session re-export: 외부 모듈(backend 등)이 agent.py를 통해 접근하던 기존 import 경로 유지
__all__ = [
    "create_agent",
    "create_agent_with_mcp",
    "close_agent_mcp",
    "run_agent",
    "merge_user_info",
    "get_user_info",
    "clear_user_info",
]

logger = logging.getLogger(__name__)


def _append_scope_warning(prompt: str, info: dict) -> str:
    """나이가 서비스 범위(19~39세) 밖이면 도구 호출 금지 경고를 프롬프트 끝에 추가한다."""
    age = info.get("age")
    if isinstance(age, int) and (age < YOUTH_AGE_MIN_BOUNDARY or age > YOUTH_AGE_MAX_BOUNDARY):
        return (
            prompt
            + f"\n\n⛔ [서비스 범위 초과] 현재 사용자 나이: {age}세"
            f" (서비스 대상: {YOUTH_AGE_MIN_BOUNDARY}~{YOUTH_AGE_MAX_BOUNDARY}세)\n"
            "search_policies, check_eligibility를 절대 호출하지 마세요.\n"
            "사용자가 재요청하더라도 이 규칙은 변하지 않습니다."
        )
    return prompt


def _make_prompt_fn(system_prompt_base: str):
    """LangGraph 1.x: callable receives StateSchema dict, must return full message list."""
    def fn(state: dict) -> list:
        thread_id = getattr(_current_thread_id, "value", "") or ""
        info = get_user_info(thread_id)
        existing_messages = list(state.get("messages", []))

        # 매 턴마다 현재 날짜 동적 주입 (요일 포함)
        now = datetime.now()
        weekday = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
        today_str = now.strftime("%Y-%m-%d")
        base = f"오늘 날짜: {today_str} ({weekday}요일)\n\n{system_prompt_base}"

        # income_raw는 내부 계산용 — 프롬프트 노출 제외
        displayable = {k: v for k, v in info.items() if v is not None and k != "income_raw"}
        if not displayable:
            logger.debug("[prompt_fn] thread_id=%r store=empty → 기본 프롬프트", thread_id)
            return [SystemMessage(content=_append_scope_warning(base, info))] + existing_messages
        lines = [f"- {_USER_INFO_LABEL.get(k, k)}: {v}" for k, v in displayable.items()]
        injected = (
            base
            + "\n\n[현재 파악된 사용자 정보]\n"
            + "\n".join(lines)
            + "\n이 정보는 이미 확인된 것이므로:"
            + "\n- 사용자에게 다시 묻지 마세요."
            + "\n- 사용자가 새 정보를 제공하거나 기존 정보를 수정할 때만 extract_info를 호출하세요. 그 외에는 재호출하지 마세요."
            + "\n- 이미 파악된 정보로 바로 search_policies 또는 check_eligibility로 진행하세요."
        )
        logger.debug("[prompt_fn] thread_id=%r 주입: %s", thread_id, lines)
        return [SystemMessage(content=_append_scope_warning(injected, info))] + existing_messages
    return fn


# ============================================================================
# Agent 생성
# ============================================================================

def _read_timeout_seconds(default: int = 25) -> int:
    raw = os.getenv("CHAT_LLM_TIMEOUT_SECONDS")
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def create_agent(
    model: str = ORCHESTRATOR_MODEL,
    temperature: float = 0,
    checkpointer: Optional[MemorySaver] = None,
    max_iterations: int = 5,
    use_short_prompt: bool = False,
    policy_fetcher: PolicyFetcher | None = None,
    timeout_seconds: int | None = None,
):
    """
    복지나침반 ReAct Agent 생성
    
    Args:
        model: 사용할 모델 (기본: gpt-4o-mini)
        temperature: 응답 다양성 (0=결정적, 1=창의적)
        checkpointer: 대화 히스토리 저장용 (멀티턴 지원)
        max_iterations: 최대 도구 반복 횟수(RecursionLimit 계산에 사용)
        use_short_prompt: True면 토큰 절약용 짧은 프롬프트 사용
        policy_fetcher: policies="all" 매칭용 정책 fetch 함수
    
    Returns:
        CompiledGraph (LangGraph Agent)
    """
    # LLM 설정
    if timeout_seconds is None:
        timeout_seconds = _read_timeout_seconds()

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        timeout=timeout_seconds,
    )
    
    # 시스템 프롬프트 선택
    system_prompt = (
        ORCHESTRATOR_SYSTEM_PROMPT_SHORT 
        if use_short_prompt 
        else ORCHESTRATOR_SYSTEM_PROMPT
    )
    tools = create_tools(policy_fetcher)
    
    # ReAct Agent 생성
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=_make_prompt_fn(system_prompt),
        checkpointer=checkpointer,
    )
    setattr(agent, "_max_iterations", max_iterations)
    
    return agent


async def create_agent_with_mcp(
    model: str = "gpt-4o-mini",
    temperature: float = 0,
    use_short_prompt: bool = False,
    checkpointer: Optional[MemorySaver] = None,
    mcp_command: Optional[str] = None,
    mcp_args: Optional[list[str]] = None,
    max_iterations: int = 5,
    policy_fetcher: PolicyFetcher | None = None,
    timeout_seconds: int | None = None,
):
    """
    MCP 경유 모드 Agent 생성.

    - 오케스트레이터는 그대로 두고 (로컬 실행)
    - search 도구는 MCP 서버 도구를 사용 (내부 rewrite 포함)
    - matching 경로(extract_info/check_eligibility)는 로컬 도구 유지
    - create_agent와 동일하게 max_iterations/policy_fetcher를 지원
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:
        raise ImportError(
            "langchain-mcp-adapters 미설치: `uv sync` 후 create_agent_with_mcp()를 사용하세요."
        ) from exc

    if timeout_seconds is None:
        timeout_seconds = _read_timeout_seconds()

    project_root = Path(__file__).resolve().parents[2]
    server_path = project_root / "llm" / "mcp" / "server.py"

    command = mcp_command or sys.executable
    args = mcp_args or [str(server_path)]

    mcp_client = MultiServerMCPClient(
        {
            "welfare-rag": {
                "transport": "stdio",
                "command": command,
                "args": args,
            }
        }
    )
    mcp_tools = await mcp_client.get_tools()

    # search는 MCP로 대체하고, rewrite는 search 내부로 통합했으므로 로컬에서 제외
    local_tools = [
        tool
        for tool in create_tools(policy_fetcher)
        if getattr(tool, "name", "") not in {"rewrite_query", "search_policies"}
    ]
    tools = [*local_tools, *mcp_tools]

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        timeout=timeout_seconds,
    )
    system_prompt = (
        ORCHESTRATOR_SYSTEM_PROMPT_SHORT
        if use_short_prompt
        else ORCHESTRATOR_SYSTEM_PROMPT
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=_make_prompt_fn(system_prompt),
        checkpointer=checkpointer,
    )

    setattr(agent, "_max_iterations", max_iterations)
    setattr(agent, "_mcp_client", mcp_client)
    return agent


async def close_agent_mcp(agent) -> None:
    """create_agent_with_mcp()로 생성한 에이전트의 MCP 클라이언트 종료."""
    client = getattr(agent, "_mcp_client", None)
    if client is not None and hasattr(client, "aclose"):
        await client.aclose()


# ============================================================================
# Agent 실행
# ============================================================================


def _extract_final_ai_text(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.type == "ai":
            content = msg.content
            return content if isinstance(content, str) else str(content)
    return ""


_SEARCH_ENTRY_RE = re.compile(r"^(\d+)\.\s+(.+?)\s+\(([^)]+)\)", re.MULTILINE)
_CAT_RE = re.compile(r"카테고리:\s*([^|\n]+)")
_URL_RE = re.compile(r"신청:\s*(\S+)")
_DESC_RE = re.compile(r"설명:\s*(.+)")


def _parse_search_policies_text(text: str) -> list[PolicyResult]:
    """search_policies 텍스트에서 기본 정책 목록을 파싱한다. eligibility는 uncertain."""
    entries = re.split(r"\n(?=\d+\.\s+)", text)
    policies: list[PolicyResult] = []
    for entry in entries:
        m = _SEARCH_ENTRY_RE.match(entry.strip())
        if not m:
            continue
        title = m.group(2).strip()
        policy_id = m.group(3).strip()

        category = ""
        cat_m = _CAT_RE.search(entry)
        if cat_m:
            category = cat_m.group(1).strip()

        apply_url = None
        url_m = _URL_RE.search(entry)
        if url_m:
            apply_url = url_m.group(1).strip()

        summary = ""
        desc_m = _DESC_RE.search(entry)
        if desc_m:
            summary = desc_m.group(1).strip()

        try:
            policies.append(
                PolicyResult.from_dict(
                    {
                        "policy_id": policy_id,
                        "title": title,
                        "category": category,
                        "summary": summary,
                        "eligibility": None,
                        "ineligible_reasons": [],
                        "apply_url": apply_url,
                    }
                )
            )
        except (ValueError, TypeError):
            pass
    return policies


def _extract_policies_from_messages(
    messages: list,
    *,
    today=None,
) -> list[PolicyResult] | None:
    """ToolMessage에서 정책 목록을 추출한다.

    check_eligibility ToolMessage → JSON 파싱 → PolicyResult 목록
    search_policies ToolMessage만 있으면 → 텍스트 파싱 → uncertain PolicyResult 목록
    도구 호출이 전혀 없으면 None 반환.
    """
    check_content: str | None = None
    search_content: str | None = None

    for msg in messages:
        if getattr(msg, "type", "") == "tool":
            name = getattr(msg, "name", "")
            if name == "check_eligibility":
                check_content = msg.content if isinstance(msg.content, str) else None
            elif name == "search_policies":
                search_content = msg.content if isinstance(msg.content, str) else None

    if check_content is not None:
        try:
            data = json.loads(check_content)
        except (json.JSONDecodeError, TypeError):
            data = None
        # scope_blocked sentinel → 빈 리스트 반환 (search_content로 폴백하지 않음)
        if isinstance(data, dict) and data.get("scope_blocked"):
            return []
        if isinstance(data, list):
            policies: list[PolicyResult] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                mapped = {
                    "policy_id": item.get("policy_id"),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "summary": item.get("summary"),
                    "eligibility": item.get("is_eligible"),
                    "ineligible_reasons": (
                        item.get("reasons")
                        if isinstance(item.get("reasons"), list)
                        else []
                    ),
                    "deadline": item.get("apply_end_date"),
                    "apply_url": item.get("apply_url"),
                    "detail_url": item.get("detail_url"),
                }
                try:
                    policies.append(PolicyResult.from_dict(mapped, today=today))
                except (ValueError, TypeError):
                    pass
            return [p for p in policies if p.eligibility != "ineligible"]

    if search_content is not None:
        try:
            _sd = json.loads(search_content)
        except (json.JSONDecodeError, TypeError):
            _sd = None
        if isinstance(_sd, dict) and _sd.get("scope_blocked"):
            return []

    if search_content is not None and search_content not in (
        "검색 결과 없음",
        "검색 중 오류가 발생했습니다",
        "검색 백엔드가 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요.",
    ):
        return _parse_search_policies_text(search_content)

    return None


_POLICY_TOOL_NAMES = {"search_policies", "check_eligibility"}


def _had_policy_tool_calls(messages: list) -> bool:
    """현재 턴 메시지에 search_policies 또는 check_eligibility ToolMessage가 있는지 확인."""
    return any(
        getattr(msg, "type", "") == "tool"
        and getattr(msg, "name", "") in _POLICY_TOOL_NAMES
        for msg in messages
    )


def _strip_json_code_fence(raw_text: str) -> str:
    stripped = raw_text.strip()
    if not stripped.startswith("```"):
        return raw_text

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        opening = lines[0].strip().lower()
        if opening in {"```", "```json"}:
            return "\n".join(lines[1:-1]).strip()
    return raw_text


def _parse_chat_response(raw_text: str) -> tuple[ChatResponse, bool]:
    stripped = _strip_json_code_fence(raw_text).strip()
    decoder = json.JSONDecoder()
    candidates = [stripped]

    first_brace = stripped.find("{")
    if first_brace > 0:
        candidates.append(stripped[first_brace:])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed, _end = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            try:
                return ChatResponse.from_dict(parsed), True
            except (ValueError, TypeError):
                continue

    return ChatResponse(message=raw_text, policies=[], follow_up=None), False


def run_agent(
    agent,
    message: str,
    thread_id: str = "default",
    verbose: bool = False,
    max_iterations: int | None = None,
) -> dict:
    """
    Agent에 메시지 전달하고 응답 받기
    
    Args:
        agent: create_agent()로 생성한 Agent
        message: 사용자 메시지
        thread_id: 대화 세션 ID (멀티턴 지원)
        verbose: True면 중간 과정 출력
    
    Returns:
        {
            "response": ChatResponse,
            "raw_text": 최종 AI 원문,
            "tool_calls": 호출된 도구 목록,
            "messages": 전체 메시지 히스토리,
            "error": 에러 발생 시 에러 메시지 (없으면 None),
        }
    """
    # 설정
    effective_max_iterations = max_iterations if max_iterations is not None else getattr(agent, "_max_iterations", 5)
    recursion_limit = effective_max_iterations * 2 + 1
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler is not None:
        config.setdefault("callbacks", []).append(langfuse_handler)

    # 입력 메시지
    inputs = {"messages": [HumanMessage(content=message)]}

    try:
        # thread_local에 thread_id 세팅 — prompt callable이 store 조회에 사용
        _current_thread_id.value = thread_id
        try:
            # 실행
            with langfuse_session(session_id=thread_id):
                result = agent.invoke(inputs, config=config)
        finally:
            _current_thread_id.value = ""

        # 결과 파싱
        messages = result.get("messages", [])

        # 현재 턴 extract_info ToolMessage 파싱 → store 누적
        # checkpointer가 있으면 result["messages"]에 전체 히스토리가 담기므로
        # 마지막 HumanMessage 이후 메시지만 처리 (현재 턴 신규 메시지만)
        last_human_idx = -1
        for i, msg in enumerate(messages):
            if getattr(msg, "type", "") == "human":
                last_human_idx = i
        for msg in messages[last_human_idx + 1:]:
            if getattr(msg, "type", "") == "tool" and getattr(msg, "name", "") == "extract_info":
                try:
                    extracted = json.loads(msg.content)
                    if isinstance(extracted, dict):
                        merge_user_info(thread_id, extracted)
                except (json.JSONDecodeError, TypeError):
                    pass

        raw_text = _extract_final_ai_text(messages)
        response, parsed_ok = _parse_chat_response(raw_text)

        if not parsed_ok:
            if _had_policy_tool_calls(messages):
                # 정책 검색은 실행됐는데 LLM이 JSON 대신 평문으로 응답 — 진짜 포맷 이탈
                logger.warning(
                    "tool_called_but_unparsed. raw_text_preview=%r", raw_text[:300]
                )
            else:
                # 비정책 대화 턴 (인사·안내·clarification) — 평문 응답이 정상 동작
                logger.debug(
                    "text_only_response. raw_text_preview=%r", raw_text[:300]
                )

        # ToolMessage 기반 policies 추출 (LLM JSON 파싱 대신 항상 도구 결과 사용)
        # checkpointer로 전체 히스토리가 쌓이므로 현재 턴 메시지만 넘김 (extract_info와 동일 패턴)
        extracted_policies = _extract_policies_from_messages(messages[last_human_idx + 1:])
        if extracted_policies is not None:
            response = ChatResponse(
                message=response.message,
                policies=extracted_policies,
                follow_up=response.follow_up,
                stage="complete",
            )
        
        # 도구 호출 추출
        tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "name": tc.get("name"),
                        "args": tc.get("args"),
                    })
        
        if verbose:
            print("\n=== Tool Calls ===")
            for tc in tool_calls:
                print(f"  - {tc['name']}: {tc['args']}")
            print("\n=== Structured Output Parse ===")
            print("  - success" if parsed_ok else "  - fallback to raw_text")
            print("\n=== Response ===")
            print(raw_text)
        
        return {
            "response": response,
            "raw_text": raw_text,
            "tool_calls": tool_calls,
            "messages": messages,
            "error": None,
        }
        
    except Exception as e:
        logger.exception("Agent 실행 중 오류 발생")
        error_msg = f"Agent 실행 중 오류 발생: {str(e)}"

        if verbose:
            print(f"\n=== Error ===\n{error_msg}")

        fallback_text = "죄송해요, 일시적인 오류가 발생했어요. 잠시 후 다시 시도해주세요! 🙏"


        return {
            "response": ChatResponse(
                message=fallback_text,
                policies=[],
                follow_up=None,
            ),
            "raw_text": fallback_text,
            "tool_calls": [],
            "messages": [],
            "error": error_msg,
        }


# TODO [BRAIN4-XX]: stream_agent / create_agent_with_mcp 경로에 서비스 범위 가드레일 미적용.
# run_agent와 동일한 _current_thread_id 세팅 + scope guard 도구 적용 필요. 별도 티켓으로 분리.
def stream_agent(
    agent,
    message: str,
    thread_id: str = "default",
):
    """
    Agent 스트리밍 실행 (실시간 응답)

    Yields:
        각 스텝의 결과 dict
    """
    max_iterations = getattr(agent, "_max_iterations", 5)
    recursion_limit = max_iterations * 2 + 1
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler is not None:
        config.setdefault("callbacks", []).append(langfuse_handler)
    inputs = {"messages": [HumanMessage(content=message)]}

    with langfuse_session(session_id=thread_id):
        try:
            for chunk in agent.stream(inputs, config=config, stream_mode="values"):
                yield chunk
        except Exception as e:
            logger.exception("스트리밍 중 오류 발생")
            yield {"error": f"스트리밍 중 오류: {str(e)}"}


# ============================================================================
# 간편 함수
# ============================================================================

def chat(message: str, thread_id: str = "default") -> str:
    """
    간편 채팅 함수
    
    Args:
        message: 사용자 메시지
        thread_id: 대화 세션 ID
    
    Returns:
        응답 텍스트
        
    Example:
        >>> response = chat("27살인데 월세 지원 받을 수 있어요?")
        >>> print(response)
    """
    # 싱글톤 Agent (메모리 유지)
    if not hasattr(chat, "_agent"):
        chat._checkpointer = MemorySaver()
        chat._agent = create_agent(checkpointer=chat._checkpointer)
    
    result = run_agent(chat._agent, message, thread_id=thread_id)
    return result["response"].message


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    print("=== 복지나침반 Agent 테스트 ===\n")
    
    # Agent 생성 (체크포인터 없이 - 테스트용)
    agent = create_agent(use_short_prompt=True)
    
    if agent is None:
        print("❌ Agent 생성 실패!")
        exit(1)
    
    # 테스트 대화
    test_messages = [
        "안녕하세요!",
        "27살이고 강남에 살아요. 월세 지원 받을 수 있나요?",
        "취업 관련 정책도 알려주세요",
    ]
    
    for msg in test_messages:
        print(f"👤 사용자: {msg}")
        print("-" * 50)
        
        result = run_agent(agent, msg, verbose=True)
        
        if result["error"]:
            print(f"❌ 에러: {result['error']}")
        else:
            print(f"\n🤖 복지나침반: {result['response'].message[:200]}...")
        
        print("\n" + "=" * 60 + "\n")
