"""로컬 Cross-Encoder 리랭커"""

import time
from functools import lru_cache
from typing import List

from langchain_core.documents import Document

from embeddings.config import RerankerConfig
from embeddings.rerankers.base import BaseReranker, RerankResult


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    """싱글톤 모델 로드"""
    try:
        from FlagEmbedding import FlagReranker
        import torch
    except ImportError:
        raise ImportError(
            "로컬 리랭커 설치 필요:\n"
            "  uv pip install -e '.[local-reranker]'"
        )
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔄 리랭커 로딩: {model_name} ({device})...")
    
    model = FlagReranker(model_name, device=device, use_fp16=(device == "cuda"))
    print("✅ 로드 완료")
    return model


class LocalReranker(BaseReranker):
    """로컬 Cross-Encoder 리랭커"""
    
    def __init__(self, model_type: str, max_length: int = None):
        if not RerankerConfig.is_local(model_type):
            raise ValueError(f"Invalid: {model_type}")
        
        self._type = model_type
        self._model_name = RerankerConfig.get_model_name(model_type)
        self._max_length = max_length or RerankerConfig.DEFAULT_MAX_LENGTH
        self._model = None
    
    @property
    def name(self) -> str:
        return self._type
    
    @property
    def model(self):
        if self._model is None:
            self._model = _load_model(self._model_name)
        return self._model
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10,
    ) -> RerankResult:
        if not documents:
            return RerankResult([], 0.0, self.name)
        
        pairs = [[query, self._format_doc(doc)] for doc in documents]
        
        start = time.perf_counter()
        scores = self.model.compute_score(
            pairs, max_length=self._max_length, normalize=True
        )
        latency = (time.perf_counter() - start) * 1000
        
        if isinstance(scores, (int, float)):
            scores = [scores]
        
        scored = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        
        reranked = []
        for doc, score in scored[:top_k]:
            doc.metadata['rerank_score'] = float(score)
            doc.metadata['reranker'] = self.name
            reranked.append(doc)
        
        return RerankResult(reranked, latency, self.name)
    
    def warmup(self, runs: int = None):
        """워밍업"""
        runs = runs or RerankerConfig.WARMUP_RUNS
        print(f"🔥 Warming up {self.name}...")
        for _ in range(runs):
            self.model.compute_score([["test", "test"]], max_length=128)
        print("✅ 완료")


def warmup_reranker(model_type: str, runs: int = None):
    """편의 함수"""
    if RerankerConfig.is_local(model_type):
        LocalReranker(model_type).warmup(runs)