"""
ReAct Agent 테스트

BRAIN4-29 AC 검증:
- [x] ReAct agent 생성 및 실행 가능
- [x] 기본 테스트 통과 ("안녕" → 응답 생성)
"""

import asyncio
import json
import os
import sys
import types

import pytest


needs_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


def _is_backend_unavailable_error(exc: Exception) -> bool:
    text = str(exc).lower()
    keywords = (
        "connection error",
        "failed to establish",
        "api connection",
        "apiconnectionerror",
        "read timeout",
        "timed out",
        "nodename nor servname",
        "temporary failure in name resolution",
    )
    return any(keyword in text for keyword in keywords)


# ============================================================================
# 1. Agent 생성 테스트
# ============================================================================

class TestAgentCreation:
    """Agent 생성 관련 테스트"""
    
    def test_create_agent_default(self):
        """기본 설정으로 Agent 생성"""
        from llm.agents.agent import create_agent
        
        agent = create_agent()
        
        assert agent is not None
        # CompiledGraph 타입 확인
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "stream")
    
    def test_create_agent_with_short_prompt(self):
        """짧은 프롬프트로 Agent 생성"""
        from llm.agents.agent import create_agent
        
        agent = create_agent(use_short_prompt=True)
        
        assert agent is not None
    
    def test_create_agent_with_custom_model(self):
        """커스텀 모델로 Agent 생성"""
        from llm.agents.agent import create_agent
        
        agent = create_agent(model="gpt-4o-mini", temperature=0.5)
        
        assert agent is not None

    def test_create_agent_passes_policy_fetcher(self, monkeypatch):
        """create_agent가 create_tools로 policy_fetcher를 전달한다."""
        from llm.agents import agent as agent_module

        captured = {}

        def fake_create_tools(policy_fetcher=None):
            captured["policy_fetcher"] = policy_fetcher
            return []

        def fake_chat_openai(*, model, temperature, **kwargs):
            return {"model": model, "temperature": temperature}

        class DummyAgent:
            pass

        def fake_create_react_agent(model, tools, prompt, checkpointer):
            captured["tools"] = tools
            captured["prompt"] = prompt
            captured["checkpointer"] = checkpointer
            return DummyAgent()

        monkeypatch.setattr(agent_module, "create_tools", fake_create_tools)
        monkeypatch.setattr(agent_module, "ChatOpenAI", fake_chat_openai)
        monkeypatch.setattr(agent_module, "create_react_agent", fake_create_react_agent)

        fetcher = lambda ids: []
        agent = agent_module.create_agent(policy_fetcher=fetcher, max_iterations=7)

        assert captured["policy_fetcher"] is fetcher
        assert captured["tools"] == []
        assert getattr(agent, "_max_iterations") == 7

    def test_run_agent_sets_recursion_limit(self):
        """run_agent가 max_iterations 기반 recursion_limit을 설정한다."""
        from llm.agents.agent import run_agent
        from llm.agents.schemas import ChatResponse

        class DummyMessage:
            type = "ai"
            content = "ok"
            tool_calls = []

        class DummyAgent:
            def __init__(self):
                self.last_config = None

            def invoke(self, _inputs, config=None):
                self.last_config = config
                return {"messages": [DummyMessage()]}

        agent = DummyAgent()
        setattr(agent, "_max_iterations", 5)

        result = run_agent(agent, "테스트")

        assert result["error"] is None
        assert isinstance(result["response"], ChatResponse)
        assert result["response"].message == "ok"
        assert result["raw_text"] == "ok"
        assert agent.last_config["recursion_limit"] == 11

    def test_create_agent_with_mcp_syncs_policy_fetcher_and_max_iterations(self, monkeypatch):
        """create_agent_with_mcp가 create_agent와 주요 인자를 동기화한다."""
        from llm.agents import agent as agent_module

        captured = {}

        class DummyMCPClient:
            def __init__(self, config):
                captured["mcp_config"] = config

            async def get_tools(self):
                class DummyMCPTool:
                    name = "search_policies"

                return [DummyMCPTool()]

        client_module = types.ModuleType("langchain_mcp_adapters.client")
        client_module.MultiServerMCPClient = DummyMCPClient
        package_module = types.ModuleType("langchain_mcp_adapters")
        package_module.client = client_module
        monkeypatch.setitem(sys.modules, "langchain_mcp_adapters", package_module)
        monkeypatch.setitem(sys.modules, "langchain_mcp_adapters.client", client_module)

        class DummyTool:
            def __init__(self, name):
                self.name = name

        def fake_create_tools(policy_fetcher=None):
            captured["policy_fetcher"] = policy_fetcher
            return [DummyTool("extract_info"), DummyTool("search_policies"), DummyTool("check_eligibility")]

        def fake_chat_openai(*, model, temperature, **kwargs):
            captured["temperature"] = temperature
            return object()

        class DummyAgent:
            pass

        def fake_create_react_agent(model, tools, prompt, checkpointer):
            captured["tools"] = tools
            return DummyAgent()

        monkeypatch.setattr(agent_module, "create_tools", fake_create_tools)
        monkeypatch.setattr(agent_module, "ChatOpenAI", fake_chat_openai)
        monkeypatch.setattr(agent_module, "create_react_agent", fake_create_react_agent)

        fetcher = lambda ids: []
        agent = asyncio.run(
            agent_module.create_agent_with_mcp(
                policy_fetcher=fetcher,
                max_iterations=7,
                temperature=0,
            )
        )

        assert captured["policy_fetcher"] is fetcher
        assert captured["temperature"] == 0
        assert getattr(agent, "_max_iterations") == 7

