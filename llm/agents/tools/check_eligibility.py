"""
자격 판정 도구

검색된 정책 리스트와 사용자 정보를 받아 룰베이스로 자격을 판정한다.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from langchain_core.tools import BaseTool, tool

# 소득 코드 상수 (backend/policies/services/matching_keys.py와 동일 값 유지)
INCOME_ANY = "0043001"
INCOME_ANNUAL = "0043002"
INCOME_ETC = "0043003"

# 청년 정책 만 나이 경계 (만 나이 vs 세는 나이 차이로 1살이 자격을 결정할 수 있음)
YOUTH_AGE_MIN_BOUNDARY = 19
YOUTH_AGE_MAX_BOUNDARY = 39

SEOUL_WIDE_DISTRICTS = {"서울", "서울시", "서울특별시"}
logger = logging.getLogger(__name__)


PolicyFetcher = Callable[[Optional[list[str]]], list[dict]]

NEED_CANONICAL_MAP = {
    "일자리": "취업",
    "취업": "취업",
    "구직": "취업",
    "창업": "창업",
    "주거": "주거",
    "금융": "금융",
    "교육": "교육",
    "문화": "문화",
    "복지문화": "문화",
    "건강": "건강",
}

NEED_KEYWORDS = {
    "취업": ("취업", "일자리", "구직", "채용", "인턴", "면접", "고용"),
    "창업": ("창업", "스타트업", "사업", "소상공", "창직"),
    "주거": ("주거", "월세", "전세", "임대", "보증금", "주택", "원룸", "고시원"),
    "금융": ("금융", "대출", "저축", "자금", "신용", "융자", "이자"),
    "교육": ("교육", "학습", "훈련", "자격증", "강의", "학비", "학교"),
    "문화": ("문화", "예술", "공연", "전시", "여가", "관람", "체육"),
    "건강": ("건강", "의료", "병원", "심리", "상담", "치료", "검진"),
}


def _safe_int(value: Any) -> int | None:
    """LLM JSON에서 숫자가 문자열로 올 수 있으므로 방어적으로 정수 변환한다."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    return None


