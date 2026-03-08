from __future__ import annotations

from datetime import date

import pytest

from llm.agents.schemas import (
    ChatResponse,
    EligibilityStatus,
    PolicyResult,
    build_chat_response,
    policy_info_to_result,
)


class TestPolicyResult:
    def test_constructs_with_all_fields(self):
        result = PolicyResult(
            plcy_no="P100",
            plcy_nm="청년월세지원",
            category="주거",
            summary="월세를 지원합니다.",
            eligibility=EligibilityStatus.ELIGIBLE,
            ineligible_reasons=[],
            deadline="2026-03-20",
            dday=12,
            apply_url="https://example.com/apply",
            detail_url="https://example.com/detail",
        )

        assert result.plcy_no == "P100"
        assert result.eligibility is EligibilityStatus.ELIGIBLE
        assert result.to_dict()["eligibility"] == "eligible"

    def test_constructs_with_optional_none_fields(self):
        result = PolicyResult(
            plcy_no="P101",
            plcy_nm="상시정책",
            category="취업",
            summary="상시 모집 정책입니다.",
            eligibility=EligibilityStatus.UNCERTAIN,
            deadline=None,
            dday=None,
            apply_url=None,
            detail_url=None,
        )

        assert result.deadline is None
        assert result.dday is None
        assert result.apply_url is None
        assert result.detail_url is None


class TestChatResponse:
    def test_round_trip_to_dict_from_dict(self):
        response = ChatResponse(
            message="맞는 정책을 정리했어요.",
            policies=[
                PolicyResult(
                    plcy_no="P100",
                    plcy_nm="청년월세지원",
                    category="주거",
                    summary="월세를 지원합니다.",
                    eligibility=EligibilityStatus.ELIGIBLE,
                    deadline="2026-03-20",
                    dday=12,
                    apply_url="https://example.com/apply",
                    detail_url="https://example.com/detail",
                )
            ],
            follow_up="더 확인할까요?",
            stage="complete",
        )

        restored = ChatResponse.from_dict(response.to_dict(), today=date(2026, 3, 8))

        assert restored == response


class TestPolicyInfoToResult:
    def test_maps_eligible_policy(self):
        result = policy_info_to_result(
            {
                "policy_id": "P100",
                "title": "청년월세지원",
                "category": "주거",
                "support_content": "월세를 지원합니다.",
                "apply_end_date": "2026-03-20",
                "apply_url": "https://example.com/apply",
                "link": "https://example.com/detail",
            },
            {
                "is_eligible": True,
                "reasons": [],
            },
            today=date(2026, 3, 8),
        )

        assert result.plcy_no == "P100"
        assert result.plcy_nm == "청년월세지원"
        assert result.summary == "월세를 지원합니다."
        assert result.eligibility is EligibilityStatus.ELIGIBLE
        assert result.ineligible_reasons == []
        assert result.deadline == "2026-03-20"
        assert result.dday == 12
        assert result.detail_url == "https://example.com/detail"

    def test_maps_ineligible_policy_and_reasons(self):
        result = policy_info_to_result(
            {
                "plcy_no": "P101",
                "plcy_nm": "청년취업지원",
                "category_name": "일자리",
                "description": "취업 준비를 돕습니다.",
                "deadline": "2026-03-01",
            },
            {
                "is_eligible": False,
                "ineligible_reasons": ["나이 조건 미충족"],
            },
            today=date(2026, 3, 8),
        )

        assert result.eligibility is EligibilityStatus.INELIGIBLE
        assert result.ineligible_reasons == ["나이 조건 미충족"]
        assert result.dday == -7

    def test_maps_uncertain_policy(self):
        result = policy_info_to_result(
            {
                "policy_id": "P102",
                "title": "청년금융지원",
                "category": "금융",
                "plcy_expl": "소득 확인이 더 필요합니다.",
                "apply_end_date": "",
            },
            {
                "is_eligible": None,
                "reasons": ["소득 정보 없음"],
            },
            today=date(2026, 3, 8),
        )

        assert result.eligibility is EligibilityStatus.UNCERTAIN
        assert result.ineligible_reasons == ["소득 정보 없음"]
        assert result.deadline is None
        assert result.dday is None

    def test_ignores_invalid_deadline(self):
        result = policy_info_to_result(
            {
                "policy_id": "P103",
                "title": "청년교육지원",
                "category": "교육",
                "summary": "교육비를 지원합니다.",
                "apply_end_date": "20260399",
            },
            {
                "is_eligible": True,
                "reasons": [],
            },
            today=date(2026, 3, 8),
        )

        assert result.deadline is None
        assert result.dday is None


class TestBuildChatResponse:
    def test_builds_response_with_index_matching(self):
        response = build_chat_response(
            message="추천 결과예요.",
            policies=[
                {
                    "policy_id": "P1",
                    "title": "정책1",
                    "category": "주거",
                    "summary": "첫 번째 정책",
                },
                {
                    "policy_id": "P2",
                    "title": "정책2",
                    "category": "취업",
                    "summary": "두 번째 정책",
                },
            ],
            eligibility_results=[
                {"is_eligible": True, "reasons": []},
                {"is_eligible": None, "reasons": ["소득 정보 없음"]},
            ],
            follow_up="원하시면 더 추려드릴게요.",
            today=date(2026, 3, 8),
        )

        assert [policy.plcy_no for policy in response.policies] == ["P1", "P2"]
        assert response.policies[0].eligibility is EligibilityStatus.ELIGIBLE
        assert response.policies[1].eligibility is EligibilityStatus.UNCERTAIN
        assert response.follow_up == "원하시면 더 추려드릴게요."

    def test_builds_empty_response_for_no_policies(self):
        response = build_chat_response(
            message="검색 결과가 없어요.",
            policies=[],
            eligibility_results=[],
            today=date(2026, 3, 8),
        )

        assert response.message == "검색 결과가 없어요."
        assert response.policies == []
        assert response.follow_up is None

    def test_raises_on_length_mismatch(self):
        with pytest.raises(ValueError):
            build_chat_response(
                message="길이 불일치",
                policies=[{"policy_id": "P1"}],
                eligibility_results=[],
            )


class TestDdayBehavior:
    def test_from_dict_calculates_future_dday_when_missing(self):
        result = PolicyResult.from_dict(
            {
                "plcy_no": "P200",
                "plcy_nm": "미래 정책",
                "category": "주거",
                "summary": "곧 마감됩니다.",
                "eligibility": "eligible",
                "deadline": "2026-03-10",
            },
            today=date(2026, 3, 8),
        )

        assert result.dday == 2

    def test_from_dict_keeps_none_dday_for_always_open(self):
        result = PolicyResult.from_dict(
            {
                "plcy_no": "P201",
                "plcy_nm": "상시 정책",
                "category": "복지문화",
                "summary": "상시 신청 가능",
                "eligibility": "uncertain",
                "deadline": None,
            },
            today=date(2026, 3, 8),
        )

        assert result.dday is None

    def test_from_dict_calculates_past_dday(self):
        result = PolicyResult.from_dict(
            {
                "plcy_no": "P202",
                "plcy_nm": "지난 정책",
                "category": "금융",
                "summary": "이미 마감되었습니다.",
                "eligibility": "ineligible",
                "deadline": "2026-03-01",
                "ineligible_reasons": ["기간 종료"],
            },
            today=date(2026, 3, 8),
        )

        assert result.dday == -7
