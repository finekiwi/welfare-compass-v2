"""
[DEPRECATED - 실험 종료]

Cohere API 리랭커는 실험 종료되었습니다.
최종 결정: BGE 리랭커 (bge-reranker-v2-m3)

BGE 리랭커를 사용하려면:
- ensemble_retriever_bge.py 사용
- 또는 local_reranker.py의 LocalReranker("bge-reranker-v2-m3") 직접 사용

이 파일은 참고용으로만 보존되어 있습니다.
"""

# """Cohere API 리랭커"""
#
# import os
# import time
# from typing import List, Optional
#
# from langchain_core.documents import Document
#
# from embeddings.config import RerankerConfig
# from embeddings.rerankers.base import BaseReranker, RerankResult
#
#
# class CohereReranker(BaseReranker):
#     """Cohere Rerank API"""
#
#     def __init__(self, model: str = None):
#         self.model = model or RerankerConfig.COHERE_MODEL
#         self._client = None
#
#     @property
#     def name(self) -> str:
#         return "cohere"
#
#     @property
#     def client(self):
#         if self._client is None:
#             import cohere
#             api_key = os.getenv("COHERE_API_KEY")
#             if not api_key:
#                 raise ValueError("COHERE_API_KEY 환경변수 필요")
#             self._client = cohere.Client(api_key)
#         return self._client
#
#     def rerank(
#         self,
#         query: str,
#         documents: List[Document],
#         top_k: int = 10,
#         max_retries: int = None,
#     ) -> RerankResult:
#         """리랭킹 with exponential backoff retry"""
#         if not documents:
#             return RerankResult([], 0.0, self.name)
#
#         if max_retries is None:
#             max_retries = RerankerConfig.COHERE_MAX_RETRIES
#
#         texts = [self._format_doc(doc) for doc in documents]
#
#         for attempt in range(max_retries):
#             try:
#                 start = time.perf_counter()
#                 response = self.client.rerank(
#                     model=self.model,
#                     query=query,
#                     documents=texts,
#                     top_n=min(top_k, len(documents)),
#                     return_documents=False
#                 )
#                 latency = (time.perf_counter() - start) * 1000
#
#                 # 성공 시 결과 반환
#                 reranked = []
#                 for r in response.results:
#                     doc = documents[r.index]
#                     doc.metadata['rerank_score'] = r.relevance_score
#                     doc.metadata['reranker'] = self.name
#                     reranked.append(doc)
#
#                 return RerankResult(reranked, latency, self.name)
#
#             except Exception as e:
#                 error_str = str(e)
#
#                 # 재시도 가능 여부 판단
#                 should_retry = self._should_retry(error_str, attempt, max_retries)
#
#                 if should_retry:
#                     wait_time = self._calculate_backoff(e, attempt)
#                     print(f"⏳ Cohere 재시도 {attempt+1}/{max_retries} (대기: {wait_time}초, 에러: {error_str[:50]})")
#                     time.sleep(wait_time)
#                     continue
#                 else:
#                     # 재시도 불가능한 에러 또는 최대 재시도 도달
#                     error_msg = f"Cohere reranking failed after {attempt+1} attempts: {error_str}"
#                     print(f"❌ {error_msg}")
#                     raise RuntimeError(error_msg)
#
#         # 모든 재시도 실패 (이 코드에는 도달하지 않지만 안전장치)
#         raise RuntimeError(f"Cohere reranking failed after {max_retries} retries")
#
#     def _should_retry(self, error_str: str, attempt: int, max_retries: int) -> bool:
#         """재시도 가능 여부 판단"""
#         if attempt >= max_retries - 1:
#             return False
#
#         # 429 (Too Many Requests), 500, 502, 503, 504는 재시도
#         retry_codes = ["429", "500", "502", "503", "504", "Too Many Requests", "timeout"]
#         return any(code in error_str for code in retry_codes)
#
#     def _calculate_backoff(self, error, attempt: int) -> int:
#         """Exponential backoff 계산"""
#         # Retry-After 헤더 확인 (Cohere API가 제공하는 경우)
#         if hasattr(error, 'response') and error.response:
#             retry_after = error.response.headers.get('Retry-After')
#             if retry_after:
#                 try:
#                     return int(retry_after)
#                 except ValueError:
#                     pass
#
#         # Exponential backoff: 1, 2, 4, 8, 16초
#         return min(2 ** attempt, RerankerConfig.COHERE_MAX_DELAY)
#
#
# # 하위 호환용
# def get_cohere_client():
#     """기존 코드 호환"""
#     api_key = os.getenv("COHERE_API_KEY")
#     if not api_key:
#         return None
#     import cohere
#     return cohere.Client(api_key)
#
#
# def rerank_with_cohere(
#     query: str,
#     documents: List[Document],
#     top_k: int = 10,
#     model: str = None
# ) -> List[Document]:
#     """기존 API 호환 - List[Document] 반환"""
#     try:
#         reranker = CohereReranker(model)
#         return reranker.rerank(query, documents, top_k).documents
#     except RuntimeError as e:
#         # 재시도 모두 실패 → 상위로 전파
#         raise
#     except ValueError as e:
#         # API 키 없음
#         print("⚠️ COHERE_API_KEY 없음")
#         raise RuntimeError("COHERE_API_KEY not found")
