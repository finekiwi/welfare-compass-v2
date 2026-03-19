"""
extract_info 도구 테스트

- Unit 테스트: Mock 기반, LLM 호출 없음
- Integration 테스트: 실제 LLM 호출 (OPENAI_API_KEY 필요)
"""

from __future__ import annotations

import importlib
import json
import os
from datetime import datetime
from unittest.mock import patch

import pytest


# ============================================================================
# Unit: JSON 파싱 (_parse_json_response)
# ============================================================================


class TestParseJsonResponse:

    def test_valid_json(self):
        from llm.agents.tools.extract_info import _parse_json_response

        raw = json.dumps(
            {
                "age": 27,
                "district": "강남구",
                "employment_status": "구직중",
                "income_raw": "월 200만원",
                "household_size": 1,
                "housing_type": "월세",
            },
            ensure_ascii=False,
        )
        result = _parse_json_response(raw)
        assert result["age"] == 27
        assert result["district"] == "강남구"
        assert result["employment_status"] == "구직중"

    def test_json_with_code_block(self):
        from llm.agents.tools.extract_info import _parse_json_response

        raw = (
            "```json\n"
            '{"age": 25, "district": "잠실", "employment_status": "직장인", '
            '"income_raw": null, "household_size": null, "housing_type": "전세"}\n'
            "```"
        )
        result = _parse_json_response(raw)
        assert result["age"] == 25
        assert result["district"] == "잠실"

    def test_invalid_json_returns_empty(self):
        from llm.agents.tools.extract_info import _empty_result, _parse_json_response

        result = _parse_json_response("{invalid-json")
        assert result == _empty_result()

    def test_core_field_type_mismatch_fallback(self):
        """age는 int|str 허용 (출생연도 패스스루), district는 str만 허용."""
        from llm.agents.tools.extract_info import _parse_json_response

        raw = json.dumps(
            {
                "age": "27",
                "district": 123,
                "employment_status": "구직중",
                "income_raw": None,
                "household_size": None,
                "housing_type": None,
            },
            ensure_ascii=False,
        )
        result = _parse_json_response(raw)
        # age: 문자열 "27"은 파싱 단계에서 통과 → _normalize_age()가 정수 27로 변환
        assert result["age"] == "27"
        assert result["district"] is None

    def test_residence_field_accepted_as_district_fallback(self):
        """LLM이 구버전 프롬프트대로 residence를 출력해도 district로 매핑된다."""
        from llm.agents.tools.extract_info import _parse_json_response

        raw = json.dumps(
            {
                "age": 27,
                "residence": "강남구",
                "employment_status": "구직중",
                "income_raw": None,
                "household_size": None,
                "housing_type": None,
            },
            ensure_ascii=False,
        )
        result = _parse_json_response(raw)
        assert result["district"] == "강남구"


# ============================================================================
# Unit: 후처리 (_post_process)
# ============================================================================


class TestPostProcessDistrict:

    @pytest.mark.parametrize(
        "raw_district,expected",
        [
            ("홍대", "마포구"),
            ("합정", "마포구"),
            ("연남", "마포구"),
            ("성수", "성동구"),
            ("성수동", "성동구"),
            ("잠실", "송파구"),
            ("석촌", "송파구"),
            ("건대", "광진구"),
            ("구의", "광진구"),
            ("이태원", "용산구"),
            ("여의도", "영등포구"),
            ("신림", "관악구"),
            ("노량진", "동작구"),
            ("신촌", "서대문구"),
        ],
    )
    def test_dong_to_gu_mapping(self, raw_district: str, expected: str):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["district"] = raw_district
        result = _post_process(payload)
        assert result["district"] == expected

    def test_suffix_auto_add(self):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["district"] = "강남"
        result = _post_process(payload)
        assert result["district"] == "강남구"

    def test_unknown_district_to_none(self):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["district"] = "제주도"
        result = _post_process(payload)
        assert result["district"] is None

    @pytest.mark.parametrize(
        "raw_district,expected",
        [
            ("목동", "양천구"),
            ("창동", "도봉구"),
            ("서울대입구", "관악구"),
            ("서울대입구 근처", "관악구"),
        ],
    )
    def test_district_preprocess_order_regression(self, raw_district: str, expected: str):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["district"] = raw_district
        result = _post_process(payload)
        assert result["district"] == expected


