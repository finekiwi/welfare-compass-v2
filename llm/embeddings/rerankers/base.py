"""리랭커 추상 클래스"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from langchain_core.documents import Document


@dataclass
class RerankResult:
    """리랭킹 결과"""
    documents: List[Document]
    latency_ms: float = 0.0
    reranker_type: str = ""
    
    def __iter__(self):
        return iter(self.documents)
    
    def __len__(self):
        return len(self.documents)
    
    def __getitem__(self, idx):
        return self.documents[idx]
    
    def __bool__(self):
        return len(self.documents) > 0


class BaseReranker(ABC):
    """리랭커 추상 클래스"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """리랭커 이름"""
        pass
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10,
    ) -> RerankResult:
        """문서 리랭킹"""
        pass
    
    def _format_doc(self, doc: Document) -> str:
        """문서를 리랭킹용 텍스트로 변환"""
        name = doc.metadata.get('plcyNm', '')
        return f"{name}: {doc.page_content}" if name else doc.page_content