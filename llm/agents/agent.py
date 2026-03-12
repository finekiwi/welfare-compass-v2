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
import sys
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .schemas import ChatResponse
from .tools import create_tools
from .tools.check_eligibility import PolicyFetcher
from .prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT, ORCHESTRATOR_SYSTEM_PROMPT_SHORT
from ..services import get_langfuse_handler, langfuse_session

logger = logging.getLogger(__name__)


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
    model: str = "gpt-4o-mini",
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
        prompt=SystemMessage(content=system_prompt),
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
        prompt=SystemMessage(content=system_prompt),
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
    max_iterations = getattr(agent, "_max_iterations", 5)
    recursion_limit = max_iterations * 2 + 1
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
        # 실행
        with langfuse_session(session_id=thread_id):
            result = agent.invoke(inputs, config=config)

        # 결과 파싱
        messages = result.get("messages", [])
        raw_text = _extract_final_ai_text(messages)
        response, parsed_ok = _parse_chat_response(raw_text)
        
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
