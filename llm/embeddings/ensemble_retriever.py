"""
앙상블 리트리버 모듈 (with Cohere Reranker)

BM25 + Dense 검색 결과를 EnsembleRetriever로 통합 후 Cohere로 재순위
- BM25: 키워드 기반 검색 (Kiwi 한국어 토크나이저)
- Dense: 의미 기반 검색 (OpenAI Embeddings + Chroma)
- Reranker: Cohere rerank-multilingual-v3.0
- 마감일만 필터링, 나머지 조건은 룰베이스에서 처리
"""

import os
import sys
from typing import List, Optional

import cohere
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document

# 상위 디렉토리 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings.vector_store import load_vector_db
from embeddings.bm25_retriever import get_bm25_retriever, search_policies_bm25
from embeddings.retriever_utils import remove_duplicates, filter_expired


# ============================================================================
# 상수
# ============================================================================
DEFAULT_BM25_WEIGHT = 0.4
DEFAULT_DENSE_WEIGHT = 0.6
ENSEMBLE_FETCH_K = 20  # 앙상블에서 가져올 개수 (리랭커 전)
RERANK_TOP_K = 10      # 리랭커 후 최종 반환 개수

# Cohere 설정
COHERE_RERANK_MODEL = "rerank-multilingual-v3.0"


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
# Cohere Reranker
# ============================================================================
def get_cohere_client() -> Optional[cohere.Client]:
    """Cohere 클라이언트 생성
    
    Returns:
        cohere.Client 또는 None (API 키 없으면)
    """
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        return None
    return cohere.Client(api_key)


def rerank_with_cohere(
    query: str,
    documents: List[Document],
    top_k: int = RERANK_TOP_K,
    model: str = COHERE_RERANK_MODEL
) -> List[Document]:
    """Cohere Rerank API로 문서 재순위
    
    Args:
        query: 검색 쿼리
        documents: 재순위할 Document 리스트
        top_k: 반환할 상위 결과 개수
        model: Cohere 모델명
        
    Returns:
        재순위된 Document 리스트
        
    Note:
        - COHERE_API_KEY 환경변수 필요
        - API 키 없거나 에러 시 원본 그대로 반환 (graceful degradation)
        
    Example:
        >>> docs = ensemble_search("월세", k=20)
        >>> reranked = rerank_with_cohere("월세 지원받고 싶어요", docs, top_k=10)
    """
    if not documents:
        return []
    
    client = get_cohere_client()
    if not client:
        print("⚠️  COHERE_API_KEY 없음 - 리랭킹 스킵")
        return documents[:top_k]
    
    # Document → text 변환 (리랭킹용)
    # page_content + 정책명 결합하면 더 정확
    texts = []
    for doc in documents:
        policy_name = doc.metadata.get('plcyNm', '')
        text = f"{policy_name}: {doc.page_content}"
        texts.append(text)
    
    try:
        response = client.rerank(
            model=model,
            query=query,
            documents=texts,
            top_n=min(top_k, len(documents)),
            return_documents=False  # index만 받음 (토큰 절약)
        )
        
        # 재순위된 index로 Document 재정렬
        reranked = []
        for result in response.results:
            idx = result.index
            doc = documents[idx]
            # 리랭커 점수 메타데이터에 추가 (디버깅/분석용)
            doc.metadata['rerank_score'] = result.relevance_score
            reranked.append(doc)
        
        return reranked
        
    except Exception as e:
        print(f"⚠️  Cohere 리랭킹 실패: {e}")
        return documents[:top_k]


