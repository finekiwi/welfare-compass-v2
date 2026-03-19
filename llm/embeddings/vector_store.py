"""
벡터 DB 관리 모듈

Chroma를 사용한 정책 데이터 벡터화 및 검색 기능 제공
"""

from dotenv import load_dotenv
import os
import json
from datetime import datetime
import shutil
from typing import List, Optional, Dict, Any

# 환경변수 로드 (OpenAI API Key 등)
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

try:
    from llm.embeddings.policy_utils import create_policy_text, extract_metadata  # noqa: F401
except ModuleNotFoundError:
    # `PYTHONPATH=/app/llm`처럼 embeddings top-level로 실행하는 경로 호환
    from embeddings.policy_utils import create_policy_text, extract_metadata  # noqa: F401

# ============================================================================
# 경로 설정
# ============================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/chroma_db')
DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data/raw/seoul_policies.json')

# ============================================================================
# 상수
# ============================================================================
SEARCH_BUFFER_MULTIPLIER = 2  # 마감일 필터링 손실 대비 여유분
EMBEDDING_MODEL = "text-embedding-3-small"

# 소득 조건 코드 매핑
INCOME_CODES = {
    "무관": "0043001",
    "중위50이하": "0043002",
    "중위100이하": "0043003",
    "중위150이하": "0043004",
}

# ============================================================================
# 헬퍼 함수
# ============================================================================

def is_policy_active(aply_ymd: str) -> bool:
    """정책이 현재 활성 상태인지 확인 (마감일 기준)
    
    Args:
        aply_ymd: 신청기간 문자열 (예: "20240101~20241231")
        
    Returns:
        활성 상태면 True, 마감이면 False
    """
    if not aply_ymd or aply_ymd.strip() == '':
        return True  # 상시 모집
    
    today = datetime.now().strftime("%Y%m%d")
    
    try:
        # "YYYYMMDD~YYYYMMDD" 형식에서 종료일 추출
        if '~' in aply_ymd:
            end_date = aply_ymd.split('~')[-1].strip()
        else:
            end_date = aply_ymd.strip()
        
        return end_date >= today
    
    except Exception as e:
        print(f"⚠️  날짜 파싱 실패: {aply_ymd} ({e})")
        return True  # 파싱 실패 시 포함


# ============================================================================
# 메인 함수
# ============================================================================

def create_vector_db(force_recreate: bool = False) -> Chroma:
    """벡터 DB 생성 및 저장
    
    Args:
        force_recreate: True면 기존 DB 삭제 후 재생성
        
    Returns:
        생성된 Chroma 벡터 DB 객체
        
    Raises:
        FileNotFoundError: 정책 데이터 파일이 없는 경우
    """
    
    # 이미 존재하면 스킵 (force_recreate=False일 때)
    if os.path.exists(DB_PATH) and not force_recreate:
        stats = get_db_stats_lightweight()
        if sum(stats.get("collections", {}).values()) > 0:
            print(f"✅ 벡터 DB 이미 존재: {DB_PATH}")
            print(f"   재생성하려면 force_recreate=True로 호출하세요")
            return load_vector_db()
        print("⚠️  벡터 DB 디렉토리는 있지만 비어있음 — 새로 생성합니다")
    
    # 재생성 시 기존 DB 삭제 (볼륨 마운트 포인트 보존 위해 내용물만 삭제)
    if force_recreate and os.path.exists(DB_PATH):
        for item in os.listdir(DB_PATH):
            item_path = os.path.join(DB_PATH, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        print(f"🗑️  기존 벡터 DB 삭제: {DB_PATH}")
    
    # 임베딩 모델 초기화
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    
    # 정책 데이터 로드
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"정책 데이터 파일이 없습니다: {DATA_PATH}")
    
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        policies = json.load(f)
    
    print(f"📄 총 {len(policies)}개 정책 로드됨")
    
    # 텍스트 및 메타데이터 준비
    texts = []
    metadatas = []
    
    for policy in policies:
        text = create_policy_text(policy)
        metadata = extract_metadata(policy)
        
        texts.append(text)
        metadatas.append(metadata)
    
    # 벡터 DB 생성
    print("⚙️  벡터 DB 생성 중... (30초~1분 소요)")
    db = Chroma.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    
    print(f"✅ 벡터 DB 저장 완료: {DB_PATH}")
    print(f"   - 임베딩 모델: {EMBEDDING_MODEL}")
    print(f"   - 정책 수: {len(policies)}개")
    
    return db


