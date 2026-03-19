"""
정책 데이터 변환 유틸리티

vector_store.py와 bm25_retriever.py에서 공통으로 사용하는 함수 모음
"""

from typing import Any, Dict


def _parse_age(raw, *, default: int, zero_means: int) -> int:
    """API age 필드 파싱.

    회의 결정(1/19) 기준:
    - None/빈 값 → default (서울시 청년 기준 19~39)
    - '0' → zero_means (연령무관: min=0, max=99)
    - 유효한 숫자 → 그대로 사용
    """
    if raw is None or raw == '':
        return default
    if str(raw) == '0':
        return zero_means
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def create_policy_text(policy: dict) -> str:
    """정책 데이터를 검색 최적화된 텍스트로 변환

    Args:
        policy: 정책 데이터 dict

    Returns:
        검색용 텍스트 문자열
    """
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


def extract_metadata(policy: dict) -> Dict[str, Any]:
    """정책 데이터에서 메타데이터 추출

    Args:
        policy: 정책 원본 데이터

    Returns:
        메타데이터 dict
    """
    return {
        "plcyNo": policy.get('plcyNo', ''),
        "plcyNm": policy.get('plcyNm', ''),
        "minAge": _parse_age(policy.get('sprtTrgtMinAge'), default=19, zero_means=0),
        "maxAge": _parse_age(policy.get('sprtTrgtMaxAge'), default=39, zero_means=99),
        "region": policy.get('rgtrHghrkInstCdNm', ''),
        "earnCndSeCd": policy.get('earnCndSeCd', ''),
        "earnMaxAmt": policy.get('earnMaxAmt'),
        "lclsfNm": policy.get('lclsfNm', ''),
        "mclsfNm": policy.get('mclsfNm', ''),
        "aplyYmd": policy.get('aplyYmd', ''),
        "aplyUrlAddr": policy.get('aplyUrlAddr', ''),
        "plcySprtCn": policy.get('plcySprtCn', '')[:200] if policy.get('plcySprtCn') else '',
    }