# ============================================================================
# 통합 검색 함수 (메인 API)
# ============================================================================
def ensemble_search(
    query: str,
    # TODO: 실데이터 연동 후 기본값 False로 변경
    include_expired: bool = True,
    k: int = RERANK_TOP_K,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
    use_reranker: bool = True,
    verbose: bool = False
) -> List[Document]:
    """앙상블 검색 + 리랭킹 (BM25 + Dense → Cohere Rerank)
    
    나이, 소득, 지역 등 세부 조건은 룰베이스 매칭에서 처리.
    검색 단계에서는 관련 후보를 넓게 가져오는 것이 목적.
    
    파이프라인:
        쿼리 → 앙상블(BM25+Dense) → Top 20 → Cohere 리랭커 → Top 10
    
    Args:
        query: 검색 쿼리
        include_expired: 마감 정책 포함 여부
        k: 최종 반환 결과 개수 (리랭커 후)
        bm25_weight: BM25 가중치
        dense_weight: Dense 가중치
        use_reranker: Cohere 리랭커 사용 여부
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
    
    # Cohere 리랭킹
    if use_reranker and filtered:
        reranked = rerank_with_cohere(query, filtered, top_k=k)
        if verbose:
            print(f"🎯 리랭킹 완료: {len(reranked)}개")
            # 리랭크 점수 출력
            for i, doc in enumerate(reranked[:5], 1):
                score = doc.metadata.get('rerank_score', 'N/A')
                print(f"   {i}. {doc.metadata.get('plcyNm', '?')} (score: {score:.3f})")
        final = reranked
    else:
        final = filtered[:k]
        if verbose and not use_reranker:
            print(f"⏭️  리랭커 비활성화 - Top {k} 반환")
    
    if not final:
        print(f"⚠️  검색 결과 없음: '{query}'")
    
    return final


# ============================================================================
# 비교 테스트
# ============================================================================
def compare_retrievers(query: str, k: int = 5):
    """BM25 vs Dense vs Ensemble vs Reranked 비교 테스트
    
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
    
    # 3. 앙상블 (리랭커 OFF)
    print(f"\n[앙상블 BM25:0.4 / Dense:0.6 (리랭커 OFF)]")
    ensemble_no_rerank = ensemble_search(
        query, k=k, 
        bm25_weight=0.4, dense_weight=0.6, 
        use_reranker=False
    )
    for i, r in enumerate(ensemble_no_rerank, 1):
        name = r.metadata['plcyNm']
        source = []
        if name in bm25_names:
            source.append("BM25")
        if name in dense_names:
            source.append("Dense")
        source_str = f" ← {'+'.join(source)}" if source else " ← 순위밖"
        print(f"  {i}. {name}{source_str}")
    
    # 4. 앙상블 + 리랭커
    print(f"\n[앙상블 + Cohere 리랭커]")
    ensemble_reranked = ensemble_search(
        query, k=k, 
        bm25_weight=0.4, dense_weight=0.6, 
        use_reranker=True
    )
    for i, r in enumerate(ensemble_reranked, 1):
        name = r.metadata['plcyNm']
        score = r.metadata.get('rerank_score', 'N/A')
        source = []
        if name in bm25_names:
            source.append("BM25")
        if name in dense_names:
            source.append("Dense")
        source_str = f" ← {'+'.join(source)}" if source else " ← 순위밖"
        score_str = f" (score: {score:.3f})" if isinstance(score, float) else ""
        print(f"  {i}. {name}{source_str}{score_str}")
    
    # 결과 분석
    print(f"\n[분석]")
    overlap = bm25_names & dense_names
    only_bm25 = bm25_names - dense_names
    only_dense = dense_names - bm25_names
    print(f"  - BM25 ∩ Dense (둘 다): {len(overlap)}개")
    print(f"  - BM25만: {len(only_bm25)}개")
    print(f"  - Dense만: {len(only_dense)}개")
    
    # 리랭킹으로 순위 변동 분석
    ensemble_names = [r.metadata['plcyNm'] for r in ensemble_no_rerank]
    reranked_names = [r.metadata['plcyNm'] for r in ensemble_reranked]
    if ensemble_names != reranked_names:
        print(f"  - 리랭킹으로 순위 변동 있음 ✓")
    else:
        print(f"  - 리랭킹 후에도 순위 동일")


# ============================================================================
# 메인 테스트
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("앙상블 + 리랭커 테스트")
    print("="*60)
    
    # API 키 체크
    if not os.getenv("COHERE_API_KEY"):
        print("\n⚠️  COHERE_API_KEY 환경변수를 설정해주세요!")
        print("   export COHERE_API_KEY='your-api-key'")
        print("   또는 .env 파일에 추가\n")
    
    # 테스트 쿼리들
    compare_retrievers("월세 지원", k=5)
    compare_retrievers("취업 지원", k=5)
    compare_retrievers("창업 지원", k=5)
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")