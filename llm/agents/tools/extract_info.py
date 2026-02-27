"""
정보 추출 도구

사용자 발화에서 프로필 정보를 추출합니다. (LLM + deterministic 후처리)
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, TypedDict, cast

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from llm.agents.prompts.extract_info import (
    EXTRACT_INFO_SYSTEM_PROMPT,
    EXTRACT_INFO_SYSTEM_PROMPT_SHORT,
)

try:
    from langfuse.decorators import observe
except ImportError:
    def observe(*_args, **_kwargs):  # type: ignore[override]
        """Langfuse 미설치 환경용 no-op 데코레이터."""
        def _decorator(func):
            return func
        return _decorator


# ============================================================================
# 설정
# ============================================================================

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.0

logger = logging.getLogger(__name__)

# import 시점에 1회만 평가되며, 런타임 중 환경변수를 재조회하지 않습니다.
DEBUG_EXTRACT_INFO_RAW = os.getenv("DEBUG_EXTRACT_INFO_RAW", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


# ============================================================================
# 타입 정의
# ============================================================================

class ExtractResult(TypedDict):
    """extract_info 표준 출력 타입."""

    age: int | None
    residence: str | None
    employment_status: str | None
    income: int | None
    income_raw: str | None
    household_size: int | None
    housing_type: str | None
    interests: list[str] | None
    special_conditions: list[str] | None


# ============================================================================
# 정규화 테이블
# ============================================================================

SEOUL_DISTRICTS = {
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
}

DISTRICT_ROOT_TO_FULL = {district[:-1]: district for district in SEOUL_DISTRICTS}

DONG_TO_GU = {
    "강남": "강남구",
    "역삼": "강남구",
    "삼성": "강남구",
    "청담": "강남구",
    "압구정": "강남구",
    "논현": "강남구",
    "대치": "강남구",
    "도곡": "강남구",
    "개포": "강남구",
    "신사": "강남구",
    "강동": "강동구",
    "천호": "강동구",
    "암사": "강동구",
    "명일": "강동구",
    "고덕": "강동구",
    "둔촌": "강동구",
    "강북": "강북구",
    "미아": "강북구",
    "수유": "강북구",
    "우이": "강북구",
    "강서": "강서구",
    "화곡": "강서구",
    "가양": "강서구",
    "마곡": "강서구",
    "발산": "강서구",
    "등촌": "강서구",
    "염창": "강서구",
    "방화": "강서구",
    "관악": "관악구",
    "신림": "관악구",
    "봉천": "관악구",
    "서울대": "관악구",
    "서울대입구": "관악구",
    "낙성대": "관악구",
    "광진": "광진구",
    "건대": "광진구",
    "건국대": "광진구",
    "구의": "광진구",
    "자양": "광진구",
    "중곡": "광진구",
    "구로": "구로구",
    "가산": "구로구",
    "구디": "구로구",
    "신도림": "구로구",
    "오류": "구로구",
    "개봉": "구로구",
    "고척": "구로구",
    "금천": "금천구",
    "독산": "금천구",
    "시흥": "금천구",
    "노원": "노원구",
    "상계": "노원구",
    "중계": "노원구",
    "공릉": "노원구",
    "하계": "노원구",
    "도봉": "도봉구",
    "쌍문": "도봉구",
    "방학": "도봉구",
    "창동": "도봉구",
    "동대문": "동대문구",
    "회기": "동대문구",
    "휘경": "동대문구",
    "이문": "동대문구",
    "장안": "동대문구",
    "답십리": "동대문구",
    "청량리": "동대문구",
    "동작": "동작구",
    "노량진": "동작구",
    "사당": "동작구",
    "대방": "동작구",
    "신대방": "동작구",
    "흑석": "동작구",
    "마포": "마포구",
    "홍대": "마포구",
    "홍대입구": "마포구",
    "합정": "마포구",
    "연남": "마포구",
    "상수": "마포구",
    "망원": "마포구",
    "공덕": "마포구",
    "아현": "마포구",
    "서교": "마포구",
    "서대문": "서대문구",
    "신촌": "서대문구",
    "이대": "서대문구",
    "연희": "서대문구",
    "홍제": "서대문구",
    "북아현": "서대문구",
    "서초": "서초구",
    "반포": "서초구",
    "잠원": "서초구",
    "방배": "서초구",
    "양재": "서초구",
    "서래마을": "서초구",
    "성동": "성동구",
    "성수": "성동구",
    "성수동": "성동구",
    "왕십리": "성동구",
    "금호": "성동구",
    "옥수": "성동구",
    "행당": "성동구",
    "성북": "성북구",
    "안암": "성북구",
    "길음": "성북구",
    "정릉": "성북구",
    "석관": "성북구",
    "성신여대": "성북구",
    "송파": "송파구",
    "잠실": "송파구",
    "석촌": "송파구",
    "문정": "송파구",
    "가락": "송파구",
    "오금": "송파구",
    "방이": "송파구",
    "신천": "송파구",
    "양천": "양천구",
    "목동": "양천구",
    "신정": "양천구",
    "신월": "양천구",
    "영등포": "영등포구",
    "여의도": "영등포구",
    "당산": "영등포구",
    "문래": "영등포구",
    "신길": "영등포구",
    "대림": "영등포구",
    "용산": "용산구",
    "이태원": "용산구",
    "한남": "용산구",
    "후암": "용산구",
    "남영": "용산구",
    "효창": "용산구",
    "삼각지": "용산구",
    "은평": "은평구",
    "불광": "은평구",
    "연신내": "은평구",
    "구파발": "은평구",
    "응암": "은평구",
    "녹번": "은평구",
    "종로": "종로구",
    "대학로": "종로구",
    "혜화": "종로구",
    "광화문": "종로구",
    "종각": "종로구",
    "인사동": "종로구",
    "삼청동": "종로구",
    "부암동": "종로구",
    "중구": "중구",
    "명동": "중구",
    "을지로": "중구",
    "충무로": "중구",
    "동대문역사문화공원": "중구",
    "중랑": "중랑구",
    "상봉": "중랑구",
    "면목": "중랑구",
    "망우": "중랑구",
    "신내": "중랑구",
}

VALID_EMPLOYMENT = {"재직", "자영업", "무직", "구직중", "학생", "창업준비", "프리랜서"}
EMPLOYMENT_NORMALIZE = {
    "직장인": "재직",
    "회사원": "재직",
    "재직중": "재직",
    "재직": "재직",
    "회사다님": "재직",
    "근무중": "재직",
    "취준생": "구직중",
    "취업준비": "구직중",
    "취업준비중": "구직중",
    "구직자": "구직중",
    "대학생": "학생",
    "대학원생": "학생",
    "휴학생": "학생",
    "학생": "학생",
    "백수": "무직",
    "실업": "무직",
    "알바": "프리랜서",
    "아르바이트": "프리랜서",
    "계약직": "프리랜서",
    "프리랜서": "프리랜서",
    "자영업": "자영업",
    "소상공인": "자영업",
    "가게운영": "자영업",
    "창업준비": "창업준비",
    "창업중": "창업준비",
    "사업준비": "창업준비",
}

# 보건복지부 연도별 기준중위소득(월, 원) - 1~7인 가구
# 매년 1월 보건복지부 고시 기준 수동 갱신 필요
# backend matching 기준표와 동일한 값을 유지해야 운영 정합성이 보장됩니다.
MEDIAN_INCOME_WON_BY_YEAR: dict[int, dict[int, int]] = {
    2021: {
        1: 1827831,
        2: 3088079,
        3: 3983950,
        4: 4876290,
        5: 5757373,
        6: 6628603,
        7: 7497198,
    },
    2022: {
        1: 1944812,
        2: 3260085,
        3: 4194701,
        4: 5121080,
        5: 6024515,
        6: 6907004,
        7: 7780592,
    },
    2023: {
        1: 2077892,
        2: 3456155,
        3: 4434816,
        4: 5400964,
        5: 6330688,
        6: 7227981,
        7: 8107515,
    },
    2024: {
        1: 2228445,
        2: 3682609,
        3: 4714657,
        4: 5729913,
        5: 6695735,
        6: 7618369,
        7: 8514994,
    },
    2025: {
        1: 2392013,
        2: 3932658,
        3: 5025353,
        4: 6097773,
        5: 7108192,
        6: 8064805,
        7: 8988428,
    },
    2026: {
        1: 2564238,
        2: 4199292,
        3: 5367880,
        4: 6509816,
        5: 7571462,
        6: 8555952,
        7: 9515150,
    },
}

DEFAULT_MEDIAN_REFERENCE_YEAR = 2026
DEFAULT_HOUSEHOLD_SIZE = 1

VALID_INTERESTS = {"일자리", "주거", "교육", "복지문화", "참여권리", "기타"}
INTEREST_KEYWORDS = {
    "일자리": {
        "취업",
        "구직",
        "취준",
        "면접",
        "이력서",
        "일자리",
        "채용",
        "인턴",
        "창업",
        "사업",
        "자영업",
        "소상공",
        "가게",
        "스타트업",
    },
    "주거": {"주거", "월세", "전세", "임대", "보증금", "이사", "집", "방"},
    "교육": {"교육", "학습", "학비", "훈련", "자격증", "학교", "대학", "강의"},
    "복지문화": {"문화", "예술", "여가", "공연", "전시", "창작", "건강", "의료", "심리", "정신건강", "상담", "마음"},
    "기타": {"금융", "대출", "저축", "자산", "통장", "돈", "생활비"},
}

VALID_SPECIAL_CONDITIONS = {"신혼", "한부모", "장애", "다자녀", "저소득", "차상위", "기초수급", "중소기업", "군인"}
SPECIAL_CONDITION_NORMALIZE = {
    "장애인": "장애",
    "기초수급자": "기초수급",
    "수급자": "기초수급",
}

VALID_HOUSING_TYPES = {"전세", "월세", "자가"}
HOUSING_NORMALIZE = {
    "월세": "월세",
    "원룸": "월세",
    "고시원": "월세",
    "전세": "전세",
    "자가": "자가",
    "내집": "자가",
    "자기집": "자가",
}


# ============================================================================
# 내부 함수
# ============================================================================

def _empty_result() -> ExtractResult:
    """빈 결과를 반환합니다."""

    return {
        "age": None,
        "residence": None,
        "employment_status": None,
        "income": None,
        "income_raw": None,
        "household_size": None,
        "housing_type": None,
        "interests": [],
        "special_conditions": [],
    }


def _debug_dump_raw(stage: str, payload: Any) -> None:
    """raw 디버그 모드에서 단계별 데이터를 출력합니다."""

    if not DEBUG_EXTRACT_INFO_RAW:
        return

    print(f"[RAW] {stage}")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    else:
        print(str(payload))


def _debug_dump_post_diff(before: ExtractResult, after: ExtractResult) -> None:
    """후처리 전후 변경된 필드만 출력합니다."""

    if not DEBUG_EXTRACT_INFO_RAW:
        return

    diff: dict[str, dict[str, Any]] = {}
    for key in before.keys():
        before_value = before.get(key)
        after_value = after.get(key)
        if before_value != after_value:
            diff[key] = {"before": before_value, "after": after_value}

    print("[RAW] POST_DIFF")
    if not diff:
        print("(no changes)")
        return
    print(json.dumps(diff, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def _get_llm(model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> ChatOpenAI:
    """LLM 인스턴스를 반환합니다."""

    return ChatOpenAI(model=model, temperature=temperature)


@observe(name="extract_info_llm")
def _extract_with_llm(
    message: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    use_short_prompt: bool = False,
) -> str:
    """
    LLM을 사용하여 사용자 정보를 추출합니다.

    Args:
        message: 사용자 발화
        model: LLM 모델명
        temperature: LLM 온도
        use_short_prompt: 토큰 절약용 축약 프롬프트 사용 여부
            (운영 미사용, 평가/비교 실험용)

    Returns:
        LLM 원시 응답 문자열
    """

    llm = _get_llm(model=model, temperature=temperature)
    system_prompt = (
        EXTRACT_INFO_SYSTEM_PROMPT_SHORT if use_short_prompt else EXTRACT_INFO_SYSTEM_PROMPT
    )

    response = llm.invoke(
        [
            ("system", system_prompt),
            ("user", message),
        ]
    )

    content = response.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                part_text = str(part.get("text", "")).strip()
                if part_text:
                    text_parts.append(part_text)
            else:
                part_text = str(part).strip()
                if part_text:
                    text_parts.append(part_text)
        return " ".join(text_parts).strip()
    return str(content).strip()


def _strip_code_fence(text: str) -> str:
    """응답에 포함된 markdown 코드 블록을 제거합니다."""

    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
        return value.strip()

    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    return value


def _parse_json_response(raw_response: str) -> ExtractResult:
    """
    LLM 원시 응답을 JSON으로 파싱합니다.

    Args:
        raw_response: LLM 원시 응답

    Returns:
        파싱된 결과. 실패 시 빈 결과.
    """

    if not raw_response or not raw_response.strip():
        return _empty_result()

    try:
        text = _strip_code_fence(raw_response)
        payload = json.loads(text)
        if not isinstance(payload, dict):
            return _empty_result()

        result = _empty_result()

        raw_age = payload.get("age")
        result["age"] = raw_age if isinstance(raw_age, int) and not isinstance(raw_age, bool) else None

        raw_residence = payload.get("residence")
        result["residence"] = raw_residence if isinstance(raw_residence, str) else None

        result["employment_status"] = cast(str | None, payload.get("employment_status"))
        result["income"] = cast(int | None, payload.get("income"))
        result["income_raw"] = cast(str | None, payload.get("income_raw"))
        result["household_size"] = cast(int | None, payload.get("household_size"))
        result["housing_type"] = cast(str | None, payload.get("housing_type"))

        raw_interests = payload.get("interests") if "interests" in payload else None
        if raw_interests is None:
            result["interests"] = None
        else:
            result["interests"] = raw_interests if isinstance(raw_interests, list) else []

        raw_conditions = payload.get("special_conditions") if "special_conditions" in payload else None
        if raw_conditions is None:
            result["special_conditions"] = None
        else:
            result["special_conditions"] = raw_conditions if isinstance(raw_conditions, list) else []
        return result

    except (json.JSONDecodeError, TypeError, ValueError):
        return _empty_result()


def _normalize_age(value: Any) -> int | None:
    """age 값을 정규화합니다."""
    # TODO: [BRAIN4-check_eligibility] 경계선 나이(19, 39세) 확인 로직은
    #       check_eligibility에서 "확인필요" 판정으로 처리 예정.
    #       extract_info는 추출만 담당, 확인 질문은 오케스트레이터 책임.

    candidate: int | None = None

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        candidate = value
    elif isinstance(value, float):
        if value.is_integer():
            candidate = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        # 명시적으로 "만"이 붙은 경우는 만나이 그대로 사용
        explicit_man_age = re.search(r"(?:만\s*나이|만)\D*(-?\d{1,3})", text)
        if explicit_man_age:
            candidate = int(explicit_man_age.group(1))
        else:
            # "한국나이/세는나이/연나이"는 만나이로 1세 보정
            explicit_korean_age = re.search(
                r"(?:한국\s*나이|세는\s*나이|연\s*나이)\D*(-?\d{1,3})",
                text,
            )
            if explicit_korean_age:
                candidate = int(explicit_korean_age.group(1)) - 1
            else:
                year_match = re.search(r"(\d{2,4})\s*년생", text)
                if year_match:
                    birth_year = int(year_match.group(1))
                    current_year = datetime.now().year
                    if birth_year < 100:
                        pivot = current_year % 100
                        birth_year = 2000 + birth_year if birth_year <= pivot else 1900 + birth_year
                    # 정책: 생일 미경과를 가정한 보수 추정으로 1세 차감
                    candidate = current_year - birth_year - 1
                else:
                    age_match = re.search(r"-?\d{1,3}", text)
                    if age_match:
                        candidate = int(age_match.group(0))

    if candidate is None:
        return None
    if candidate < 0 or candidate >= 150:
        return None
    return candidate


def _normalize_location_token(text: str) -> str:
    """지역 토큰을 매핑 가능한 형태로 정리합니다."""

    cleaned = re.sub(r"\s+", "", text)
    cleaned = (
        cleaned.replace("서울특별시", "")
        .replace("서울시", "")
        .replace("서울", "")
        .replace("특별시", "")
    )
    cleaned = re.sub(r"(근처|주변|인근|쪽|부근)$", "", cleaned)
    cleaned = re.sub(r"(역|동)$", "", cleaned)
    return cleaned


def _normalize_residence(value: Any) -> str | None:
    """residence 값을 서울시 구 단위로 정규화합니다."""

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    def _resolve_compact_location(compact: str) -> str | None:
        if not compact:
            return None
        if compact in SEOUL_DISTRICTS:
            return compact
        if compact in DONG_TO_GU:
            return DONG_TO_GU[compact]
        if compact in DISTRICT_ROOT_TO_FULL:
            return DISTRICT_ROOT_TO_FULL[compact]

        for district in SEOUL_DISTRICTS:
            if district in compact:
                return district
        for dong in sorted(DONG_TO_GU.keys(), key=len, reverse=True):
            if dong in compact:
                return DONG_TO_GU[dong]

        candidate = f"{compact}구"
        if candidate in SEOUL_DISTRICTS:
            return candidate
        return None

    raw_compact = re.sub(r"\s+", "", text)
    resolved = _resolve_compact_location(raw_compact)
    if resolved:
        return resolved

    cleaned_compact = _normalize_location_token(text)
    resolved = _resolve_compact_location(cleaned_compact)
    if resolved:
        return resolved

    return None


def _normalize_employment(value: Any) -> str | None:
    """employment_status 값을 정규화합니다."""

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    if text in VALID_EMPLOYMENT:
        return text

    compact = re.sub(r"\s+", "", text)
    if compact in EMPLOYMENT_NORMALIZE:
        normalized = EMPLOYMENT_NORMALIZE[compact]
        return normalized if normalized in VALID_EMPLOYMENT else None

    if any(token in compact for token in ("취준", "취업준비", "구직")):
        return "구직중"
    if any(token in compact for token in ("직장", "회사", "재직")):
        return "재직"
    if any(token in compact for token in ("대학", "학생", "휴학")):
        return "학생"
    if any(token in compact for token in ("백수", "무직", "실업")):
        return "무직"
    if any(token in compact for token in ("프리랜서", "알바", "아르바이트", "계약직")):
        return "프리랜서"
    if any(token in compact for token in ("자영업", "소상공", "가게운영")):
        return "자영업"
    if any(token in compact for token in ("창업준비", "사업준비", "창업중")):
        return "창업준비"
    if "창업" in compact:
        return "창업준비"

    return None


def _resolve_reference_year(reference_year: int | None) -> int:
    """입력 연도를 기준표 내 유효 연도로 보정합니다."""

    available_years = sorted(MEDIAN_INCOME_WON_BY_YEAR.keys())
    if not available_years:
        return DEFAULT_MEDIAN_REFERENCE_YEAR
    if reference_year is None:
        return available_years[-1]
    if reference_year in MEDIAN_INCOME_WON_BY_YEAR:
        return reference_year
    if reference_year < available_years[0]:
        return available_years[0]
    if reference_year > available_years[-1]:
        return available_years[-1]

    # 중간 연도인 경우 가장 가까운 과거 연도 사용
    candidates = [year for year in available_years if year <= reference_year]
    return candidates[-1] if candidates else available_years[0]


def _resolve_household_size(household_size: int | None) -> int:
    """입력 가구원수를 기준표 내 유효 범위(1~7)로 보정합니다."""

    if household_size is None:
        return DEFAULT_HOUSEHOLD_SIZE
    return min(max(1, household_size), 7)


def _extract_monthly_income_manwon(
    text: str, *, assume_manwon_without_unit: bool = False
) -> float | None:
    """자연어에서 월소득을 추정해 만원 단위로 반환합니다."""

    if not text:
        return None

    source = text.replace(",", "")

    keyword = r"(?:월|달|한달|한\s*달|월급|급여|매달)"
    income_verb = r"(?:벌|받|받아|받고|수입|소득)"

    patterns: list[tuple[str, str]] = [
        (rf"{keyword}[^\d]{{0,8}}(\d+(?:\.\d+)?)\s*만원", "manwon"),
        (rf"{keyword}[^\d]{{0,8}}(\d+(?:\.\d+)?)\s*원", "won"),
        (rf"{keyword}[^\d]{{0,8}}(\d+(?:\.\d+)?)[^\n]{{0,8}}{income_verb}", "unknown"),
    ]

    for pattern, unit in patterns:
        match = re.search(pattern, source)
        if not match:
            continue

        amount = float(match.group(1))
        if unit == "manwon":
            return amount
        if unit == "won":
            return amount / 10000.0

        if assume_manwon_without_unit:
            return amount

        # 단위 미표기: 관용적으로 1000 이하면 만원 단위로 해석
        if amount <= 1000:
            return amount
        return amount / 10000.0

    return None


def _extract_annual_income_manwon(
    text: str, *, assume_manwon_without_unit: bool = False
) -> float | None:
    """자연어에서 연소득을 추정해 만원 단위로 반환합니다."""

    if not text:
        return None

    source = text.replace(",", "")
    keyword = r"(?:연봉|연소득|연수입|연\s*소득|연\s*수입)"

    patterns: list[tuple[str, str]] = [
        (rf"{keyword}[^\d]{{0,8}}(\d+(?:\.\d+)?)\s*만원", "manwon"),
        (rf"{keyword}[^\d]{{0,8}}(\d+(?:\.\d+)?)\s*원", "won"),
        (rf"{keyword}[^\d]{{0,8}}(\d+(?:\.\d+)?)", "unknown"),
    ]

    for pattern, unit in patterns:
        match = re.search(pattern, source)
        if not match:
            continue

        amount = float(match.group(1))
        if unit == "manwon":
            return amount
        if unit == "won":
            return amount / 10000.0

        if assume_manwon_without_unit:
            return amount

        # 단위 미표기: 일반적인 연봉 표기(3000, 4200)는 만원 단위로 해석
        if amount <= 10000:
            return amount
        return amount / 10000.0

    return None


def _extract_household_size(text: str) -> int | None:
    """문장에서 가구원수를 추정합니다."""

    if not text:
        return None

    compact = re.sub(r"\s+", "", text)

    for pattern in (
        r"([1-7])인가구",
        r"([1-7])인 가구",
        r"([1-7])명가구",
        r"([1-7])인 가족",
        r"([1-7])명 가족",
    ):
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))

    if any(token in compact for token in ("혼자", "자취", "독거", "싱글", "1인가구")):
        return 1
    if any(token in compact for token in ("부부", "신혼", "둘이", "2인가구")):
        return 2

    return None


def _extract_reference_year(text: str) -> int | None:
    """문장에서 기준 연도를 추정합니다."""

    if not text:
        return None

    match = re.search(r"(20\d{2})\s*년", text)
    if not match:
        return None
    return int(match.group(1))


def _extract_median_income_ratio(text: str) -> float | None:
    """중위소득 비율 표현(50/100/150%)을 추출합니다."""

    if not text:
        return None

    compact = re.sub(r"\s+", "", text).replace("중위소득", "중위")
    # TODO: 중위소득 비율 일반화 시
    # - "중위(소득)" 문맥 앵커 필수 유지
    # - 유효범위 가드(30~200%) + 노이즈 케이스 테스트 동반
    match = re.search(r"중위(?:\D{0,4})?(50|100|150)%?", compact)
    if not match:
        return None

    ratio_map = {"50": 0.5, "100": 1.0, "150": 1.5}
    return ratio_map.get(match.group(1))


def _annual_income_from_median_ratio(
    ratio: float,
    household_size: int | None = None,
    reference_year: int | None = None,
) -> int:
    """중위소득 비율을 연소득(만원)으로 환산합니다."""

    year = _resolve_reference_year(reference_year)
    size = _resolve_household_size(household_size)
    median_month_won = MEDIAN_INCOME_WON_BY_YEAR[year][size]
    annual_won = median_month_won * ratio * 12
    return int(round(annual_won / 10000.0))


def _normalize_income(
    income_raw: str | None,
    message: str | None = None,
    household_size: int | None = None,
) -> int | None:
    """income_raw/message에서 연소득(만원)을 추출합니다."""

    candidates: list[str] = []
    if isinstance(income_raw, str) and income_raw.strip():
        candidates.append(income_raw.strip())
    if isinstance(message, str) and message.strip():
        candidates.append(message.strip())

    if not candidates:
        return None

    inferred_household_size = household_size
    if inferred_household_size is None:
        for candidate in candidates:
            inferred_household_size = _extract_household_size(candidate)
            if inferred_household_size is not None:
                break

    inferred_year: int | None = None
    for candidate in candidates:
        inferred_year = _extract_reference_year(candidate)
        if inferred_year is not None:
            break

    for candidate in candidates:
        if re.search(r"(?:월|달|한달|한\s*달|월급|급여|매달)", candidate):
            monthly_income = _extract_monthly_income_manwon(
                candidate,
                assume_manwon_without_unit=True,
            )
            if monthly_income is not None and monthly_income >= 0:
                return int(round(monthly_income * 12))

    for candidate in candidates:
        if re.search(r"(?:연봉|연소득|연수입|연\s*소득|연\s*수입)", candidate):
            annual_income = _extract_annual_income_manwon(
                candidate,
                assume_manwon_without_unit=True,
            )
            if annual_income is not None and annual_income >= 0:
                return int(round(annual_income))

    for candidate in candidates:
        annual_income = _extract_annual_income_manwon(candidate)
        if annual_income is not None and annual_income >= 0:
            return int(round(annual_income))

    for candidate in candidates:
        monthly_income = _extract_monthly_income_manwon(candidate)
        if monthly_income is not None and monthly_income >= 0:
            return int(round(monthly_income * 12))

    for candidate in candidates:
        ratio = _extract_median_income_ratio(candidate)
        if ratio is not None:
            return _annual_income_from_median_ratio(
                ratio,
                household_size=inferred_household_size,
                reference_year=inferred_year,
            )

    return None


def _normalize_household_size_field(value: Any) -> int | None:
    """household_size 필드를 정수로 정규화합니다."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return min(max(value, 1), 20) if value > 0 else None
    if isinstance(value, float):
        if value.is_integer():
            return min(max(int(value), 1), 20) if value > 0 else None
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        numeric = re.search(r"\d{1,2}", text)
        if numeric:
            parsed = int(numeric.group(0))
            return min(max(parsed, 1), 20) if parsed > 0 else None
    return None


