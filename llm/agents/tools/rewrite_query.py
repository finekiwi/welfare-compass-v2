"""
쿼리 리라이팅 도구

일상어를 검색에 최적화된 키워드로 변환 (LLM 기반)
"""

from langchain_core.tools import tool


@tool
def rewrite_query(query: str) -> str:
    """
    사용자의 일상어 질문을 검색 키워드로 변환합니다.
    
    Args:
        query: 사용자 원본 질문
        
    Returns:
        검색에 최적화된 키워드 문자열
    
    Example:
        >>> rewrite_query("월세 도움 받을 수 있어?")
        "청년 월세 지원 주거 보조금"
    """
    # TODO: BRAIN4-30에서 구현
    # - GPT-4o-mini로 쿼리 변환
    # - 구어체 → 정책 용어 매핑
    
    # stub: 원본 그대로 반환
    return query