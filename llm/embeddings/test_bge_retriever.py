"""
BGE 리랭커 테스트

실행: pytest test_bge_retriever.py -v
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document

from ensemble_retriever_bge import (
    rerank_with_bge,
    remove_duplicates,
    filter_expired,
    BGE_MODEL_TYPE,
)
from embeddings.rerankers.base import RerankResult


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def sample_documents():
    """테스트용 Document 리스트"""
    return [
        Document(
            page_content="서울시 청년 월세 지원 사업입니다.",
            metadata={"plcyNo": "R2024010001", "plcyNm": "청년월세지원"},
        ),
        Document(
            page_content="취업 준비생을 위한 취업지원 프로그램입니다.",
            metadata={"plcyNo": "R2024010002", "plcyNm": "청년취업지원"},
        ),
        Document(
            page_content="청년 창업을 위한 자금 대출 지원입니다.",
            metadata={"plcyNo": "R2024010003", "plcyNm": "창업자금대출"},
        ),
    ]


# ============================================================================
# rerank_with_bge 테스트
# ============================================================================
class TestRerankWithBge:
    """BGE 리랭커 함수 테스트"""

    def test_empty_documents_returns_empty(self):
        """빈 문서 리스트 → 빈 리스트 반환"""
        docs, latency = rerank_with_bge("쿼리", [])
        assert docs == []
        assert latency == 0.0

    @patch("ensemble_retriever_bge.get_bge_reranker")
    def test_rerank_success(self, mock_get_reranker, sample_documents):
        """정상 리랭킹 동작 확인"""
        reranked = [
            Document(
                page_content=sample_documents[2].page_content,
                metadata={**sample_documents[2].metadata, "rerank_score": 0.95, "reranker": BGE_MODEL_TYPE},
            ),
            Document(
                page_content=sample_documents[0].page_content,
                metadata={**sample_documents[0].metadata, "rerank_score": 0.85, "reranker": BGE_MODEL_TYPE},
            ),
        ]
        mock_reranker = Mock()
        mock_reranker.rerank.return_value = RerankResult(
            documents=reranked, latency_ms=42.0, reranker_type=BGE_MODEL_TYPE
        )
        mock_get_reranker.return_value = mock_reranker

        docs, latency = rerank_with_bge("창업 대출", sample_documents, top_k=2)

        assert len(docs) == 2
        assert docs[0].metadata["plcyNm"] == "창업자금대출"
        assert docs[1].metadata["plcyNm"] == "청년월세지원"
        assert docs[0].metadata["rerank_score"] == 0.95
        assert latency == 42.0

    @patch("ensemble_retriever_bge.get_bge_reranker")
    def test_rerank_score_stored_in_metadata(self, mock_get_reranker, sample_documents):
        """리랭크 점수가 메타데이터에 저장되는지 확인"""
        scored_doc = Document(
            page_content=sample_documents[0].page_content,
            metadata={**sample_documents[0].metadata, "rerank_score": 0.77, "reranker": BGE_MODEL_TYPE},
        )
        mock_reranker = Mock()
        mock_reranker.rerank.return_value = RerankResult(
            documents=[scored_doc], latency_ms=10.0
        )
        mock_get_reranker.return_value = mock_reranker

        docs, _ = rerank_with_bge("월세", sample_documents, top_k=1)

        assert "rerank_score" in docs[0].metadata
        assert docs[0].metadata["rerank_score"] == 0.77

    @patch("ensemble_retriever_bge.get_bge_reranker")
    def test_reranker_called_with_correct_args(self, mock_get_reranker, sample_documents):
        """reranker.rerank()에 올바른 인자가 전달되는지 확인"""
        mock_reranker = Mock()
        mock_reranker.rerank.return_value = RerankResult(documents=[], latency_ms=0.0)
        mock_get_reranker.return_value = mock_reranker

        rerank_with_bge("청년 지원", sample_documents, top_k=3)

        mock_reranker.rerank.assert_called_once_with("청년 지원", sample_documents, 3)


# ============================================================================
# remove_duplicates 테스트
# ============================================================================
class TestRemoveDuplicates:
    """중복 제거 함수 테스트"""

    def test_no_duplicates(self, sample_documents):
        """중복 없으면 그대로"""
        result = remove_duplicates(sample_documents)
        assert len(result) == 3

    def test_remove_duplicates(self):
        """동일 plcyNo 중복 제거 확인"""
        docs = [
            Document(page_content="A", metadata={"plcyNo": "001", "plcyNm": "정책A"}),
            Document(page_content="B", metadata={"plcyNo": "002", "plcyNm": "정책B"}),
            Document(page_content="A2", metadata={"plcyNo": "001", "plcyNm": "정책A"}),  # 중복
        ]
        result = remove_duplicates(docs)
        assert len(result) == 2
        assert result[0].page_content == "A"  # 먼저 나온 것 유지

    def test_no_plcy_no_included(self):
        """plcyNo 없는 문서는 포함"""
        docs = [
            Document(page_content="A", metadata={"plcyNm": "정책A"}),  # plcyNo 없음
            Document(page_content="B", metadata={"plcyNo": "001", "plcyNm": "정책B"}),
        ]
        result = remove_duplicates(docs)
        assert len(result) == 2

    def test_empty_list(self):
        """빈 리스트 → 빈 리스트"""
        assert remove_duplicates([]) == []


# ============================================================================
# filter_expired 테스트
# ============================================================================
class TestFilterExpired:
    """마감 필터링 테스트"""

    def test_include_expired_true(self):
        """include_expired=True면 모두 포함"""
        docs = [
            Document(page_content="A", metadata={"aplyYmd": "20200101~20201231"}),
            Document(page_content="B", metadata={"aplyYmd": "20300101~20301231"}),
        ]
        result = filter_expired(docs, include_expired=True)
        assert len(result) == 2

    def test_filter_expired_policies(self):
        """마감된 정책은 제외"""
        docs = [
            Document(page_content="A", metadata={"aplyYmd": "20200101~20201231"}),  # 마감
            Document(page_content="B", metadata={"aplyYmd": "20300101~20301231"}),  # 미래
        ]
        result = filter_expired(docs, include_expired=False)
        assert len(result) == 1
        assert result[0].page_content == "B"

    def test_empty_list(self):
        """빈 리스트 → 빈 리스트"""
        assert filter_expired([], include_expired=False) == []
