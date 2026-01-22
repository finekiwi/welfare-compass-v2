"""
앙상블 리트리버 모듈

BM25 + Dense 검색 결과를 EnsembleRetriever로 통합
- BM25: 키워드 기반 검색 (Kiwi 한국어 토크나이저)
- Dense: 의미 기반 검색 (OpenAI Embeddings + Chroma)
- 마감일만 필터링, 나머지 조건은 룰베이스에서 처리
"""

import os
import sys
from typing import List

from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document

# 상위 디렉토리 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings.vector_store import load_vector_db, is_policy_active
from embeddings.bm25_retriever import get_bm25_retriever, search_policies_bm25


# ============================================================================
# 상수
# ============================================================================
DEFAULT_BM25_WEIGHT = 0.4
DEFAULT_DENSE_WEIGHT = 0.6
ENSEMBLE_FETCH_K = 20  # 각 retriever가 가져올 개수


# ============================================================================
# Dense Retriever 래퍼
# ============================================================================
def get_dense_retriever(k: int = ENSEMBLE_FETCH_K):
    """Chroma DB → LangChain retriever 변환
    
    Args:
        k: 검색 결과 개수
        
    Returns:
        VectorStoreRetriever
    """
    db = load_vector_db()
    return db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )


def search_policies_dense(query: str, k: int = 5) -> List[Document]:
    """Dense 검색 단독 실행 (비교 테스트용)"""
    retriever = get_dense_retriever(k=k)
    return retriever.invoke(query)


# ============================================================================
# 앙상블 리트리버
# ============================================================================
def create_ensemble_retriever(
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
    k: int = ENSEMBLE_FETCH_K
) -> EnsembleRetriever:
    """BM25 + Dense 앙상블 리트리버 생성
    
    Args:
        bm25_weight: BM25 가중치 (기본 0.4)
        dense_weight: Dense 가중치 (기본 0.6)
        k: 각 retriever 검색 개수
        
    Returns:
        EnsembleRetriever
        
    Example:
        >>> retriever = create_ensemble_retriever(bm25_weight=0.3, dense_weight=0.7)
        >>> results = retriever.invoke("월세 지원")
    """
    # 가중치 정규화 (합이 1이 되도록)
    total = bm25_weight + dense_weight
    bm25_weight = bm25_weight / total
    dense_weight = dense_weight / total
    
    bm25_retriever = get_bm25_retriever(k=k)
    dense_retriever = get_dense_retriever(k=k)
    
    return EnsembleRetriever(
        retrievers=[bm25_retriever, dense_retriever],
        weights=[bm25_weight, dense_weight]
    )


# ============================================================================
# 중복 제거
# ============================================================================
def remove_duplicates(documents: List[Document]) -> List[Document]:
    """plcyNo 기준 중복 제거
    
    Args:
        documents: Document 리스트
        
    Returns:
        중복 제거된 Document 리스트
    """
    seen = set()
    unique = []
    for doc in documents:
        plcy_no = doc.metadata.get('plcyNo')
        if plcy_no and plcy_no not in seen:
            seen.add(plcy_no)
            unique.append(doc)
        elif not plcy_no:
            # plcyNo 없으면 일단 포함
            unique.append(doc)
    return unique


# ============================================================================
# 중복 제거
# ============================================================================
def remove_duplicates(documents: List[Document]) -> List[Document]:
    """plcyNo 기준 중복 제거 (먼저 나온 거 유지)
    
    Args:
        documents: Document 리스트
        
    Returns:
        중복 제거된 Document 리스트
    """
    seen = set()
    unique = []
    for doc in documents:
        plcy_no = doc.metadata.get('plcyNo')
        if plcy_no and plcy_no not in seen:
            seen.add(plcy_no)
            unique.append(doc)
        elif not plcy_no:
            # plcyNo 없으면 일단 포함 (데이터 문제 대비)
            unique.append(doc)
    return unique


# ============================================================================
# 마감일 필터링 (나머지는 룰베이스에서 처리)
# ============================================================================
def filter_expired(
    documents: List[Document],
    include_expired: bool = False
) -> List[Document]:
    """마감된 정책만 필터링 (나이/소득/지역은 룰베이스에서 처리)
    
    Args:
        documents: 검색 결과 Document 리스트
        include_expired: True면 마감된 정책도 포함
        
    Returns:
        필터링된 Document 리스트
    """
    if include_expired:
        return documents
    
    return [
        doc for doc in documents
        if is_policy_active(doc.metadata.get('aplyYmd', ''))
    ]