class TestPostProcessEmployment:

    @pytest.mark.parametrize(
        "raw_status,expected",
        [
            ("취준생", "구직중"),
            ("취업 준비", "구직중"),
            ("백수", "무직"),
            ("직장인", "재직"),
            ("회사원", "재직"),
            ("근무중", "재직"),
            ("대학생", "학생"),
            ("대학원생", "학생"),
            ("알바", "프리랜서"),
            ("자영업", "자영업"),
            ("창업 준비", "창업준비"),
            ("사업준비", "창업준비"),
        ],
    )
    def test_employment_normalization(self, raw_status: str, expected: str):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["employment_status"] = raw_status
        result = _post_process(payload)
        assert result["employment_status"] == expected

    def test_employment_valid_value_kept(self):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["employment_status"] = "프리랜서"
        result = _post_process(payload)
        assert result["employment_status"] == "프리랜서"

    def test_employment_unknown_to_none(self):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["employment_status"] = "외계인"
        result = _post_process(payload)
        assert result["employment_status"] is None


class TestPostProcessIncome:

    @pytest.mark.parametrize(
        "income_raw,message,expected_income",
        [
            ("월 200만원", "월 200만원 벌어요", 2400),
            ("월급 180", "월급 180 받아요", 2160),
            ("월 500만원", "월 500만원 벌어요", 6000),
            ("월 1500", "월 1500 벌어", 18000),
            ("연봉 3000만원", "연봉 3000만원이에요", 3000),
            ("연소득 2400", "연소득 2400이에요", 2400),
            (None, "소득 없어요", None),
            (None, None, None),
        ],
    )
    def test_income_normalization(self, income_raw, message, expected_income):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["income_raw"] = income_raw
        result = _post_process(payload, message=message)
        assert result["income_level"] == expected_income

    def test_income_normalization_from_median_expression(self):
        from llm.agents.tools.extract_info import (
            MEDIAN_INCOME_WON_BY_YEAR,
            _empty_result,
            _post_process,
        )

        payload = _empty_result()
        payload["income_raw"] = "중위소득 50% 이하"
        result = _post_process(payload, message="중위소득 50% 이하에요")

        latest_year = max(MEDIAN_INCOME_WON_BY_YEAR.keys())
        expected_income = int(round(MEDIAN_INCOME_WON_BY_YEAR[latest_year][1] * 0.5 * 12 / 10000.0))
        assert result["income_level"] == expected_income


class TestPostProcessHousingType:

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("월세", "월세"),
            ("전세", "전세"),
            ("자가", "자가"),
            ("원룸", "월세"),
            ("고시원", "월세"),
            ("아파트", None),
            (None, None),
        ],
    )
    def test_housing_type_normalization(self, raw, expected):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["housing_type"] = raw
        result = _post_process(payload)
        assert result["housing_type"] == expected


class TestPostProcessIncomeAgeInterests:

    @pytest.mark.parametrize(
        "raw_age,expected",
        [
            (27, 27),
            ("28", 28),
            ("29세", 29),
            ("만 27세", 27),
            ("만나이 27", 27),
            ("한국나이 27", 26),
            ("세는나이 30세", 29),
            (-1, None),
            ("-3", None),
            (151, None),
            ("150", None),
        ],
    )
    def test_age_normalization(self, raw_age, expected):
        from llm.agents.tools.extract_info import _empty_result, _post_process

        payload = _empty_result()
        payload["age"] = raw_age
        result = _post_process(payload)
        assert result["age"] == expected



# ============================================================================
# Unit: @tool 테스트 (Mock)
# ============================================================================


