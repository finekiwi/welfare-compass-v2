"""
Cohere 리랭커 테스트

실행: pytest test_reranker.py -v
"""

import os
import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document

# 테스트 대상 함수들
from ensemble_retriever import (
    rerank_with_cohere,
    get_cohere_client,
    remove_duplicates,
    filter_expired,
    COHERE_RERANK_MODEL,
)


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def sample_documents():
    """테스트용 Document 리스트"""
    return [
        Document(
            page_content="서울시 청년 월세 지원 사업입니다.",
            metadata={"plcyNo": "R2024010001", "plcyNm": "청년월세지원"}
        ),
        Document(
            page_content="취업 준비생을 위한 취업지원 프로그램입니다.",
            metadata={"plcyNo": "R2024010002", "plcyNm": "청년취업지원"}
        ),
        Document(
            page_content="청년 창업을 위한 자금 대출 지원입니다.",
            metadata={"plcyNo": "R2024010003", "plcyNm": "창업자금대출"}
        ),
    ]


@pytest.fixture
def mock_cohere_response():
    """Cohere API 응답 Mock"""
    mock_result = Mock()
    mock_result.results = [
        Mock(index=2, relevance_score=0.95),  # 창업자금대출
        Mock(index=0, relevance_score=0.85),  # 청년월세지원  
        Mock(index=1, relevance_score=0.70),  # 청년취업지원
    ]
    return mock_result


# ============================================================================
# rerank_with_cohere 테스트
# ============================================================================
class TestRerankWithCohere:
    """Cohere 리랭커 함수 테스트"""
    
    def test_empty_documents_returns_empty(self):
        """빈 문서 리스트 → 빈 리스트 반환"""
        result = rerank_with_cohere("쿼리", [])
        assert result == []
    
    @patch.dict(os.environ, {"COHERE_API_KEY": ""}, clear=True)
    def test_no_api_key_returns_original(self, sample_documents):
        """API 키 없으면 원본 그대로 반환 (graceful degradation)"""
        result = rerank_with_cohere("월세", sample_documents, top_k=2)
        assert len(result) == 2
        assert result[0].metadata["plcyNo"] == "R2024010001"  # 첫번째 그대로
    
    @patch("ensemble_retriever.get_cohere_client")
    def test_rerank_success(self, mock_client_fn, sample_documents, mock_cohere_response):
        """정상 리랭킹 동작 확인"""
        mock_client = Mock()
        mock_client.rerank.return_value = mock_cohere_response
        mock_client_fn.return_value = mock_client
        
        result = rerank_with_cohere("창업 대출", sample_documents, top_k=3)
        
        # 리랭킹된 순서 확인 (점수 높은 순)
        assert len(result) == 3
        assert result[0].metadata["plcyNm"] == "창업자금대출"  # 0.95
        assert result[1].metadata["plcyNm"] == "청년월세지원"   # 0.85
        assert result[2].metadata["plcyNm"] == "청년취업지원"   # 0.70
        
        # 리랭크 점수 메타데이터 확인
        assert result[0].metadata["rerank_score"] == 0.95
    
    @patch("ensemble_retriever.get_cohere_client")
    def test_rerank_api_error_returns_original(self, mock_client_fn, sample_documents):
        """API 에러 시 원본 반환"""
        mock_client = Mock()
        mock_client.rerank.side_effect = Exception("API Error")
        mock_client_fn.return_value = mock_client
        
        result = rerank_with_cohere("쿼리", sample_documents, top_k=2)
        
        assert len(result) == 2
        assert result[0].metadata["plcyNo"] == "R2024010001"  # 원본 순서
    
    @patch("ensemble_retriever.get_cohere_client")
    def test_top_k_less_than_docs(self, mock_client_fn, sample_documents):
        """top_k < 문서 수일 때 top_k만큼만 반환"""
        mock_response = Mock()
        mock_response.results = [Mock(index=0, relevance_score=0.9)]
        
        mock_client = Mock()
        mock_client.rerank.return_value = mock_response
        mock_client_fn.return_value = mock_client
        
        result = rerank_with_cohere("쿼리", sample_documents, top_k=1)
        assert len(result) == 1


# ============================================================================
# get_cohere_client 테스트
# ============================================================================
class TestGetCohereClient:
    """Cohere 클라이언트 생성 테스트"""
    
    @patch.dict(os.environ, {"COHERE_API_KEY": ""}, clear=True)
    def test_no_api_key_returns_none(self):
        """API 키 없으면 None 반환"""
        result = get_cohere_client()
        assert result is None
    
    @patch.dict(os.environ, {"COHERE_API_KEY": "test-key"})
    @patch("ensemble_retriever.cohere.Client")
    def test_valid_api_key_returns_client(self, mock_client_class):
        """API 키 있으면 클라이언트 반환"""
        mock_client_class.return_value = Mock()
        result = get_cohere_client()
        assert result is not None
        mock_client_class.assert_called_once_with("test-key")


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
        """중복 제거 확인"""
        docs = [
            Document(page_content="A", metadata={"plcyNo": "001", "plcyNm": "정책A"}),
            Document(page_content="B", metadata={"plcyNo": "002", "plcyNm": "정책B"}),
            Document(page_content="A2", metadata={"plcyNo": "001", "plcyNm": "정책A"}),  # 중복
        ]
        result = remove_duplicates(docs)
        assert len(result) == 2
        assert result[0].page_content == "A"  # 먼저 나온 거 유지
    
    def test_no_plcy_no_included(self):
        """plcyNo 없는 문서는 일단 포함"""
        docs = [
            Document(page_content="A", metadata={"plcyNm": "정책A"}),  # plcyNo 없음
            Document(page_content="B", metadata={"plcyNo": "001", "plcyNm": "정책B"}),
        ]
        result = remove_duplicates(docs)
        assert len(result) == 2


# ============================================================================
# filter_expired 테스트
# ============================================================================
class TestFilterExpired:
    """마감 필터링 테스트"""
    
    def test_include_expired_true(self):
        """include_expired=True면 모두 포함"""
        docs = [
            Document(page_content="A", metadata={"aplyYmd": "2020-01-01~2020-12-31"}),
            Document(page_content="B", metadata={"aplyYmd": "상시"}),
        ]
        result = filter_expired(docs, include_expired=True)
        assert len(result) == 2
    
    def test_filter_expired_policies(self):
        """마감된 정책 필터링"""
        docs = [
            Document(page_content="A", metadata={"aplyYmd": "2020-01-01~2020-12-31"}),  # 마감됨
            Document(page_content="B", metadata={"aplyYmd": "상시"}),  # 상시
        ]
        result = filter_expired(docs, include_expired=False)
        # 상시만 남아야 함
        assert len(result) == 1
        assert result[0].page_content == "B"


# ============================================================================
# Integration Test (선택적 - API 키 필요)
# ============================================================================
@pytest.mark.skipif(
    not os.getenv("COHERE_API_KEY"),
    reason="COHERE_API_KEY 환경변수 필요"
)
class TestIntegration:
    """실제 API 연동 테스트 (로컬에서만)"""
    
    def test_real_cohere_api(self, sample_documents):
        """실제 Cohere API 호출"""
        result = rerank_with_cohere(
            query="창업 자금 대출",
            documents=sample_documents,
            top_k=3
        )
        
        assert len(result) == 3
        assert all("rerank_score" in doc.metadata for doc in result)
        # 점수 내림차순 정렬 확인
        scores = [doc.metadata["rerank_score"] for doc in result]
        assert scores == sorted(scores, reverse=True)