# ============================================================================
# 통합 검색 함수 (메인 API)
# ============================================================================
def ensemble_search(
    query: str,
    # TODO: 실데이터 연동 후 기본값 False로 변경
    include_expired: bool = True,
    k: int = 10,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
    verbose: bool = False
) -> List[Document]:
    """앙상블 검색 (BM25 + Dense, 마감일만 필터링)
    
    나이, 소득, 지역 등 세부 조건은 룰베이스 매칭에서 처리.
    검색 단계에서는 관련 후보를 넓게 가져오는 것이 목적.
    
    Args:
        query: 검색 쿼리
        include_expired: 마감 정책 포함 여부
        k: 반환할 결과 개수 (룰베이스에 전달할 후보 수)
        bm25_weight: BM25 가중치
        dense_weight: Dense 가중치
        verbose: 디버깅 출력
        
    Returns:
        Document 리스트
        
    Example:
        >>> results = ensemble_search("월세 지원", k=10)
        >>> # 이후 룰베이스 매칭으로 전달
        >>> matched = match_welfare_programs(user_info, results_df)
    """
    ensemble = create_ensemble_retriever(
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
        k=ENSEMBLE_FETCH_K
    )
    
    results = ensemble.invoke(query)
    
    # 중복 제거
    results = remove_duplicates(results)
    
    if verbose:
        print(f"🔍 앙상블 검색: {len(results)}개")
        print(f"   BM25:{bm25_weight:.1f} / Dense:{dense_weight:.1f}")
    
    # 중복 제거 (plcyNo 기준)
    results = remove_duplicates(results)
    
    if verbose:
        print(f"📋 중복 제거 후: {len(results)}개")
    
    # 마감일만 필터링
    filtered = filter_expired(results, include_expired)
    
    if verbose:
        expired_count = len(results) - len(filtered)
        print(f"📊 마감 정책 제외: {expired_count}개 제거 → {len(filtered)}개")
    
    final = filtered[:k]
    
    if not final:
        print(f"⚠️  검색 결과 없음: '{query}'")
    
    return final


# ============================================================================
# 비교 테스트
# ============================================================================
def compare_retrievers(query: str, k: int = 5):
    """BM25 vs Dense vs Ensemble 비교 테스트
    
    Args:
        query: 검색 쿼리
        k: 각 방식별 결과 개수
    """
    print(f"\n{'='*60}")
    print(f"🔍 쿼리: '{query}'")
    print('='*60)
    
    # 1. BM25 단독
    print(f"\n[BM25 단독]")
    bm25_results = search_policies_bm25(query, k=k)
    for i, r in enumerate(bm25_results, 1):
        print(f"  {i}. {r.metadata['plcyNm']}")
    bm25_names = {r.metadata['plcyNm'] for r in bm25_results}
    
    # 2. Dense 단독  
    print(f"\n[Dense 단독]")
    dense_results = search_policies_dense(query, k=k)
    for i, r in enumerate(dense_results, 1):
        print(f"  {i}. {r.metadata['plcyNm']}")
    dense_names = {r.metadata['plcyNm'] for r in dense_results}
    
    # 3. 앙상블 (4:6)
    print(f"\n[앙상블 BM25:0.4 / Dense:0.6]")
    ensemble_46 = ensemble_search(query, k=k, bm25_weight=0.4, dense_weight=0.6)
    for i, r in enumerate(ensemble_46, 1):
        name = r.metadata['plcyNm']
        # 어디서 왔는지 표시
        source = []
        if name in bm25_names:
            source.append("BM25")
        if name in dense_names:
            source.append("Dense")
        source_str = f" ← {'+'.join(source)}" if source else " ← 순위밖"
        print(f"  {i}. {name}{source_str}")
    
    # 4. 앙상블 (5:5)
    print(f"\n[앙상블 BM25:0.5 / Dense:0.5]")
    ensemble_55 = ensemble_search(query, k=k, bm25_weight=0.5, dense_weight=0.5)
    for i, r in enumerate(ensemble_55, 1):
        name = r.metadata['plcyNm']
        source = []
        if name in bm25_names:
            source.append("BM25")
        if name in dense_names:
            source.append("Dense")
        source_str = f" ← {'+'.join(source)}" if source else " ← 순위밖"
        print(f"  {i}. {name}{source_str}")
    
    # 5. 앙상블 (7:3) - BM25 강조
    print(f"\n[앙상블 BM25:0.7 / Dense:0.3]")
    ensemble_73 = ensemble_search(query, k=k, bm25_weight=0.7, dense_weight=0.3)
    for i, r in enumerate(ensemble_73, 1):
        name = r.metadata['plcyNm']
        source = []
        if name in bm25_names:
            source.append("BM25")
        if name in dense_names:
            source.append("Dense")
        source_str = f" ← {'+'.join(source)}" if source else " ← 순위밖"
        print(f"  {i}. {name}{source_str}")
    
    # 결과 분석
    print(f"\n[분석]")
    overlap = bm25_names & dense_names
    only_bm25 = bm25_names - dense_names
    only_dense = dense_names - bm25_names
    print(f"  - BM25 ∩ Dense (둘 다): {len(overlap)}개")
    print(f"  - BM25만: {len(only_bm25)}개")
    print(f"  - Dense만: {len(only_dense)}개")


# ============================================================================
# 메인 테스트
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("앙상블 리트리버 비교 테스트")
    print("="*60)
    
    # 테스트 쿼리들
    compare_retrievers("월세 지원", k=5)
    compare_retrievers("취업 지원", k=5)
    compare_retrievers("창업 지원", k=5)
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")