def _normalize_text(value: Any) -> str:
    """문자열 비교 전에 입력을 정규화한다. 비문자열은 fail-open으로 빈 문자열 처리."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _normalize_needs(value: Any) -> list[str]:
    """needs/interests 값을 표준 카테고리로 정규화한다."""
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        token = item.strip()
        if not token:
            continue
        canonical = NEED_CANONICAL_MAP.get(token, token)
        if canonical in NEED_KEYWORDS and canonical not in normalized:
            normalized.append(canonical)
    return normalized


def _policy_text(policy: dict[str, Any]) -> str:
    """needs 매칭용 텍스트를 구성한다."""
    parts: list[str] = []
    for key in ("category", "category_name", "title", "summary", "description", "support_content"):
        value = policy.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())

    tags = policy.get("tags")
    if isinstance(tags, list):
        parts.extend(str(tag).strip() for tag in tags if isinstance(tag, str) and tag.strip())

    return " ".join(parts).lower()


def _policy_matches_need(policy: dict[str, Any], needs: list[str]) -> bool:
    """정책이 needs 카테고리 중 하나와 매칭되는지 판단한다."""
    if not needs:
        return True
    text = _policy_text(policy)
    if not text:
        return False
    for need in needs:
        keywords = NEED_KEYWORDS.get(need, ())
        if any(keyword in text for keyword in keywords):
            return True
    return False


def _check_age(policy: dict[str, Any], user_age: int | None) -> dict[str, Any]:
    """나이 조건을 판정한다."""
    age_min = _safe_int(policy.get("age_min"))
    age_max = _safe_int(policy.get("age_max"))
    age_min = 0 if age_min is None else age_min
    age_max = 999 if age_max is None else age_max

    if user_age is None:
        return {"result": None, "message": "나이 정보 없음 (확인 필요)"}

    # 청년 경계 확인은 합의 스펙대로 19(하한), 39(상한)에만 적용한다.
    if user_age == YOUTH_AGE_MIN_BOUNDARY and age_min == YOUTH_AGE_MIN_BOUNDARY:
        return {
            "result": None,
            "message": f"경계 나이 확인 필요: 19세 (조건: {age_min}~{age_max}세)",
        }

    # 39세 경계는 상한(age_max=39)에서만 만 나이 확인 필요로 처리한다.
    if user_age == YOUTH_AGE_MAX_BOUNDARY and age_max == YOUTH_AGE_MAX_BOUNDARY:
        return {
            "result": None,
            "message": f"경계 나이 확인 필요: 39세 (조건: {age_min}~{age_max}세)",
        }

    if age_min <= user_age <= age_max:
        return {"result": True, "message": f"충족 ({age_min}~{age_max}세)"}

    return {
        "result": False,
        "message": f"나이 미충족: {user_age}세 (조건: {age_min}~{age_max}세)",
    }


def _check_income(policy: dict[str, Any], user_income: int | None) -> dict[str, Any]:
    """소득 조건을 판정한다."""
    income_level = _normalize_text(policy.get("income_level"))
    income_max = _safe_int(policy.get("income_max"))

    if not income_level or income_level in {INCOME_ANY, INCOME_ETC}:
        return {"result": True, "message": "소득 조건 무관/기타 (통과)"}

    if income_level != INCOME_ANNUAL:
        # 여기 도달 시 INCOME_ANY, INCOME_ETC 이미 제외됨
        return {"result": True, "message": f"알 수 없는 소득 코드({income_level})로 통과"}

    if income_max is None:
        return {"result": True, "message": "소득 상한 정보 없음 (통과)"}
    if income_max < 0:
        logger.warning(
            "income_max is negative. policy_id=%s income_max=%s",
            policy.get("policy_id", ""),
            income_max,
        )
        return {"result": True, "message": "소득 상한 비정상값 (통과)"}
    if income_max == 0:
        # 운영 데이터에서 0은 상한 미기재 표현으로 간주하여 warning 없이 통과 처리한다.
        return {"result": True, "message": "소득 상한 정보 없음 (통과)"}

    if user_income is None:
        return {"result": None, "message": "소득 정보 없음 (확인 필요)"}

    if user_income <= income_max:
        return {
            "result": True,
            "message": f"소득 충족 (연 {user_income}만원 ≤ {income_max}만원)",
        }

    return {
        "result": False,
        "message": f"소득 미충족 (연 {user_income}만원 > {income_max}만원)",
    }


def _check_region(policy: dict[str, Any], user_residence: str) -> dict[str, Any]:
    """지역 조건을 판정한다."""
    policy_district = _normalize_text(policy.get("district"))

    if not policy_district:
        return {"result": True, "message": "지역 제한 없음 (통과)"}

    if not user_residence:
        return {"result": None, "message": "거주지 정보 없음 (확인 필요)"}

    if policy_district in SEOUL_WIDE_DISTRICTS:
        return {"result": True, "message": f"서울시 정책 ({user_residence} 거주)"}

    # FN_013 결정사항: 지역은 부분일치가 아닌 엄격 일치만 허용
    if user_residence == policy_district:
        return {"result": True, "message": f"지역 충족 ({policy_district})"}

    return {
        "result": False,
        "message": f"지역 미충족: {user_residence} (조건: {policy_district})",
    }


def _judge(details: dict[str, dict[str, Any]]) -> tuple[bool | None, list[str]]:
    """세부 조건 결과를 종합해 최종 적격 여부와 사유를 반환한다."""
    false_reasons = [
        detail["message"] for detail in details.values() if detail.get("result") is False
    ]
    if false_reasons:
        # False가 하나라도 있으면 부적격 확정. None(확인 필요) 사유는 함께 노출하지 않음.
        # 부적격 정책에 확인 필요 사유를 섞으면 UX 상 혼란을 줄 수 있다.
        return False, false_reasons

    none_reasons = [
        detail["message"] for detail in details.values() if detail.get("result") is None
    ]
    if none_reasons:
        return None, none_reasons

    return True, []


def create_check_eligibility(policy_fetcher: PolicyFetcher) -> BaseTool:
    """policy_fetcher를 주입받아 check_eligibility 도구를 생성한다."""

    @tool
    def check_eligibility(policies: str, user_info: str) -> str:
        """
        검색된 정책에 대해 사용자 자격요건을 룰베이스로 판정한다.

        Args:
            policies: search_policies 결과 JSON 문자열 또는 "all"/"all_policies"
            user_info: extract_info 결과 JSON 문자열 (사용자 정보 dict)

        Returns:
            판정 결과 JSON 문자열 (정책별 is_eligible + reasons + details)
        """
        try:
            info = json.loads(user_info)
        except (json.JSONDecodeError, TypeError) as exc:
            return json.dumps(
                {
                    "error": f"user_info 파싱 실패: {str(exc)}",
                    "policies_checked": 0,
                },
                ensure_ascii=False,
            )

        if not isinstance(info, dict):
            return json.dumps(
                {
                    "error": "user_info는 JSON 객체여야 합니다.",
                    "policies_checked": 0,
                },
                ensure_ascii=False,
            )

        is_all_mode = isinstance(policies, str) and policies.strip() in ("all", "all_policies")
        if is_all_mode:
            try:
                policies_list = policy_fetcher(None)
            except Exception as exc:
                return json.dumps(
                    {
                        "error": f"policy fetch 실패: {str(exc)}",
                        "policies_checked": 0,
                    },
                    ensure_ascii=False,
                )
        else:
            try:
                policies_list = json.loads(policies)
            except (json.JSONDecodeError, TypeError) as exc:
                return json.dumps(
                    {
                        "error": f"policies 파싱 실패: {str(exc)}",
                        "policies_checked": 0,
                    },
                    ensure_ascii=False,
                )

        if not isinstance(policies_list, list):
            return json.dumps(
                {
                    "error": "policies는 JSON 리스트여야 합니다.",
                    "policies_checked": 0,
                },
                ensure_ascii=False,
            )

        # NOTE: user_info는 호환 필드명을 허용한다.
        # - district (정식) / residence (하위호환)
        # - income_level (정식, 숫자형) / income (하위호환)
        user_age = _safe_int(info.get("age"))
        user_income = _safe_int(info.get("income_level"))
        if user_income is None:
            user_income = _safe_int(info.get("income"))

        user_residence = _normalize_text(info.get("district"))
        if not user_residence:
            user_residence = _normalize_text(info.get("residence"))

        user_needs = _normalize_needs(info.get("needs"))

        # matching(all) 경로에서 needs가 있으면 정책 후보를 먼저 좁힌다.
        if is_all_mode and user_needs:
            policies_list = [
                policy
                for policy in policies_list
                if isinstance(policy, dict) and _policy_matches_need(policy, user_needs)
            ]

        results: list[dict[str, Any]] = []
        for idx, policy_item in enumerate(policies_list):
            if not isinstance(policy_item, dict):
                logger.warning(
                    "invalid policy item skipped. index=%s item_type=%s",
                    idx,
                    type(policy_item).__name__,
                )
                continue
            policy = policy_item

            details = {
                "age": _check_age(policy, user_age),
                "income": _check_income(policy, user_income),
                "region": _check_region(policy, user_residence),
            }
            is_eligible, reasons = _judge(details)

            results.append(
                {
                    "policy_id": policy.get("policy_id", ""),
                    "title": policy.get("title", ""),
                    "apply_url": policy.get("apply_url", ""),
                    "is_eligible": is_eligible,
                    "reasons": reasons,
                    "details": details,
                }
            )

        return json.dumps(results, ensure_ascii=False)

    return check_eligibility
