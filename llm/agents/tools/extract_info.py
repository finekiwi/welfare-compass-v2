"""
정보 추출 도구

사용자 발화에서 프로필 정보 추출 (LLM 기반)
- 나이, 소득수준, 지역, 고용상태, 관심분야
"""

from langchain_core.tools import tool


@tool
def extract_info(message: str) -> dict:
    """
    사용자 메시지에서 프로필 정보를 추출합니다.
    
    Args:
        message: 사용자 발화 텍스트
        
    Returns:
        추출된 정보 dict:
        - age: 나이 (int 또는 None)
        - income_level: 소득수준 (str 또는 None)
        - region: 거주지역 (str 또는 None)
        - employment_status: 고용상태 (str 또는 None)
        - interests: 관심분야 리스트 (list[str])
    
    Example:
        >>> extract_info("27살이고 강남에 살아요")
        {"age": 27, "region": "강남구", "interests": [], ...}
    """
    # TODO: BRAIN4-30에서 구현
    # - GPT-4o-mini로 정보 추출
    # - 프롬프트 기반 JSON 파싱
    
    return {
        "age": None,
        "income_level": None,
        "region": None,
        "employment_status": None,
        "interests": [],
        "_stub": True,  # stub 표시 (구현 후 삭제)
    }