def load_vector_db() -> Chroma:
    """저장된 벡터 DB 로드
    
    Returns:
        Chroma 벡터 DB 객체
        
    Raises:
        FileNotFoundError: 벡터 DB가 없는 경우
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"❌ 벡터 DB가 없습니다: {DB_PATH}\n"
            f"   먼저 create_vector_db()를 실행하세요."
        )
    
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    db = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
    )
    
    return db


def search_policies(
    query: str, 
    age: Optional[int] = None, 
    income_code: Optional[str] = None,
    region: Optional[str] = None,
    include_expired: bool = False, 
    k: int = 5,
    verbose: bool = False
) -> List[Any]:
    """정책 검색 (의미 기반 + 필터링)
    
    Args:
        query: 검색 쿼리 (자연어)
        age: 사용자 나이 (필터링용)
        income_code: 소득 조건 코드 (예: "0043001")
        region: 지역 (예: "서울시")
        include_expired: True면 마감된 정책도 포함
        k: 반환할 결과 개수
        verbose: True면 디버깅 정보 출력
        
    Returns:
        검색 결과 리스트 (LangChain Document 객체)
        
    Example:
        >>> results = search_policies("월세 지원", age=27, k=5)
        >>> for r in results:
        ...     print(r.metadata['plcyNm'])
    """
    db = load_vector_db()
    
    # 필터 조건 설정
    conditions = []
    
    if age is not None:
        conditions.append({"minAge": {"$lte": age}})
        conditions.append({"maxAge": {"$gte": age}})
    
    if income_code:
        conditions.append({"earnCndSeCd": {"$eq": income_code}})
    
    if region:
        conditions.append({"region": {"$eq": region}})
    
    # 필터 조합
    where_filter = None
    if conditions:
        where_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    if verbose and where_filter:
        print(f"🔍 필터: {where_filter}")
    
    # 의미 기반 검색 (여유분 포함)
    results = db.similarity_search(
        query, 
        k=k * SEARCH_BUFFER_MULTIPLIER, 
        filter=where_filter
    )
    
    if verbose:
        print(f"📊 필터링 전 결과: {len(results)}개")
    
    # 마감일 필터링
    if not include_expired:
        filtered_results = [
            r for r in results 
            if is_policy_active(r.metadata.get('aplyYmd', ''))
        ]
        results = filtered_results[:k]
    else:
        results = results[:k]
    
    if verbose:
        print(f"📊 최종 결과: {len(results)}개")
    
    # 결과 없으면 경고
    if len(results) == 0:
        print(f"\n⚠️  검색 결과 없음")
        print(f"   📝 쿼리: '{query}'")
        if age:
            print(f"   👤 나이: {age}세")
        if income_code:
            print(f"   💰 소득조건: {income_code}")
        if region:
            print(f"   📍 지역: {region}")
        print(f"   💡 힌트: 조건을 완화하거나 다른 키워드로 검색해보세요\n")
    
    return results


def search_policies_by_income_level(
    query: str,
    age: Optional[int] = None,
    income_level: str = "무관",
    **kwargs
) -> List[Any]:
    """소득 수준 이름으로 정책 검색 (편의 함수)
    
    Args:
        query: 검색 쿼리
        age: 사용자 나이
        income_level: 소득 수준 ("무관", "중위50이하", "중위100이하" 등)
        **kwargs: search_policies()의 다른 인자들
        
    Returns:
        검색 결과 리스트
        
    Example:
        >>> results = search_policies_by_income_level(
        ...     "취업 지원", 
        ...     age=25, 
        ...     income_level="무관"
        ... )
    """
    income_code = INCOME_CODES.get(income_level)
    
    if income_code is None:
        print(f"⚠️  알 수 없는 소득 수준: '{income_level}'")
        print(f"   사용 가능: {list(INCOME_CODES.keys())}")
        income_code = INCOME_CODES["무관"]  # 기본값
    
    return search_policies(
        query=query,
        age=age,
        income_code=income_code,
        **kwargs
    )


def get_db_stats() -> Dict[str, Any]:
    """벡터 DB 통계 정보 반환
    
    Returns:
        통계 정보 dict
    """
    if not os.path.exists(DB_PATH):
        return {"exists": False}
    
    try:
        db = load_vector_db()
        collection = db._collection
        
        return {
            "exists": True,
            "path": DB_PATH,
            "count": collection.count(),
            "embedding_model": EMBEDDING_MODEL,
        }
    except Exception as e:
        return {
            "exists": True,
            "path": DB_PATH,
            "error": str(e)
        }


# ============================================================================
# 테스트 / 실행
# ============================================================================

def run_tests():
    """기본 테스트 실행"""
    print("\n" + "="*60)
    print("벡터 DB 테스트")
    print("="*60)
    
    # 벡터 DB 없으면 생성
    if not os.path.exists(DB_PATH):
        print("\n[1] 벡터 DB 생성")
        create_vector_db()
    else:
        print("\n[1] 기존 벡터 DB 사용")
        stats = get_db_stats()
        print(f"    - 경로: {stats['path']}")
        print(f"    - 정책 수: {stats.get('count', 'N/A')}개")
    
    print("\n" + "-"*60)
    print("[2] 검색 테스트")
    print("-"*60)
    
    # 테스트 1: 월세 지원
    print("\n🔍 테스트 1: '월세 지원' (27세)")
    results = search_policies("월세 지원", age=27, k=3, verbose=True)
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r.metadata['plcyNm']}")
        print(f"      마감: {r.metadata.get('aplyYmd', '상시')}")
    
    # 테스트 2: 취업 지원
    print("\n🔍 테스트 2: '취업 지원' (25세, 소득무관)")
    results = search_policies_by_income_level(
        "취업 지원", 
        age=25, 
        income_level="무관",
        k=3
    )
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r.metadata['plcyNm']}")
    
    # 테스트 3: 조건 까다로운 검색
    print("\n🔍 테스트 3: '창업 지원' (50세) - 결과 없을 것으로 예상")
    results = search_policies("창업 지원", age=50, k=3)
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")


def get_db_stats_lightweight() -> Dict[str, Any]:
    """벡터 DB 통계 (OpenAI 키 불필요 — chromadb 직접 접근)"""
    if not os.path.exists(DB_PATH):
        return {"exists": False, "path": DB_PATH}

    import chromadb
    client = chromadb.PersistentClient(path=DB_PATH)
    collections = client.list_collections()
    stats = {
        "exists": True,
        "path": DB_PATH,
        "collections": {},
    }
    for col in collections:
        stats["collections"][col.name] = col.count()
    return stats


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="ChromaDB 벡터 DB 관리 CLI")
    parser.add_argument('--reindex', action='store_true', help='기존 DB 삭제 후 재생성 (OpenAI 키 필요)')
    parser.add_argument('--stats', action='store_true', help='현재 DB 통계 출력 (OpenAI 키 불필요)')
    args = parser.parse_args()

    if args.stats:
        stats = get_db_stats_lightweight()
        if not stats["exists"]:
            print(f"벡터 DB 없음: {stats['path']}")
        else:
            print(f"벡터 DB 경로: {stats['path']}")
            for name, count in stats["collections"].items():
                print(f"  컬렉션 '{name}': {count}건")
    elif args.reindex:
        print("=== ChromaDB 재인덱싱 시작 ===")
        before = get_db_stats_lightweight()
        before_count = sum(before.get("collections", {}).values())
        print(f"변경 전: {before_count}건")

        start = time.time()
        create_vector_db(force_recreate=True)
        elapsed = time.time() - start

        after = get_db_stats_lightweight()
        after_count = sum(after.get("collections", {}).values())
        print(f"변경 후: {after_count}건 ({elapsed:.1f}초 소요)")
    else:
        run_tests()