# ============================================================================
# 2. 기본 응답 테스트 (실제 API 호출)
# ============================================================================

class TestAgentResponse:
    """Agent 응답 테스트 (실제 API 호출)"""

    pytestmark = [pytest.mark.integration, needs_api_key]
    
    @pytest.fixture
    def agent(self):
        """테스트용 Agent 생성"""
        from llm.agents.agent import create_agent
        return create_agent(use_short_prompt=True)

    @staticmethod
    def _assert_or_skip(result: dict):
        if result.get("error") and _is_backend_unavailable_error(Exception(result["error"])):
            pytest.skip(f"integration unavailable: {result['error']}")
        assert result["error"] is None
    
    def test_chitchat_response(self, agent):
        """chitchat: 인사에 응답"""
        from llm.agents.agent import run_agent
        
        result = run_agent(agent, "안녕!", verbose=True)
        
        # 응답 있음
        assert result["response"] is not None
        assert len(result["response"].message) > 0
        
        # 에러 없음
        self._assert_or_skip(result)
        
        # chitchat은 도구 호출 없음 (또는 최소)
        # (모델이 도구 호출할 수도 있어서 강제 assert 안 함)
        print(f"\n응답: {result['response'].message}")
        print(f"도구 호출: {result['tool_calls']}")
    
    def test_matching_response(self, agent):
        """matching: 추천 요청에 도구 호출"""
        from llm.agents.agent import run_agent
        
        result = run_agent(
            agent, 
            "27살인데 뭐 받을 수 있어?",
            verbose=True
        )
        
        # 응답 있음
        assert result["response"] is not None
        assert len(result["response"].message) > 0
        
        # 에러 없음
        self._assert_or_skip(result)
        
        # 도구 호출 있음 (stub이라도 호출되어야 함)
        print(f"\n응답: {result['response'].message}")
        print(f"도구 호출: {result['tool_calls']}")
    
    def test_faq_response(self, agent):
        """faq: 상세 질문에 응답"""
        from llm.agents.agent import run_agent
        
        result = run_agent(
            agent,
            "청년월세지원 신청 어떻게 해?",
            verbose=True
        )
        
        assert result["response"] is not None
        self._assert_or_skip(result)
        
        print(f"\n응답: {result['response'].message}")
        print(f"도구 호출: {result['tool_calls']}")
    
    def test_explore_response(self, agent):
        """explore: 탐색 요청에 응답"""
        from llm.agents.agent import run_agent
        
        result = run_agent(
            agent,
            "주거 관련 정책 뭐 있어?",
            verbose=True
        )
        
        assert result["response"] is not None
        self._assert_or_skip(result)
        
        print(f"\n응답: {result['response'].message}")
        print(f"도구 호출: {result['tool_calls']}")


