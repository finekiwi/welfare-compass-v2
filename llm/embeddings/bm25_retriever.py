"""
BM25 리트리버 모듈

한국어 형태소 분석(Kiwi) + LangChain BM25Retriever
Dense 검색(vector_store.py)과 동일한 Document 구조 사용
"""

import os
import json
from functools import lru_cache
from typing import List, Optional

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

# ============================================================================
# 경로 설정
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '../../data/raw/seoul_policies.json')

# ============================================================================
# 한국어 토크나이저 (Kiwi)
# ============================================================================
@lru_cache(maxsize=1)
def get_kiwi():
    """Kiwi 인스턴스 싱글톤"""
    from kiwipiepy import Kiwi
    return Kiwi()


def korean_preprocess(text: str) -> List[str]:
    """한국어 형태소 분석 기반 전처리
    
    Args:
        text: 원본 텍스트
        
    Returns:
        토큰 리스트 (명사, 동사, 형용사 등 의미있는 품사만)
    """
    try:
        kiwi = get_kiwi()
        tokens = [
            token.form
            for token in kiwi.tokenize(text)
            if token.tag in ["NNG", "NNP", "VV", "VA", "XR"]
            
        ]
        return tokens if tokens else text.split()
    except Exception:
        return text.split()


# ============================================================================
# Document 생성 (vector_store.py와 동일한 구조)
# ============================================================================
def create_policy_text(policy: dict) -> str:
    """정책 데이터를 검색 최적화된 텍스트로 변환"""
    parts = []
    
    if policy.get('plcyNm'):
        parts.append(f"정책명: {policy['plcyNm']}")
        parts.append(policy['plcyNm'])
    
    if policy.get('plcyExplnCn'):
        parts.append(f"설명: {policy['plcyExplnCn']}")
    
    if policy.get('plcySprtCn'):
        parts.append(f"지원내용: {policy['plcySprtCn']}")
    
    if policy.get('sprtTrgtCn'):
        parts.append(f"대상: {policy['sprtTrgtCn']}")
    
    return " | ".join(parts)


def extract_metadata(policy: dict) -> dict:
    """정책 데이터에서 메타데이터 추출"""
    return {
        "plcyNo": policy.get('plcyNo', ''),
        "plcyNm": policy.get('plcyNm', ''),
        "minAge": int(policy.get('sprtTrgtMinAge') or 0),
        "maxAge": int(policy.get('sprtTrgtMaxAge') or 99),
        "region": policy.get('rgtrHghrkInstCdNm', ''),
        "earnCndSeCd": policy.get('earnCndSeCd', ''),
        "earnMaxAmt": policy.get('earnMaxAmt'),
        "lclsfNm": policy.get('lclsfNm', ''),
        "mclsfNm": policy.get('mclsfNm', ''),
        "aplyYmd": policy.get('aplyYmd', ''),
        "aplyUrlAddr": policy.get('aplyUrlAddr', ''),
        "plcySprtCn": policy.get('plcySprtCn', '')[:200] if policy.get('plcySprtCn') else '',
    }


def load_policy_documents() -> List[Document]:
    """정책 JSON 로드 → LangChain Document 리스트 변환"""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"정책 데이터 파일이 없습니다: {DATA_PATH}")
    
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        policies = json.load(f)
    
    documents = []
    for policy in policies:
        text = create_policy_text(policy)
        metadata = extract_metadata(policy)
        
        doc = Document(page_content=text, metadata=metadata)
        documents.append(doc)
    
    return documents


# ============================================================================
# BM25 리트리버 생성
# ============================================================================
_bm25_retriever: Optional[BM25Retriever] = None
_BM25_MAX_K = 50  # 싱글톤 초기화 시 사용할 최대 k


def get_bm25_retriever(k: int = _BM25_MAX_K) -> BM25Retriever:
    """BM25 리트리버 싱글톤 반환

    싱글톤 인스턴스의 k를 직접 변경하면 동시 요청 시 race condition이 발생하므로,
    최초 초기화 시에만 k를 적용한다. 호출마다 결과 수를 조절하려면
    search_policies_bm25()의 k 파라미터를 사용할 것.

    Args:
        k: 최초 초기화 시 적용할 검색 결과 개수 (이미 초기화된 경우 무시됨)

    Returns:
        BM25Retriever 인스턴스
    """
    global _bm25_retriever

    if _bm25_retriever is None:
        print("⚙️  BM25 리트리버 초기화 중...")
        documents = load_policy_documents()

        _bm25_retriever = BM25Retriever.from_documents(
            documents,
            preprocess_func=korean_preprocess,
            k=_BM25_MAX_K,
        )
        print(f"✅ BM25 리트리버 초기화 완료 (문서 {len(documents)}개)")

    return _bm25_retriever


def search_policies_bm25(query: str, k: int = 5) -> List[Document]:
    """BM25 기반 정책 검색

    Args:
        query: 검색 쿼리 (자연어)
        k: 반환할 결과 개수

    Returns:
        검색 결과 Document 리스트
    """
    retriever = get_bm25_retriever()
    results = retriever.invoke(query)
    return results[:k]


# ============================================================================
# 테스트
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("BM25 리트리버 테스트")
    print("="*60)
    
    # 토크나이저 테스트
    print("\n[1] 토크나이저 테스트")
    test_texts = [
        "27살 취준생인데 월세 지원받고 싶어요",
        "청년 주거 지원 정책",
    ]
    for text in test_texts:
        tokens = korean_preprocess(text)
        print(f"   '{text}'")
        print(f"   → {tokens}\n")
    
    # 검색 테스트
    print("[2] 검색 테스트")
    queries = ["월세 지원", "취업 지원", "창업 지원"]
    
    for query in queries:
        print(f"\n🔍 쿼리: '{query}'")
        results = search_policies_bm25(query, k=3)
        for i, doc in enumerate(results, 1):
            print(f"   {i}. {doc.metadata['plcyNm']}")
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60)