def _normalize_housing_type(value: Any) -> str | None:
    """housing_type 값을 정규화합니다."""

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    if text in VALID_HOUSING_TYPES:
        return text

    compact = re.sub(r"\s+", "", text)
    if compact in HOUSING_NORMALIZE:
        normalized = HOUSING_NORMALIZE[compact]
        return normalized if normalized in VALID_HOUSING_TYPES else None

    if any(token in compact for token in ("월세", "원룸", "고시원")):
        return "월세"
    if "전세" in compact:
        return "전세"
    if any(token in compact for token in ("자가", "내집", "자기집")):
        return "자가"
    return None


def _normalize_special_condition_token(value: str) -> str | None:
    """특수조건 토큰을 canonical 값으로 정규화합니다."""

    token = value.strip()
    if not token:
        return None
    if token in VALID_SPECIAL_CONDITIONS:
        return token

    compact = re.sub(r"\s+", "", token)
    if compact in SPECIAL_CONDITION_NORMALIZE:
        return SPECIAL_CONDITION_NORMALIZE[compact]

    if "장애" in compact:
        return "장애"
    if any(keyword in compact for keyword in ("기초수급", "수급자")):
        return "기초수급"
    if "한부모" in compact:
        return "한부모"
    if "신혼" in compact:
        return "신혼"
    if any(keyword in compact for keyword in ("저소득", "소득없", "소득없어")):
        return "저소득"
    if "다자녀" in compact:
        return "다자녀"
    if "차상위" in compact:
        return "차상위"
    if "중소기업" in compact:
        return "중소기업"
    if "군인" in compact:
        return "군인"
    return None