# ============================================================================
# 3. 에러 핸들링 테스트
# ============================================================================

class TestAgentErrorHandling:
    """에러 핸들링 테스트"""
    
    def test_empty_message(self):
        """빈 메시지 처리"""
        from llm.agents.agent import create_agent, run_agent
        
        agent = create_agent(use_short_prompt=True)
        result = run_agent(agent, "")
        
        # 에러 또는 빈 응답이라도 크래시 안 남
        assert "response" in result
        assert hasattr(result["response"], "message")
    
    def test_very_long_message(self):
        """매우 긴 메시지 처리"""
        from llm.agents.agent import create_agent, run_agent
        
        agent = create_agent(use_short_prompt=True)
        long_message = "청년 정책 " * 100  # 반복 메시지
        
        result = run_agent(agent, long_message)
        
        # 크래시 없이 응답
        assert "response" in result
        assert hasattr(result["response"], "message")


class TestRunAgentParsing:
    """structured output 파싱 테스트"""

    @staticmethod
    def _agent_with_response(content: str):
        class DummyMessage:
            type = "ai"
            tool_calls = []

            def __init__(self, content: str):
                self.content = content

        class DummyAgent:
            def invoke(self, _inputs, config=None):
                return {"messages": [DummyMessage(content)]}

        return DummyAgent()

    def test_run_agent_parses_json_response(self):
        from llm.agents.agent import run_agent
        from llm.agents.schemas import EligibilityStatus

        agent = self._agent_with_response(
            json.dumps(
                {
                    "message": "조건에 맞는 정책을 정리했어요.",
                    "policies": [
                        {
                            "plcy_no": "P100",
                            "plcy_nm": "청년월세지원",
                            "category": "주거",
                            "summary": "월세를 지원해요.",
                            "eligibility": "eligible",
                            "ineligible_reasons": [],
                            "deadline": "2026-03-20",
                            "apply_url": "https://example.com/apply",
                            "detail_url": "https://example.com/detail",
                        }
                    ],
                    "follow_up": None,
                },
                ensure_ascii=False,
            )
        )

        result = run_agent(agent, "주거 정책 알려줘")

        assert result["error"] is None
        assert result["response"].message == "조건에 맞는 정책을 정리했어요."
        assert result["response"].policies[0].eligibility is EligibilityStatus.ELIGIBLE
        assert result["raw_text"].startswith("{")

    def test_run_agent_parses_fenced_json_response(self):
        from llm.agents.agent import run_agent

        agent = self._agent_with_response(
            """```json
{"message":"안내해드릴게요.","policies":[],"follow_up":"나이를 알려주세요."}
```"""
        )

        result = run_agent(agent, "추천해줘")

        assert result["response"].message == "안내해드릴게요."
        assert result["response"].follow_up == "나이를 알려주세요."
        assert result["response"].policies == []

    def test_run_agent_falls_back_for_plain_text(self):
        from llm.agents.agent import run_agent

        agent = self._agent_with_response("안녕하세요! 무엇을 도와드릴까요?")
        result = run_agent(agent, "안녕!")

        assert result["response"].message == "안녕하세요! 무엇을 도와드릴까요?"
        assert result["response"].policies == []
        assert result["response"].follow_up is None

    def test_run_agent_keeps_empty_policies(self):
        from llm.agents.agent import run_agent

        agent = self._agent_with_response(
            '{"message":"반가워요!","policies":[],"follow_up":null}'
        )
        result = run_agent(agent, "안녕!")

        assert result["response"].policies == []

    def test_run_agent_verbose_logs_parse_result(self, capsys):
        from llm.agents.agent import run_agent

        agent = self._agent_with_response('{"message":"안내해드릴게요.","policies":[],"follow_up":null}')
        run_agent(agent, "테스트", verbose=True)
        captured = capsys.readouterr()

        assert "Structured Output Parse" in captured.out
        assert "success" in captured.out


