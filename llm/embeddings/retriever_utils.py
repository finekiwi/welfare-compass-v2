"""
리트리버 공통 유틸리티

ensemble_retriever.py와 ensemble_retriever_bge.py에서 공통으로 사용하는 함수 모음
"""

from typing import List

from langchain_core.documents import Document

from embeddings.vector_store import is_policy_active


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
            unique.append(doc)
    return unique


def filter_expired(
    documents: List[Document],
    include_expired: bool = False
) -> List[Document]:
    """마감된 정책 필터링 (나이/소득/지역은 룰베이스에서 처리)

    Args:
        documents: 검색 결과 Document 리스트
        include_expired: True면 마감된 정책도 포함

    Returns:
        필터링된 Document 리스트
    """
    if include_expired:
        return documents
    return [doc for doc in documents if is_policy_active(doc.metadata.get('aplyYmd', ''))]
