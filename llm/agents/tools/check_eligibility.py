"""
자격 판정 도구

검색된 정책 리스트와 사용자 정보를 받아 룰베이스로 자격을 판정한다.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
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


def _rank_eligible_policies(
    eligible: list[dict[str, Any]],
    user_info: dict[str, Any],
) -> list[dict[str, Any]]:
    """적격 정책 리스트를 룰베이스 점수로 정렬하여 반환한다."""
    if not eligible:
        return eligible

    raw_user_needs = user_info.get("needs")
    if isinstance(raw_user_needs, str):
        raw_user_needs = [raw_user_needs]
    user_needs = _normalize_needs(raw_user_needs)
    user_housing = _normalize_text(user_info.get("housing_type")).lower()
    user_employment = _normalize_text(user_info.get("employment_status")).lower()

    # extract_info canonical value 기준: {"재직", "자영업", "무직", "구직중", "학생", "창업준비", "프리랜서"}
    employment_keywords = {
        "구직중": ["취업", "구직", "취준", "일자리"],
        "재직": ["재직", "직장인", "근로"],
        "자영업": ["자영업", "소상공인", "가게"],
        "창업준비": ["창업", "사업", "스타트업"],
        "학생": ["대학", "학생", "학자금"],
        "무직": ["취업", "구직", "일자리"],
        "프리랜서": ["프리랜서", "계약직", "알바"],
    }
    core_keywords = ["지원", "혜택", "무료", "할인", "교육", "상담"]
    money_amount_keywords = ["만원", "백만", "천만", "억원"]
    money_support_keywords = ["지원금", "보조금", "장학금", "수당"]
    money_discount_keywords = ["감면", "할인", "무료"]

    for policy in eligible:
        ranking_context = policy.pop("_ranking_context", None)
        if not isinstance(ranking_context, dict):
            ranking_context = {}

        score = 0
        title = _normalize_text(policy.get("title") or ranking_context.get("title")).lower()
        description = _normalize_text(
            policy.get("description") or ranking_context.get("description")
        ).lower()
        support_content = _normalize_text(
            policy.get("support_content") or ranking_context.get("support_content")
        ).lower()
        category = _normalize_text(
            policy.get("category")
            or ranking_context.get("category")
            or policy.get("category_name")
            or ranking_context.get("category_name")
        ).lower()
        title_and_description = f"{title} {description}"

        if "청년" in title:
            score += 30

        if any(keyword in support_content for keyword in money_amount_keywords):
            score += 25
        elif any(keyword in support_content for keyword in money_support_keywords):
            score += 15
        elif any(keyword in support_content for keyword in money_discount_keywords):
            score += 5

        if category and any(need.lower() in category for need in user_needs):
            score += 20

        if any(need.lower() in title or need.lower() in description for need in user_needs if need):
            score += 10

        if user_housing in {"자가", "자가소유"} and any(
            keyword in title_and_description for keyword in ("월세", "전세", "임차")
        ):
            score -= 30
        elif user_housing in {"월세", "전세", "전월세"} and any(
            keyword in title_and_description for keyword in ("월세", "전세", "임차", "주거")
        ):
            score += 40

        if any(keyword in title for keyword in employment_keywords.get(user_employment, [])):
            score += 20

        if any(keyword in title for keyword in core_keywords):
            score += 10

        end_date_raw = policy.get("apply_end_date") or ranking_context.get("apply_end_date")
        end_date: date | None = None
        if isinstance(end_date_raw, datetime):
            end_date = end_date_raw.date()
        elif isinstance(end_date_raw, date):
            end_date = end_date_raw
        elif isinstance(end_date_raw, str):
            try:
                end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
            except ValueError:
                end_date = None

        if end_date is not None:
            days_left = (end_date - date.today()).days
            if 0 <= days_left <= 7:
                score += 20
            elif 7 < days_left <= 14:
                score += 10

        policy["_priority_score"] = score

    eligible.sort(key=lambda item: item.get("_priority_score", 0), reverse=True)
    return eligible


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

        # 필수 정보 게이팅: 나이·거주지·소득 중 2개 이상 없으면 매칭 실행 안 함
        _filled = sum(1 for k in ("age", "district", "income_level") if info.get(k) is not None)
        if _filled < 2:
            return json.dumps(
                {
                    "error": "사용자 정보 부족",
                    "message": "나이, 거주지, 소득 중 2개 이상이 필요합니다.",
                    "policies_checked": 0,
                    "guide": "나이 → 거주지 → 소득 순으로 추가 질문 후 다시 호출하세요.",
                },
                ensure_ascii=False,
            )

        is_all_mode = isinstance(policies, str) and policies.strip() in ("all", "all_policies")
        is_empty = policies is None or (isinstance(policies, list) and len(policies) == 0) or policies == ""
        if is_all_mode or is_empty:
            return json.dumps(
                {
                    "status": "error",
                    "error": "policies='all'은 지원하지 않습니다. search_policies로 먼저 검색 후 정책 ID 리스트를 전달하세요.",
                    "policies_checked": 0,
                    "guide": "search_policies(query=키워드) → check_eligibility(policies=검색결과JSON) 순서로 호출하세요.",
                },
                ensure_ascii=False,
            )

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

        eligible_results: list[dict[str, Any]] = []
        ineligible_results: list[dict[str, Any]] = []
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

            _apply_end_date = policy.get("apply_end_date")
            if isinstance(_apply_end_date, (date, datetime)):
                _apply_end_date = _apply_end_date.isoformat()[:10]
            elif not isinstance(_apply_end_date, str):
                _apply_end_date = None

            result = {
                "policy_id": policy.get("policy_id") or policy.get("plcy_no") or "",
                "title": policy.get("title") or policy.get("plcy_nm") or "",
                "is_eligible": is_eligible,
                "reasons": reasons,
                "details": details,
                # 응답 구조화(PolicyResult 조립)에 필요한 추가 필드
                "apply_url": policy.get("apply_url") or "",
                "detail_url": policy.get("detail_url") or "",
                "category": policy.get("category") or policy.get("category_name") or "",
                "summary": policy.get("support_content") or policy.get("description") or policy.get("summary") or "",
                "apply_end_date": _apply_end_date,
            }
            if is_eligible is True:
                result["_ranking_context"] = {
                    "title": policy.get("title", ""),
                    "description": policy.get("description", ""),
                    "support_content": policy.get("support_content", ""),
                    "category": policy.get("category", ""),
                    "category_name": policy.get("category_name", ""),
                    "apply_end_date": policy.get("apply_end_date"),
                }
                eligible_results.append(result)
            else:
                ineligible_results.append(result)

        ranked_eligible = _rank_eligible_policies(eligible_results, info)
        return json.dumps(ranked_eligible + ineligible_results, ensure_ascii=False)

    return check_eligibility
