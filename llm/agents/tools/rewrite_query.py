"""
쿼리 리라이팅 도구

일상어를 검색에 최적화된 키워드로 변환 (LLM 기반)
"""

import json
import logging
import re
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from llm.agents.prompts.rewrite_query import REWRITE_QUERY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    """LLM 인스턴스를 반환합니다."""
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


def _rewrite_with_llm(query: str) -> str:
    """
    LLM을 사용하여 쿼리를 변환합니다.

    Args:
        query: 사용자 원본 질문

    Returns:
        LLM이 반환한 원시 응답 (JSON 문자열 또는 텍스트)
    """
    llm = _get_llm()

    messages = [
        ("system", REWRITE_QUERY_SYSTEM_PROMPT),
        ("user", query)
    ]

    response = llm.invoke(messages)
    return response.content.strip()


def _clean_fallback(text: str) -> str:
    """
    파싱 실패 시 텍스트를 정리합니다.

    JSON 문자, 따옴표, 개행 제거 및 공백 정리
    """
    # JSON 관련 문자 제거
    text = text.replace('{', '').replace('}', '').replace('[', '').replace(']', '')
    # 따옴표 제거
    text = text.replace('"', '').replace("'", '').replace('`', '')
    # 개행을 공백으로 변환
    text = text.replace('\n', ' ').replace('\r', ' ')
    # 여러 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _parse_json_response(raw_response: str, original_query: str) -> dict:
    """
    LLM 응답을 파싱하여 구조화된 딕셔너리로 반환합니다.

    Args:
        raw_response: LLM의 원시 응답
        original_query: 원본 사용자 쿼리

    Returns:
        {
            "bm25_query": str,
            "intent_keywords": list,
            "detected_pattern": str,
            "original_query": str
        }
    """
    try:
        # 코드 블록 제거 (```json ... ```)
        text = raw_response.strip()
        if text.startswith('```'):
            # 첫 번째와 마지막 줄 제거
            lines = text.split('\n')
            text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text

        # JSON 파싱
        data = json.loads(text)

        # 필드 검증 및 기본값 설정
        bm25_query = data.get("bm25_query", "").strip()
        intent_keywords = data.get("intent_keywords", [])
        detected_pattern = data.get("detected_pattern", "unknown")

        # bm25_query가 비어있으면 원본 사용
        if not bm25_query:
            bm25_query = original_query

        return {
            "bm25_query": bm25_query,
            "intent_keywords": intent_keywords,
            "detected_pattern": detected_pattern,
            "original_query": original_query
        }

    except (json.JSONDecodeError, KeyError, ValueError):
        # JSON 파싱 실패 시 텍스트 정리
        cleaned = _clean_fallback(raw_response)
        if not cleaned:
            cleaned = original_query

        return {
            "bm25_query": cleaned,
            "intent_keywords": [],
            "detected_pattern": "parse_error",
            "original_query": original_query
        }


def rewrite_query_full(query: str) -> dict:
    """
    사용자의 일상어 질문을 검색 키워드로 변환하고 전체 정보를 반환합니다.

    Args:
        query: 사용자 원본 질문

    Returns:
        {
            "bm25_query": 검색에 최적화된 키워드,
            "intent_keywords": 핵심 의도 키워드 리스트,
            "detected_pattern": 쿼리 패턴 분류,
            "original_query": 원본 쿼리
        }
    """
    # 빈 입력 처리
    if not query or len(query.strip()) < 2:
        return {
            "bm25_query": query,
            "intent_keywords": [],
            "detected_pattern": "empty",
            "original_query": query
        }

    try:
        raw_response = _rewrite_with_llm(query)
        return _parse_json_response(raw_response, query)

    except Exception:
        logger.exception("쿼리 변환 오류")
        return {
            "bm25_query": query,
            "intent_keywords": [],
            "detected_pattern": "error",
            "original_query": query
        }


def rewrite_query_internal(query: str) -> str:
    """
    검색 파이프라인에서 직접 호출하는 순수 함수형 리라이터.

    Args:
        query: 사용자 원본 질문

    Returns:
        검색에 최적화된 키워드 문자열
    """
    if not query or len(query.strip()) < 2:
        return query

    try:
        result = rewrite_query_full(query)
        return result["bm25_query"]
    except Exception:
        logger.exception("쿼리 변환 오류")
        return query


@tool
def rewrite_query(query: str) -> str:
    """
    사용자의 일상어 질문을 검색 키워드로 변환합니다.

    Args:
        query: 사용자 원본 질문

    Returns:
        검색에 최적화된 키워드 문자열

    Example:
        >>> rewrite_query("월세 도움 받을 수 있어?")
        "청년 월세 지원 주거 보조금"
    """
    return rewrite_query_internal(query)