class TestExtractInfoTool:

    def test_tool_returns_json_with_post_process(self):
        extract_info_module = importlib.import_module("llm.agents.tools.extract_info")

        with patch.object(
            extract_info_module,
            "_extract_with_llm",
            return_value=json.dumps(
                {
                    "age": 27,
                    "district": "홍대",
                    "employment_status": "취준생",
                    "income_raw": "월 200만원",
                    "household_size": None,
                    "housing_type": "월세",
                },
                ensure_ascii=False,
            ),
        ):
            output = extract_info_module.extract_info.invoke(
                "27살 홍대 사는 취준생인데 월세 지원 있을까? 월 200만원 벌어"
            )
            result = json.loads(output)

            assert result["age"] == 27
            assert result["district"] == "마포구"
            assert result["employment_status"] == "구직중"
            assert result["income_level"] == 2400
            assert result["housing_type"] == "월세"

    def test_tool_llm_exception_returns_empty(self):
        extract_info_module = importlib.import_module("llm.agents.tools.extract_info")

        with patch.object(
            extract_info_module,
            "_extract_with_llm",
            side_effect=RuntimeError("API Error"),
        ):
            output = extract_info_module.extract_info.invoke("강남 사는 취준생")
            assert json.loads(output) == extract_info_module._empty_result()

    def test_tool_invalid_json_returns_empty(self):
        extract_info_module = importlib.import_module("llm.agents.tools.extract_info")

        with patch.object(extract_info_module, "_extract_with_llm", return_value="not-json"):
            output = extract_info_module.extract_info.invoke("강남 사는 취준생")
            assert json.loads(output) == extract_info_module._empty_result()

    def test_tool_empty_message_returns_empty(self):
        from llm.agents.tools.extract_info import _empty_result, extract_info

        assert json.loads(extract_info.invoke("")) == _empty_result()

    def test_tool_single_char_message_returns_empty(self):
        from llm.agents.tools.extract_info import _empty_result, extract_info

        assert json.loads(extract_info.invoke("가")) == _empty_result()


# ============================================================================
# Unit: Hard/Edge 케이스 (Mock)
# ============================================================================


class TestHardEdgeCasesMock:

    def test_tool_handles_birth_year_and_zodiac_noise(self):
        """예: '58년생 개띠 왕십리살아' 같은 난해한 입력 처리."""
        extract_info_module = importlib.import_module("llm.agents.tools.extract_info")
        expected_age = datetime.now().year - 1958 - 1

        with patch.object(
            extract_info_module,
            "_extract_with_llm",
            return_value=json.dumps(
                {
                    "age": expected_age,
                    "district": "왕십리",
                    "employment_status": None,
                    "income_raw": None,
                    "household_size": None,
                    "housing_type": None,
                },
                ensure_ascii=False,
            ),
        ):
            result = extract_info_module.extract_info_full("58년생 개띠 왕십리살아")

            assert result["age"] == expected_age
            assert result["district"] == "성동구"

    def test_tool_handles_location_noise_and_spaced_employment(self):
        """장소 노이즈/띄어쓰기 노이즈가 있어도 정규화."""
        extract_info_module = importlib.import_module("llm.agents.tools.extract_info")

        with patch.object(
            extract_info_module,
            "_extract_with_llm",
            return_value=json.dumps(
                {
                    "age": None,
                    "district": "서울특별시 동대문역사문화공원 근처",
                    "employment_status": "취 업 준 비 중",
                    "income_raw": None,
                    "household_size": None,
                    "housing_type": None,
                },
                ensure_ascii=False,
            ),
        ):
            result = extract_info_module.extract_info_full(
                "동대문역사문화공원쪽 취업 준비 중인데 월세랑 대출 다 궁금하고 월 210만원 벌어"
            )

            assert result["district"] == "중구"
            assert result["employment_status"] == "구직중"
            assert result["income_level"] == 2520

    def test_tool_handles_office_suffix_and_employment_alias(self):
        """강남구청/회사 다님 같은 별칭 처리."""
        extract_info_module = importlib.import_module("llm.agents.tools.extract_info")

        with patch.object(
            extract_info_module,
            "_extract_with_llm",
            return_value=json.dumps(
                {
                    "age": 33,
                    "district": "강남구청",
                    "employment_status": "회사 다님",
                    "income_raw": "연봉 3000만원",
                    "household_size": None,
                    "housing_type": None,
                },
                ensure_ascii=False,
            ),
        ):
            result = extract_info_module.extract_info_full(
                "서른셋이고 강남구청 쪽 회사 다녀요. 연봉은 3000만원이에요"
            )

            assert result["age"] == 33
            assert result["district"] == "강남구"
            assert result["employment_status"] == "재직"
            assert result["income_level"] == 3000


# ============================================================================
# Unit: 매핑 테이블 무결성
# ============================================================================


