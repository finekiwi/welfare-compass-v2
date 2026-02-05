"""
search_policies 도구

BM25 + Dense 앙상블 검색 + 리랭커
MCP 서버 호출 예정 (은영)

현재: Placeholder 또는 기존 ensemble_retriever 연동
"""

from typing import Optional
from langchain_core.tools import tool


# ============================================================================
# 상수
# ============================================================================

DEFAULT_TOP_K = 10
MAX_TOP_K = 20


# ============================================================================
# 도구 정의
# ============================================================================

@tool
def search_policies(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    정책을 검색합니다. BM25(키워드) + Dense(의미) 앙상블 검색을 수행합니다.
    
    Args:
        query: 검색 쿼리 (rewrite_query로 최적화된 키워드)
        top_k: 반환할 결과 개수 (기본 10, 최대 20)
    
    Returns:
        정책 리스트, 각 항목 (Django 모델 필드명):
        - policy_id: 정책 번호
        - title: 정책명
        - description: 정책 설명
        - support_content: 지원 내용
        - age_min, age_max: 나이 조건
        - district: 지역 (서울시 구)
        - income_level: 소득 조건
        - apply_url: 신청 URL
        - category: 대분류
    """
    # 범위 제한
    top_k = min(max(1, top_k), MAX_TOP_K)
    
    # ─────────────────────────────────────────────────────────────────────
    # TODO: MCP 서버 호출 구현 (Junyong)
    # 
    # from mcp import MCPClient
    # client = MCPClient("http://localhost:8000")
    # results = client.call("search_policies", query=query, top_k=top_k)
    # return results
    # ─────────────────────────────────────────────────────────────────────
    
    # ─────────────────────────────────────────────────────────────────────
    # 대안: 기존 ensemble_retriever 직접 호출
    # 
    # try:
    #     from embeddings.ensemble_retriever import search_policies_ensemble
    #     docs = search_policies_ensemble(query, top_k=top_k)
    #     return [doc_to_dict(doc) for doc in docs]
    # except ImportError:
    #     pass
    # ─────────────────────────────────────────────────────────────────────
    
    # Placeholder: 더미 데이터 (Django 모델 필드명)
    dummy_policies = [
        {
            "policy_id": "R2024010100001",
            "title": "청년월세한시특별지원",
            "description": "청년의 주거비 부담 완화를 위한 월세 지원 사업입니다.",
            "support_content": "월 최대 20만원, 최대 12개월 지원",
            "age_min": 19,
            "age_max": 34,
            "district": "서울특별시",
            "income_level": "중위소득 60% 이하",
            "apply_url": "https://www.youthcenter.go.kr",
            "category": "주거",
        },
        {
            "policy_id": "R2024010100002",
            "title": "청년내일저축계좌",
            "description": "청년의 자산형성을 위한 정부 매칭 저축 사업입니다.",
            "support_content": "본인 저축액 1:1~1:3 매칭, 최대 1,440만원",
            "age_min": 19,
            "age_max": 34,
            "district": "서울특별시",
            "income_level": "중위소득 100% 이하",
            "apply_url": "https://www.bokjiro.go.kr",
            "category": "금융",
        },
        {
            "policy_id": "R2024010100003",
            "title": "청년취업성공패키지",
            "description": "청년 맞춤형 취업 지원 서비스입니다.",
            "support_content": "취업상담, 직업훈련, 취업알선 + 참여수당",
            "age_min": 18,
            "age_max": 34,
            "district": "서울특별시",
            "income_level": "무관",
            "apply_url": "https://www.work.go.kr",
            "category": "일자리",
        },
        {
            "policy_id": "R2024010100004",
            "title": "청년창업지원사업",
            "description": "청년 창업가를 위한 초기 자금 및 멘토링 지원입니다.",
            "support_content": "최대 1억원 창업자금 + 멘토링",
            "age_min": 19,
            "age_max": 39,
            "district": "서울특별시",
            "income_level": "무관",
            "apply_url": "https://www.sba.seoul.kr",
            "category": "일자리",
        },
        {
            "policy_id": "R2024010100005",
            "title": "청년 마음건강지원",
            "description": "청년 심리상담 및 정신건강 지원 서비스입니다.",
            "support_content": "전문상담 최대 8회 무료",
            "age_min": 19,
            "age_max": 34,
            "district": "서울특별시",
            "income_level": "무관",
            "apply_url": "https://www.blutouch.net",
            "category": "복지문화",
        },
    ]
    
    # 간단한 키워드 필터링 (Placeholder)
    query_keywords = query.lower().split()
    
    def relevance_score(policy: dict) -> int:
        text = f"{policy['title']} {policy['description']} {policy['support_content']}".lower()
        return sum(1 for kw in query_keywords if kw in text)
    
    # 관련도 순 정렬
    sorted_policies = sorted(dummy_policies, key=relevance_score, reverse=True)
    
    return sorted_policies[:top_k]


# ============================================================================
# 헬퍼 함수
# ============================================================================

def doc_to_dict(doc) -> dict:
    """LangChain Document → dict 변환 (Django 모델 필드명)"""
    return {
        "policy_id": doc.metadata.get("plcyNo", ""),
        "title": doc.metadata.get("plcyNm", ""),
        "description": doc.page_content[:300],
        "support_content": doc.metadata.get("plcySprtCn", ""),
        "age_min": doc.metadata.get("minAge", 0),
        "age_max": doc.metadata.get("maxAge", 99),
        "district": doc.metadata.get("region", ""),  # TODO: rgtrInstCdNm에서 구 추출
        "income_level": doc.metadata.get("earnCndSeCd", ""),
        "apply_url": doc.metadata.get("aplyUrlAddr", ""),
        "category": "",  # TODO: lclsfNm 매핑
    }


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    test_queries = [
        "청년 월세 지원 주거",
        "청년 취업 일자리",
        "청년 창업 자금",
    ]
    
    for query in test_queries:
        print(f"검색: {query}")
        results = search_policies.invoke({"query": query, "top_k": 3})
        for r in results:
            print(f"  - {r['title']}")
        print("-" * 50)