def _normalize_special_conditions(value: Any) -> list[str]:
    """special_conditions 값을 정규화합니다."""

    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        canonical = _normalize_special_condition_token(item)
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    return normalized


def _infer_special_conditions_from_message(message: str) -> list[str]:
    """메시지에서 특수조건을 보수적으로 추정합니다."""

    compact = re.sub(r"\s+", "", message)
    inferred: list[str] = []

    condition_patterns: list[tuple[str, tuple[str, ...]]] = [
        ("신혼", ("신혼",)),
        ("한부모", ("한부모",)),
        ("장애", ("장애인", "장애")),
        ("다자녀", ("다자녀",)),
        ("저소득", ("저소득", "소득없", "소득없어")),
        ("차상위", ("차상위",)),
        ("기초수급", ("기초수급", "기초수급자", "수급자")),
        ("중소기업", ("중소기업",)),
        ("군인", ("군인",)),
    ]

    for canonical, keywords in condition_patterns:
        if any(keyword in compact for keyword in keywords):
            inferred.append(canonical)

    return inferred


def _normalize_interest_token(value: str) -> str | None:
    """관심사 토큰을 허용 카테고리로 정규화합니다."""

    token = value.strip()
    if not token:
        return None
    if token in VALID_INTERESTS:
        return token

    compact = re.sub(r"\s+", "", token)
    for canonical, keywords in INTEREST_KEYWORDS.items():
        if compact in keywords or any(keyword in compact for keyword in keywords):
            return canonical
    return None