# ============================================================================
# 4. 도구 테스트 (단위 테스트)
# ============================================================================

class TestTools:
    """개별 도구 단위 테스트"""
    
    def test_extract_info_stub(self):
        """extract_info stub 반환값 확인"""
        from llm.agents.tools import extract_info
        
        # @tool 데코레이터가 적용되어 있어서 .invoke() 호출
        result = extract_info.invoke("27살이고 강남에 살아요")
        result = json.loads(result)  # @tool은 JSON 문자열 반환
        
        assert isinstance(result, dict)
        assert "age" in result
    
    def test_rewrite_query_stub(self, monkeypatch):
        """rewrite_query 반환값 확인"""
        import importlib
        from llm.agents.tools import rewrite_query
        import json
        rewrite_module = importlib.import_module("llm.agents.tools.rewrite_query")

        # Mock LLM 응답
        monkeypatch.setattr(
            rewrite_module,
            "_rewrite_with_llm",
            lambda _query: json.dumps({
                "bm25_query": "청년 월세 지원 주거 보조금",
                "intent_keywords": ["월세", "지원"],
                "detected_pattern": "easy"
            }),
        )

        result = rewrite_query.invoke("월세 도움 받을 수 있어?")

        assert isinstance(result, str)
        assert result == "청년 월세 지원 주거 보조금"
    
    def test_search_policies(self, monkeypatch):
        """search_policies 반환값 확인"""
        import importlib
        from llm.agents.tools import search_policies
        search_module = importlib.import_module("llm.agents.tools.search_policies")

        class DummyBackend:
            def search(self, query: str, top_k: int = 10, income_max: int | None = None):
                return {
                    "original_query": query,
                    "rewritten_query": "청년 월세 지원",
                    "result_count": 1,
                    "policies": [
                        {
                            "policy_id": "P1",
                            "title": "청년월세지원",
                            "description": "설명",
                            "category": "주거",
                            "district": "서울특별시",
                            "age_min": 19,
                            "age_max": 39,
                            "apply_url": "https://example.com",
                        }
                    ],
                }

        monkeypatch.setattr(search_module, "get_search_backend", lambda: DummyBackend())
        result = search_policies.invoke({"query": "청년 월세", "top_k": 5})

        assert isinstance(result, str)
        assert "청년월세지원" in result
        assert "검색 결과: 1건" in result
    
    def test_check_eligibility_stub(self):
        """check_eligibility JSON 문자열 반환값 확인"""
        from llm.agents.tools import check_eligibility
        import json
        
        result = check_eligibility.invoke({
            "policies": json.dumps(
                [
                    {
                        "policy_id": "T001",
                        "title": "테스트 정책",
                        "age_min": 19,
                        "age_max": 39,
                        "income_level": "0043001",
                        "district": "서울",
                    }
                ],
                ensure_ascii=False,
            ),
            "user_info": json.dumps(
                {
                    "age": 27,
                    "income_level": 2400,
                    "district": "강남구",
                },
                ensure_ascii=False,
            ),
        })
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1


# ============================================================================
# 5. 간편 함수 테스트
# ============================================================================

class TestChatFunction:
    """chat() 간편 함수 테스트"""

    pytestmark = [pytest.mark.integration, needs_api_key]
    
    def test_chat_basic(self):
        """chat() 기본 호출"""
        from llm.agents.agent import chat
        
        response = chat("안녕!")
        
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nchat 응답: {response}")
    
    def test_chat_multiturn(self):
        """chat() 멀티턴 대화"""
        from llm.agents.agent import chat
        
        # 같은 thread_id로 연속 대화
        thread_id = "test_multiturn"
        
        r1 = chat("나 27살이야", thread_id=thread_id)
        r2 = chat("아까 말한 내 나이 기억해?", thread_id=thread_id)
        
        assert len(r1) > 0
        assert len(r2) > 0
        
        print(f"\n1차 응답: {r1}")
        print(f"2차 응답: {r2}")


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