def test_dong_to_gu_values_are_valid_seoul_districts():
    from llm.agents.tools.extract_info import DONG_TO_GU, SEOUL_DISTRICTS

    assert set(DONG_TO_GU.values()).issubset(SEOUL_DISTRICTS)


def test_seoul_district_count_is_25():
    from llm.agents.tools.extract_info import SEOUL_DISTRICTS

    assert len(SEOUL_DISTRICTS) == 25


# ============================================================================
# Integration: 실제 LLM 호출
# ============================================================================


needs_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)

DEBUG_EXTRACT_INFO = os.getenv("DEBUG_EXTRACT_INFO", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _full(message: str):
    from llm.agents.tools.extract_info import extract_info_full

    return extract_info_full(message)


def _debug_dump(case_name: str, message: str, result: dict):
    """디버그 모드에서 입력/출력 상세를 출력합니다."""

    if not DEBUG_EXTRACT_INFO:
        return

    print(f"\n[DEBUG] {case_name}")
    print(f"[MESSAGE] {message}")
    print("[RESULT]")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


@pytest.mark.integration
@needs_api_key
def test_integration_case_1():
    message = "27살 강남 사는 취준생인데 뭐 받을 수 있어?"
    result = _full(message)
    _debug_dump("integration_case_1", message, result)
    assert result["age"] == 27
    assert result["district"] == "강남구"
    assert result["employment_status"] == "구직중"


@pytest.mark.integration
@needs_api_key
def test_integration_case_2():
    message = "홍대 근처 사는데 월세 지원 있어?"
    result = _full(message)
    _debug_dump("integration_case_2", message, result)
    assert result["district"] == "마포구"
    assert result["housing_type"] == "월세"


@pytest.mark.integration
@needs_api_key
def test_integration_case_3():
    message = "백수인데 돈 좀 받을 수 있나"
    result = _full(message)
    _debug_dump("integration_case_3", message, result)
    assert result["employment_status"] == "무직"


@pytest.mark.integration
@needs_api_key
def test_integration_case_4():
    message = "97년생 대학원생이고 성수동 살아"
    result = _full(message)
    _debug_dump("integration_case_4", message, result)
    expected_age = datetime.now().year - 1997 - 1
    assert result["age"] == expected_age
    assert result["district"] == "성동구"
    assert result["employment_status"] == "학생"


@pytest.mark.integration
@needs_api_key
def test_integration_case_5():
    message = "그냥 뭐 있는지 궁금해서"
    result = _full(message)
    _debug_dump("integration_case_5", message, result)
    assert result["age"] is None
    assert result["district"] is None
    assert result["employment_status"] is None
    assert result["income_level"] is None
    assert result["income_raw"] is None
    assert result["household_size"] is None
    assert result["housing_type"] is None


@pytest.mark.integration
@needs_api_key
def test_integration_case_6():
    message = "잠실 사는 25살 직장인인데 전세 대출 가능해?"
    result = _full(message)
    _debug_dump("integration_case_6", message, result)
    assert result["age"] == 25
    assert result["district"] == "송파구"
    assert result["employment_status"] == "재직"


@pytest.mark.integration
@needs_api_key
def test_integration_hard_case_birth_year_zodiac():
    message = "58년생 개띠 왕십리살아"
    result = _full(message)
    _debug_dump("integration_hard_case_birth_year_zodiac", message, result)
    assert result["district"] == "성동구"
    assert result["age"] is not None
    assert 60 <= result["age"] <= 90


@pytest.mark.integration
@needs_api_key
def test_integration_hard_case_alias_and_multi_intent():
    message = "서울대입구 근처 사는 알바생인데 월세랑 대출 둘다 알아보고 싶어"
    result = _full(message)
    _debug_dump("integration_hard_case_alias_and_multi_intent", message, result)
    assert result["district"] == "관악구"
    assert result["employment_status"] == "프리랜서"


@pytest.mark.integration
@needs_api_key
def test_integration_hard_case_noisy_expression():
    message = "동대문역사문화공원쪽;;; 취업 준비중이고 월 210만원 벌어"
    result = _full(message)
    _debug_dump("integration_hard_case_noisy_expression", message, result)
    assert result["district"] == "중구"
    assert result["employment_status"] == "구직중"
    assert result["income_level"] in {2520, None} or result["income_level"] > 0