def _normalize_interests(value: Any) -> list[str]:
    """interests 값을 정규화합니다."""

    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        canonical = _normalize_interest_token(item)
        if canonical and canonical not in normalized:
            normalized.append(canonical)

    return normalized


def _infer_interests_from_message(message: str) -> list[str]:
    """메시지 텍스트에서 관심사를 보수적으로 추정합니다."""

    text = re.sub(r"\s+", "", message)
    inferred: list[str] = []
    for canonical, keywords in INTEREST_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            inferred.append(canonical)
    return inferred


def _post_process(result: ExtractResult, message: str | None = None) -> ExtractResult:
    """
    LLM 출력값을 deterministic하게 정규화합니다.

    Args:
        result: 파싱된 LLM 출력
        message: 원본 사용자 발화 (관심사 보완 추론에 사용)

    Returns:
        정규화된 ExtractResult
    """

    normalized = _empty_result()
    normalized["age"] = _normalize_age(result.get("age"))
    normalized["residence"] = _normalize_residence(result.get("residence"))
    normalized["employment_status"] = _normalize_employment(result.get("employment_status"))
    normalized["income_raw"] = (
        result.get("income_raw")
        if isinstance(result.get("income_raw"), str) and result.get("income_raw", "").strip()
        else None
    )
    normalized["housing_type"] = _normalize_housing_type(result.get("housing_type"))
    normalized["household_size"] = _normalize_household_size_field(result.get("household_size"))

    normalized["income"] = _normalize_income(
        normalized["income_raw"],
        message=message,
        household_size=normalized["household_size"],
    )

    # TODO: income이 None이고 employment_status가 "무직"인 경우,
    #       check_eligibility에서 소득 필터 스킵 처리 필요 (extract_info는 추출만)
    if normalized["household_size"] is None and isinstance(message, str) and message.strip():
        normalized["household_size"] = _extract_household_size(message)

    raw_interests = result.get("interests")
    interests = _normalize_interests(raw_interests)
    if raw_interests is None and isinstance(message, str) and message.strip():
        interests = _infer_interests_from_message(message)
    normalized["interests"] = interests

    raw_special_conditions = result.get("special_conditions")
    conditions = _normalize_special_conditions(raw_special_conditions)
    if raw_special_conditions is None and isinstance(message, str) and message.strip():
        conditions = _infer_special_conditions_from_message(message)
    normalized["special_conditions"] = conditions

    return normalized


