"""
ReAct Agent State 정의

중앙 오케스트레이터 구조에서는 State가 단순해짐
- messages: 대화 히스토리 (HumanMessage, AIMessage, ToolMessage)
- user_info: 추출된 사용자 정보 (도구 호출로 채워짐)
- search_results: 검색 결과 (도구 호출로 채워짐)
"""

from typing import TypedDict, Annotated, Sequence
from dataclasses import dataclass, field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# ============================================================================
# 서브 타입 정의 (도구 입출력용)
# ============================================================================

@dataclass
class UserInfo:
    """사용자 정보 (extract_info 도구 출력)"""
    age: int | None = None
    income_level: str | None = None  # 중위50이하, 중위100이하, 중위150이하, 무관
    region: str | None = None        # 서울시
    district: str | None = None      # 강남구 등
    employment_status: str | None = None  # 재직자, 구직중, 학생 등
    interests: list[str] = field(default_factory=list)  # 주거, 취업 등
    
    def to_dict(self) -> dict:
        return {
            "age": self.age,
            "income_level": self.income_level,
            "region": self.region,
            "district": self.district,
            "employment_status": self.employment_status,
            "interests": self.interests,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserInfo":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def __str__(self) -> str:
        parts = []
        if self.age:
            parts.append(f"나이: {self.age}세")
        if self.district:
            parts.append(f"지역: {self.district}")
        elif self.region:
            parts.append(f"지역: {self.region}")
        if self.income_level:
            parts.append(f"소득: {self.income_level}")
        if self.employment_status:
            parts.append(f"상태: {self.employment_status}")
        if self.interests:
            parts.append(f"관심: {', '.join(self.interests)}")
        return " | ".join(parts) if parts else "정보 없음"


@dataclass
class PolicyInfo:
    """정책 정보 - Django 모델 필드명과 일치
    
    MCP 서버 응답을 그대로 사용 가능
    """
    policy_id: str
    title: str
    description: str = ""
    support_content: str = ""       # 지원 내용
    age_min: int = 0
    age_max: int = 99
    income_level: str = ""          # 소득 조건 (중위50이하, 무관 등)
    district: str = ""              # 서울시 구
    category: str = ""              # 대분류 (일자리, 주거 등)
    apply_url: str = ""
    apply_start_date: str = ""
    apply_end_date: str = ""
    # 매칭 결과 (check_eligibility에서 채움)
    is_eligible: bool | None = None
    ineligible_reasons: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "title": self.title,
            "description": self.description,
            "support_content": self.support_content,
            "age_min": self.age_min,
            "age_max": self.age_max,
            "income_level": self.income_level,
            "district": self.district,
            "category": self.category,
            "apply_url": self.apply_url,
            "apply_start_date": self.apply_start_date,
            "apply_end_date": self.apply_end_date,
            "is_eligible": self.is_eligible,
            "ineligible_reasons": self.ineligible_reasons,
        }


# ============================================================================
# Agent State (ReAct용)
# ============================================================================

class AgentState(TypedDict):
    """
    ReAct Agent State
    
    LangGraph의 create_react_agent는 기본적으로 messages만 사용.
    추가 컨텍스트가 필요하면 여기에 필드 추가.
    """
    # 대화 히스토리 (자동 누적)
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 세션 정보 (선택)
    session_id: str
    

# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    # UserInfo 테스트
    user = UserInfo(age=27, district="강남구", interests=["주거", "취업"])
    print(f"UserInfo: {user}")
    print(f"Dict: {user.to_dict()}")
    
    # PolicyInfo 테스트
    policy = PolicyInfo(
        policy_id="R2024010100001",
        title="청년월세지원",
        is_eligible=True,
    )
    print(f"\nPolicyInfo: {policy.title} (적격: {policy.is_eligible})")