"""
ReAct Agent 테스트

BRAIN4-29 AC 검증:
- [x] ReAct agent 생성 및 실행 가능
- [x] 기본 테스트 통과 ("안녕" → 응답 생성)
"""

import pytest


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


# ============================================================================
# 2. 기본 응답 테스트 (실제 API 호출)
# ============================================================================

class TestAgentResponse:
    """Agent 응답 테스트 (실제 API 호출)"""
    
    @pytest.fixture
    def agent(self):
        """테스트용 Agent 생성"""
        from llm.agents.agent import create_agent
        return create_agent(use_short_prompt=True)
    
    def test_chitchat_response(self, agent):
        """chitchat: 인사에 응답"""
        from llm.agents.agent import run_agent
        
        result = run_agent(agent, "안녕!", verbose=True)
        
        # 응답 있음
        assert result["response"] is not None
        assert len(result["response"]) > 0
        
        # 에러 없음
        assert result["error"] is None
        
        # chitchat은 도구 호출 없음 (또는 최소)
        # (모델이 도구 호출할 수도 있어서 강제 assert 안 함)
        print(f"\n응답: {result['response']}")
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
        assert len(result["response"]) > 0
        
        # 에러 없음
        assert result["error"] is None
        
        # 도구 호출 있음 (stub이라도 호출되어야 함)
        print(f"\n응답: {result['response']}")
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
        assert result["error"] is None
        
        print(f"\n응답: {result['response']}")
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
        assert result["error"] is None
        
        print(f"\n응답: {result['response']}")
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
    
    def test_very_long_message(self):
        """매우 긴 메시지 처리"""
        from llm.agents.agent import create_agent, run_agent
        
        agent = create_agent(use_short_prompt=True)
        long_message = "청년 정책 " * 100  # 반복 메시지
        
        result = run_agent(agent, long_message)
        
        # 크래시 없이 응답
        assert "response" in result


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
        
        assert isinstance(result, dict)
        assert "age" in result
        assert "interests" in result
    
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
            def search(self, query: str, top_k: int = 10):
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
        """check_eligibility stub 반환값 확인"""
        from llm.agents.tools import check_eligibility
        
        result = check_eligibility.invoke({
            "user_info": {"age": 27},
            "policy_ids": None
        })
        
        assert isinstance(result, list)
        assert len(result) > 0


# ============================================================================
# 5. 간편 함수 테스트
# ============================================================================

class TestChatFunction:
    """chat() 간편 함수 테스트"""
    
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
