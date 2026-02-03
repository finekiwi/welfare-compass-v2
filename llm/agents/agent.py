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

from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .tools import ALL_TOOLS
from .prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT, ORCHESTRATOR_SYSTEM_PROMPT_SHORT


# ============================================================================
# Agent 생성
# ============================================================================

def create_agent(
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    use_short_prompt: bool = False,
    checkpointer: Optional[MemorySaver] = None,
):
    """
    복지나침반 ReAct Agent 생성
    
    Args:
        model: 사용할 모델 (기본: gpt-4o-mini)
        temperature: 응답 다양성 (0=결정적, 1=창의적)
        use_short_prompt: True면 토큰 절약용 짧은 프롬프트 사용
        checkpointer: 대화 히스토리 저장용 (멀티턴 지원)
    
    Returns:
        CompiledGraph (LangGraph Agent)
    """
    # LLM 설정
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
    )
    
    # 시스템 프롬프트 선택
    system_prompt = (
        ORCHESTRATOR_SYSTEM_PROMPT_SHORT 
        if use_short_prompt 
        else ORCHESTRATOR_SYSTEM_PROMPT
    )
    
    # ReAct Agent 생성
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SystemMessage(content=system_prompt),
        checkpointer=checkpointer,
    )
    
    return agent


# ============================================================================
# Agent 실행
# ============================================================================

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
            "response": 최종 응답 텍스트,
            "tool_calls": 호출된 도구 목록,
            "messages": 전체 메시지 히스토리,
            "error": 에러 발생 시 에러 메시지 (없으면 None),
        }
    """
    # 설정
    config = {"configurable": {"thread_id": thread_id}}
    
    # 입력 메시지
    inputs = {"messages": [HumanMessage(content=message)]}
    
    try:
        # 실행
        result = agent.invoke(inputs, config=config)
        
        # 결과 파싱
        messages = result.get("messages", [])
        
        # 마지막 AI 메시지 추출
        response = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.type == "ai":
                response = msg.content
                break
        
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
            print("\n=== Response ===")
            print(response)
        
        return {
            "response": response,
            "tool_calls": tool_calls,
            "messages": messages,
            "error": None,
        }
        
    except Exception as e:
        error_msg = f"Agent 실행 중 오류 발생: {str(e)}"
        
        if verbose:
            print(f"\n=== Error ===\n{error_msg}")
        
        return {
            "response": "죄송해요, 일시적인 오류가 발생했어요. 잠시 후 다시 시도해주세요! 🙏",
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
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=message)]}
    
    try:
        for chunk in agent.stream(inputs, config=config, stream_mode="values"):
            yield chunk
    except Exception as e:
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
    return result["response"]


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
            print(f"\n🤖 복지나침반: {result['response'][:200]}...")
        
        print("\n" + "=" * 60 + "\n")