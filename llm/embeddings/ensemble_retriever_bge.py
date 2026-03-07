"""
앙상블 리트리버 (BGE 리랭커 전용)

BGE 리랭커만 사용하는 간소화된 앙상블 검색 구현입니다.
실험 종료 후 프로덕션 사용을 위한 깔끔한 버전입니다.

주요 특징:
- BGE (bge-reranker-v2-m3) 리랭커만 지원
- 레거시 파라미터 제거 (use_reranker 등)
- 단순하고 명확한 API
- 최적화된 기본값

사용 예시:
    from llm.embeddings.ensemble_retriever_bge import ensemble_search_with_bge

    # 기본 사용
    results = ensemble_search_with_bge("청년 창업 지원", top_k=5)

    # 메타데이터 포함
    result = ensemble_search_with_bge(
        "주거 지원",
        top_k=10,
        return_metadata=True
    )
    print(f"검색 시간: {result.latency_ms:.0f}ms")
    print(f"리랭커: {result.reranker_type}")
"""

import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Union

from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings.vector_store import load_vector_db, is_policy_active
from embeddings.bm25_retriever import get_bm25_retriever
from embeddings.config import RerankerConfig, RetrieverConfig
from embeddings.rerankers import get_reranker


# ============================================================================
# 상수
# ============================================================================
DEFAULT_BM25_WEIGHT = RetrieverConfig.DEFAULT_BM25_WEIGHT
DEFAULT_DENSE_WEIGHT = RetrieverConfig.DEFAULT_DENSE_WEIGHT
DEFAULT_RETRIEVE_K = RetrieverConfig.DEFAULT_RETRIEVE_K  # 20
DEFAULT_TOP_K = RetrieverConfig.DEFAULT_TOP_K            # 10
BGE_MODEL_TYPE = "bge-reranker-v2-m3"


# ============================================================================
# 검색 결과 클래스
# ============================================================================
@dataclass
class SearchResult:
    """BGE 검색 결과 + 메타정보"""
    documents: List[Document]
    latency_ms: float = 0.0
    reranker_type: str = BGE_MODEL_TYPE
    retrieve_k: int = 0
    final_count: int = 0

    def __iter__(self):
        return iter(self.documents)

    def __len__(self):
        return len(self.documents)

    def __getitem__(self, idx):
        return self.documents[idx]

    def __bool__(self):
        return len(self.documents) > 0


# ============================================================================
# Dense Retriever
# ============================================================================
def get_dense_retriever(k: int = DEFAULT_RETRIEVE_K):
    """Chroma DB → LangChain retriever 변환"""
    db = load_vector_db()
    return db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )


# ============================================================================
# 앙상블 리트리버
# ============================================================================
def create_ensemble_retriever(
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
    k: int = DEFAULT_RETRIEVE_K
) -> EnsembleRetriever:
    """BM25 + Dense 앙상블 리트리버 생성"""
    total = bm25_weight + dense_weight
    bm25_weight = bm25_weight / total
    dense_weight = dense_weight / total

    return EnsembleRetriever(
        retrievers=[get_bm25_retriever(k=k), get_dense_retriever(k=k)],
        weights=[bm25_weight, dense_weight]
    )


# ============================================================================
# 필터링
# ============================================================================
def remove_duplicates(documents: List[Document]) -> List[Document]:
    """plcyNo 기준 중복 제거"""
    seen = set()
    unique = []
    for doc in documents:
        plcy_no = doc.metadata.get('plcyNo')
        if plcy_no and plcy_no not in seen:
            seen.add(plcy_no)
            unique.append(doc)
        elif not plcy_no:
            unique.append(doc)
    return unique


def filter_expired(documents: List[Document], include_expired: bool = False) -> List[Document]:
    """마감 정책 필터링"""
    if include_expired:
        return documents
    return [doc for doc in documents if is_policy_active(doc.metadata.get('aplyYmd', ''))]


# ============================================================================
# 리랭커 (config 기반 팩토리)
# ============================================================================
_reranker_cache = None


def _get_reranker():
    """RerankerConfig.DEFAULT_TYPE 기반 리랭커 인스턴스 반환 (캐싱)"""
    global _reranker_cache
    if _reranker_cache is None:
        _reranker_cache = get_reranker(RerankerConfig.DEFAULT_TYPE)
    return _reranker_cache


def _get_reranker_type_name() -> str:
    """현재 설정된 리랭커 타입명 반환"""
    reranker = _get_reranker()
    if reranker is None:
        return "none"
    return reranker.name


def rerank_documents_with_config(
    query: str,
    documents: List[Document],
    top_k: int = DEFAULT_TOP_K,
) -> tuple:
    """설정된 리랭커로 문서 재정렬

    Args:
        query: 검색 쿼리
        documents: 재정렬할 문서 리스트
        top_k: 반환할 상위 k개

    Returns:
        (reranked_documents, latency_ms) 튜플
    """
    if not documents:
        return [], 0.0

    reranker = _get_reranker()
    if reranker is None:
        return documents[:top_k], 0.0

    result = reranker.rerank(query, documents, top_k)
    return result.documents, result.latency_ms