# ============================================================================
# 도구 함수
# ============================================================================

def _is_empty_result(result: ExtractResult) -> bool:
    """결과가 완전히 비어있는지 확인합니다."""

    return (
        result.get("age") is None
        and result.get("residence") is None
        and result.get("employment_status") is None
        and result.get("income") is None
        and result.get("income_raw") is None
        and result.get("household_size") is None
        and result.get("housing_type") is None
        and not result.get("interests")
        and not result.get("special_conditions")
    )


def extract_info_full(
    message: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    use_short_prompt: bool = False,
) -> ExtractResult:
    """
    사용자 발화에서 프로필 정보를 추출하고 정규화 결과를 반환합니다.

    Args:
        message: 사용자 발화
        model: 사용할 LLM 모델
        temperature: LLM 온도
        use_short_prompt: 토큰 절약용 축약 프롬프트 사용 여부
            (운영 미사용, 평가/비교 실험용)

    Returns:
        정규화된 ExtractResult
    """

    if not message or len(message.strip()) < 2:
        _debug_dump_raw("SKIP_SHORT_MESSAGE", message)
        return _empty_result()

    try:
        raw_response = _extract_with_llm(
            message=message,
            model=model,
            temperature=temperature,
            use_short_prompt=use_short_prompt,
        )
        _debug_dump_raw("MESSAGE", message)
        _debug_dump_raw("LLM_RESPONSE", raw_response)

        parsed = _parse_json_response(raw_response)
        _debug_dump_raw("PARSED_BEFORE_POST", parsed)

        if _is_empty_result(parsed):
            _debug_dump_raw("RETURN_EMPTY_PARSED", _empty_result())
            return _empty_result()

        post_processed = _post_process(parsed, message=message)
        _debug_dump_raw("POST_PROCESSED", post_processed)
        _debug_dump_post_diff(parsed, post_processed)
        return post_processed
    except Exception:
        _debug_dump_raw("EXCEPTION_IN_EXTRACT_INFO_FULL", "See traceback in logger.")
        logger.exception("extract_info_full 실행 중 오류가 발생했습니다.")
        return _empty_result()


@tool
def extract_info(message: str) -> str:
    """
    사용자 발화에서 프로필 정보를 추출합니다.

    Args:
        message: 사용자 발화

    Returns:
        JSON 문자열 (ExtractResult 스키마)
    """

    if not message or len(message.strip()) < 2:
        return json.dumps(_empty_result(), ensure_ascii=False)

    try:
        result = extract_info_full(message)
        return json.dumps(result, ensure_ascii=False)
    except Exception:
        logger.exception("extract_info 도구 실행 중 오류가 발생했습니다.")
        return json.dumps(_empty_result(), ensure_ascii=False)


# ============================================================================
# 수동 테스트
# ============================================================================

if __name__ == "__main__":
    samples = [
        "27살 강남 사는 취준생인데 뭐 받을 수 있어?",
        "홍대 근처 사는데 월세 지원 있어?",
        "97년생 대학원생이고 성수동 살아",
        "그냥 뭐 있는지 궁금해서",
    ]

    for sample in samples:
        print(f"\n입력: {sample}")
        print(extract_info.invoke(sample))
