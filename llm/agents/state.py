"""LangGraph State 스키마 정의"""
from typing import TypedDict, Literal, List, Optional


# ============================================================================
# 타입 정의
# ============================================================================
Intent = Literal["chitchat", "matching", "compare", "faq", "explore"]


# ============================================================================
# 서브 스키마
# ============================================================================
class UserProfile(TypedDict, total=False):
    """회원 프로필 (백엔드 DB에서 주입)"""
    age: int
    region: str                     # "서울 강남구"
    income_level: str               # "0043001" 등
    employment_status: str          # "재직", "구직중" 등
    housing_type: str               # "월세", "전세" 등
    special_conditions: List[str]   # ["청년", "한부모" 등]
    has_children: bool
    children_ages: List[int]


class ExtractedInfo(TypedDict, total=False):
    """발화에서 추출한 정보"""
    age: int
    region: str
    income_level: str
    employment_status: str
    housing_type: str
    special_conditions: List[str]
    has_children: bool
    children_ages: List[int]
    # 발화 전용
    needs: List[str]                # ["주거", "일자리"]
    target_policies: List[str]      # 언급된 정책명


class FinalConditions(TypedDict, total=False):
    """UserProfile + ExtractedInfo 병합 결과"""
    age: int
    region: str
    income_level: str
    employment_status: str
    housing_type: str
    special_conditions: List[str]
    has_children: bool
    children_ages: List[int]
    needs: List[str]
    target_policies: List[str]
    # 메타
    has_profile: bool               # 회원 여부
    missing_fields: List[str]       # 매칭에 필요한데 없는 필드


class PolicyResult(TypedDict):
    """검색/매칭 결과"""
    plcy_no: str
    plcy_nm: str
    plcy_explan: str
    score: float
    apply_url: str


# ============================================================================
# 메인 State
# ============================================================================
class MainState(TypedDict, total=False):
    """LangGraph 메인 State"""
    # === 입력 (API에서 주입) ===
    user_query: str
    user_profile: UserProfile
    
    # === 오케스트레이터 ===
    intent: Intent
    
    # === 정보추출 (chitchat 제외) ===
    extracted_info: ExtractedInfo
    final_conditions: FinalConditions
    
    # === 쿼리 리라이터 ===
    rewritten_query: str
    
    # === 검색/매칭 결과 ===
    search_results: List[PolicyResult]
    matched_policies: List[PolicyResult]
    
    # === 최종 출력 ===
    response: str
    
    # === 에러 ===
    error: str