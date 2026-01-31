"""
리랭커 패키지

사용:
    from embeddings.rerankers import get_reranker, rerank_documents
"""

from typing import Optional, List
from langchain_core.documents import Document

from embeddings.config import RerankerConfig, RerankerType
from embeddings.rerankers.base import BaseReranker, RerankResult


def get_reranker(
    reranker_type: RerankerType,
    max_length: int = None,
) -> Optional[BaseReranker]:
    """리랭커 팩토리"""
    if not RerankerConfig.is_valid(reranker_type):
        raise ValueError(f"Invalid: {reranker_type}")
    
    if reranker_type == "none":
        return None
    # elif reranker_type == "cohere":  # DEPRECATED - Cohere 실험 종료
    #     from embeddings.rerankers.cohere_reranker import CohereReranker
    #     return CohereReranker()
    else:
        from embeddings.rerankers.local_reranker import LocalReranker
        return LocalReranker(reranker_type, max_length)


def rerank_documents(
    query: str,
    documents: List[Document],
    reranker_type: RerankerType,
    top_k: int = 10,
    max_length: int = None,
) -> RerankResult:
    """리랭킹 수행"""
    if reranker_type == "none":
        return RerankResult(documents[:top_k], 0.0, "none")
    
    reranker = get_reranker(reranker_type, max_length)
    return reranker.rerank(query, documents, top_k)


# 하위 호환
from embeddings.rerankers.local_reranker import warmup_reranker
# from embeddings.rerankers.cohere_reranker import rerank_with_cohere, get_cohere_client  # DEPRECATED

__all__ = [
    "BaseReranker", "RerankResult",
    "get_reranker", "rerank_documents",
    "warmup_reranker",
    # "rerank_with_cohere", "get_cohere_client",  # DEPRECATED
]