# ============================================================================
# 메인 검색 함수
# ============================================================================
def ensemble_search_with_bge(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    retrieve_k: int = DEFAULT_RETRIEVE_K,
    include_expired: bool = True,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
    max_length: int = None,
    return_metadata: bool = False,
    verbose: bool = False,
) -> Union[List[Document], SearchResult]:
    """BGE 리랭커를 사용한 앙상블 검색

    검색 프로세스:
    1. BM25 + Dense 앙상블 검색 (retrieve_k * 2개 가져오기)
    2. 중복 제거 및 마감 정책 필터링
    3. BGE 리랭커로 재정렬 (top_k개 반환)

    Args:
        query: 검색 쿼리
        top_k: 최종 반환 개수 (기본값: 10)
        retrieve_k: 1차 검색 후보 수 (기본값: 20)
        include_expired: 마감 정책 포함 여부 (기본값: True)
        bm25_weight: BM25 가중치 (기본값: 0.4)
        dense_weight: Dense 가중치 (기본값: 0.6)
        max_length: BGE 리랭커 최대 토큰 길이 (None이면 기본값 8192)
        return_metadata: True이면 SearchResult 반환, False이면 List[Document] 반환
        verbose: 디버깅 정보 출력 여부

    Returns:
        return_metadata=True: SearchResult (documents + latency 정보)
        return_metadata=False: List[Document]

    Example:
        >>> # 기본 사용
        >>> results = ensemble_search_with_bge("청년 창업 지원", top_k=5)
        >>> for doc in results:
        ...     print(doc.metadata['plcyNm'])

        >>> # 메타데이터 포함
        >>> result = ensemble_search_with_bge("주거 지원", return_metadata=True)
        >>> print(f"검색 시간: {result.latency_ms:.0f}ms")
    """
    start_time = time.perf_counter()

    # 1. 앙상블 검색 (retrieve_k * 2개 가져오기)
    ensemble = create_ensemble_retriever(
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
        k=retrieve_k * 2
    )
    results = ensemble.invoke(query)

    if verbose:
        print(f"🔍 앙상블 검색: {len(results)}개")

    # 2. 중복 제거
    results = remove_duplicates(results)

    # 3. 마감 정책 필터링
    filtered = filter_expired(results, include_expired)

    if verbose:
        print(f"📋 필터 후: {len(filtered)}개")

    # 4. retrieve_k개로 자르기
    candidates = filtered[:retrieve_k]

    if verbose:
        print(f"📦 리랭킹 대상: {len(candidates)}개")

    # 5. 리랭킹 (config 기반)
    if not candidates:
        final_docs = []
        rerank_latency = 0.0
    else:
        final_docs, rerank_latency = rerank_documents_with_config(
            query,
            candidates,
            top_k=top_k,
        )

    total_latency = (time.perf_counter() - start_time) * 1000
    active_reranker = _get_reranker_type_name()

    if verbose:
        print(f"리랭킹 완료 ({active_reranker}): {len(final_docs)}개")
        print(f"총 시간: {total_latency:.0f}ms (리랭킹: {rerank_latency:.0f}ms)")

    # 결과 반환
    if return_metadata:
        return SearchResult(
            documents=final_docs,
            latency_ms=total_latency,
            reranker_type=active_reranker,
            retrieve_k=retrieve_k,
            final_count=len(final_docs)
        )
    else:
        return final_docs


# ============================================================================
# 테스트 함수
# ============================================================================
def test_bge_search(query: str = "청년 창업 지원", top_k: int = 5):
    """BGE 검색 테스트

    Args:
        query: 검색 쿼리
        top_k: 반환 개수
    """
    print(f"\n{'='*60}")
    print(f"🔍 BGE 리랭커 검색 테스트")
    print(f"{'='*60}")
    print(f"쿼리: {query}")
    print(f"Top-K: {top_k}")
    print()

    # 검색 실행
    result = ensemble_search_with_bge(
        query=query,
        top_k=top_k,
        return_metadata=True,
        verbose=True
    )

    print(f"\n{'='*60}")
    print(f"📊 검색 결과")
    print(f"{'='*60}")
    print(f"총 {len(result)}개 정책")
    print(f"검색 시간: {result.latency_ms:.0f}ms")
    print(f"리랭커: {result.reranker_type}")
    print()

    for i, doc in enumerate(result, 1):
        name = doc.metadata.get('plcyNm', '알 수 없음')
        score = doc.metadata.get('rerank_score', 0.0)
        plcy_no = doc.metadata.get('plcyNo', 'N/A')

        print(f"{i}. {name}")
        print(f"   점수: {score:.4f} | 정책번호: {plcy_no}")
        print(f"   내용: {doc.page_content[:100]}...")
        print()


# ============================================================================
# 메인
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BGE 리랭커 앙상블 검색 테스트")
    parser.add_argument("-q", "--query", default="청년 창업 지원", help="검색 쿼리")
    parser.add_argument("-k", "--top-k", type=int, default=5, help="반환 개수")
    parser.add_argument("--warmup", action="store_true", help="워밍업 수행")
    args = parser.parse_args()

    # 워밍업 (로컬 리랭커인 경우만 의미 있음)
    if args.warmup:
        reranker = _get_reranker()
        if reranker and hasattr(reranker, 'warmup'):
            reranker.warmup()
            print()

    # 테스트 실행
    test_bge_search(args.query, args.top_k)
