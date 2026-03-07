"""Cohere Rerank API 리랭커"""

import os
import time
from typing import List

from langchain_core.documents import Document

from embeddings.config import RerankerConfig
from embeddings.rerankers.base import BaseReranker, RerankResult


class CohereReranker(BaseReranker):
    """Cohere Rerank API (cohere SDK v5)"""

    def __init__(self, model: str = None):
        self._model = model or RerankerConfig.COHERE_MODEL
        self._client = None

    @property
    def name(self) -> str:
        return "cohere"

    @property
    def client(self):
        if self._client is None:
            import cohere
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError("COHERE_API_KEY 환경변수 필요")
            self._client = cohere.ClientV2(api_key=api_key)
        return self._client

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10,
        max_retries: int = None,
    ) -> RerankResult:
        """리랭킹 with exponential backoff retry"""
        if not documents:
            return RerankResult([], 0.0, self.name)

        if max_retries is None:
            max_retries = RerankerConfig.COHERE_MAX_RETRIES

        texts = [self._format_doc(doc) for doc in documents]

        for attempt in range(max_retries):
            try:
                start = time.perf_counter()
                response = self.client.rerank(
                    model=self._model,
                    query=query,
                    documents=texts,
                    top_n=min(top_k, len(documents)),
                    return_documents=False,
                )
                latency = (time.perf_counter() - start) * 1000

                reranked = []
                for r in response.results:
                    doc = documents[r.index]
                    doc.metadata["rerank_score"] = r.relevance_score
                    doc.metadata["reranker"] = self.name
                    reranked.append(doc)

                return RerankResult(reranked, latency, self.name)

            except Exception as e:
                error_str = str(e)
                should_retry = self._should_retry(error_str, attempt, max_retries)

                if should_retry:
                    wait_time = self._calculate_backoff(e, attempt)
                    print(f"Cohere 재시도 {attempt+1}/{max_retries} (대기: {wait_time}초, 에러: {error_str[:50]})")
                    time.sleep(wait_time)
                    continue
                else:
                    error_msg = f"Cohere reranking failed after {attempt+1} attempts: {error_str}"
                    raise RuntimeError(error_msg)

        raise RuntimeError(f"Cohere reranking failed after {max_retries} retries")

    def _should_retry(self, error_str: str, attempt: int, max_retries: int) -> bool:
        if attempt >= max_retries - 1:
            return False
        retry_codes = ["429", "500", "502", "503", "504", "Too Many Requests", "timeout"]
        return any(code in error_str for code in retry_codes)

    def _calculate_backoff(self, error, attempt: int) -> int:
        if hasattr(error, "response") and error.response:
            retry_after = error.response.headers.get("Retry-After")
            if retry_after:
                try:
                    return int(retry_after)
                except ValueError:
                    pass
        return min(2 ** attempt, RerankerConfig.COHERE_MAX_DELAY)
