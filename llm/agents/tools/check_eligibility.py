"""
자격 매칭 도구

사용자 조건과 정책 자격요건 매칭 (룰베이스)
"""

from typing import Optional
from langchain_core.tools import tool


@tool
def check_eligibility(
    user_info: dict,
    policy_ids: Optional[list[str]] = None,
) -> list[dict]:
    """
    사용자 조건으로 정책 자격요건을 확인합니다. (룰베이스)
    
    Args:
        user_info: 사용자 정보 dict
            - age: 나이
            - income_level: 소득수준
            - region: 거주지역
            - employment_status: 고용상태
        policy_ids: 확인할 정책 ID 리스트 (None이면 전체 DB 매칭)
        
    Returns:
        매칭 결과 리스트, 각 항목은 dict:
        - policy_id: 정책 ID
        - name: 정책명
        - eligible: 적격 여부 (bool)
        - reason: 적격/부적격 사유
        - match_score: 매칭 점수 (0~100)
    
    Example:
        >>> check_eligibility({"age": 27, "region": "강남구"})
        [{"policy_id": "P001", "eligible": True, "reason": "모든 조건 충족", ...}, ...]
    """
    # TODO: BRAIN4-31에서 구현
    # - 기존 matching.py 연결
    # - 룰베이스 자격 필터링
    
    # stub: 샘플 응답
    return [
        {
            "policy_id": "STUB_001",
            "name": "[Stub] 샘플 정책",
            "eligible": True,
            "reason": "Stub 응답 - BRAIN4-31에서 실제 매칭 로직 연동 예정",
            "match_score": 0,
            "_stub": True,
        }
    ]