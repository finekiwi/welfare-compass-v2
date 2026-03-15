"""
check_eligibility 룰베이스 테스트

요구사항:
- 입력/출력은 JSON 문자열
- 나이/소득/지역 3단 판정
- 종합 판정 우선순위: False > None > True
"""

import json
import logging
from datetime import date, timedelta


def _policy(**overrides):
    policy = {
        "policy_id": "P001",
        "title": "테스트 정책",
        "age_min": 19,
        "age_max": 39,
        "income_level": "0043001",
        "income_max": 3600,
        "district": "서울",
    }
    policy.update(overrides)
    return policy


def _user(**overrides):
    user = {
        "age": 25,
        "income_level": 2400,
        "district": "강남구",
    }
    user.update(overrides)
    return user


def _default_fetcher(_policy_ids):
    return []


def _invoke(policies, user_info, policy_fetcher=None):
    from llm.agents.tools.check_eligibility import create_check_eligibility

    tool = create_check_eligibility(policy_fetcher or _default_fetcher)
    raw = tool.invoke(
        {
            "policies": json.dumps(policies, ensure_ascii=False),
            "user_info": json.dumps(user_info, ensure_ascii=False),
        }
    )
    assert isinstance(raw, str)
    return json.loads(raw)


def _invoke_raw(policies_raw: str, user_info_raw: str, policy_fetcher=None):
    from llm.agents.tools.check_eligibility import create_check_eligibility

    tool = create_check_eligibility(policy_fetcher or _default_fetcher)
    raw = tool.invoke(
        {
            "policies": policies_raw,
            "user_info": user_info_raw,
        }
    )
    assert isinstance(raw, str)
    return json.loads(raw)


def _first(policy, user_info):
    result = _invoke([policy], user_info)
    assert isinstance(result, list)
    assert len(result) == 1
    return result[0]


def _eligible_row(**overrides):
    row = {
        "policy_id": "R001",
        "title": "기본 정책",
        "description": "",
        "support_content": "",
        "category": "",
        "apply_end_date": None,
        "is_eligible": True,
        "reasons": [],
        "details": {},
    }
    row.update(overrides)
    return row


def _rank(rows, user_info):
    from llm.agents.tools.check_eligibility import _rank_eligible_policies

    return _rank_eligible_policies(rows, user_info)


class TestAgeRules:
    def test_eligible_age_true(self):
        row = _first(_policy(age_min=19, age_max=39), _user(age=25))
        assert row["details"]["age"]["result"] is True
        assert row["is_eligible"] is True

    def test_ineligible_age_false(self):
        row = _first(_policy(age_min=19, age_max=39), _user(age=45))
        assert row["details"]["age"]["result"] is False
        assert row["is_eligible"] is False

    def test_boundary_age_19_needs_confirmation(self):
        row = _first(_policy(age_min=19, age_max=39), _user(age=19))
        assert row["details"]["age"]["result"] is None
        assert row["is_eligible"] is None

    def test_boundary_age_39_needs_confirmation(self):
        row = _first(_policy(age_min=19, age_max=39), _user(age=39))
        assert row["details"]["age"]["result"] is None
        assert row["is_eligible"] is None

    def test_age_39_with_min_39_is_true_under_current_spec(self):
        row = _first(_policy(age_min=39, age_max=45), _user(age=39))
        assert row["details"]["age"]["result"] is True
        assert row["is_eligible"] is True

    def test_non_boundary_age_25_with_max_25_true(self):
        row = _first(_policy(age_min=19, age_max=25), _user(age=25))
        assert row["details"]["age"]["result"] is True
        assert row["is_eligible"] is True

    def test_missing_user_age_none(self):
        row = _first(_policy(age_min=19, age_max=39), _user(age=None))
        assert row["details"]["age"]["result"] is None
        assert row["is_eligible"] is None

    def test_missing_policy_age_min_defaults_to_zero(self):
        row = _first(_policy(age_min=None, age_max=30), _user(age=25))
        assert row["details"]["age"]["result"] is True
        assert "0~30" in row["details"]["age"]["message"]

    def test_missing_policy_age_max_defaults_to_999(self):
        row = _first(_policy(age_min=19, age_max=None), _user(age=80))
        assert row["details"]["age"]["result"] is True
        assert "19~999" in row["details"]["age"]["message"]

    def test_string_age_is_casted(self):
        row = _first(_policy(age_min=19, age_max=39), _user(age="25"))
        assert row["details"]["age"]["result"] is True
        assert row["is_eligible"] is True

    def test_boolean_age_is_not_casted(self):
        row = _first(_policy(age_min=19, age_max=39), _user(age=True))
        assert row["details"]["age"]["result"] is None
        assert "나이 정보 없음" in row["details"]["age"]["message"]
        assert row["is_eligible"] is None


class TestIncomeRules:
    def test_income_any_true(self):
        row = _first(_policy(income_level="0043001"), _user(income=9999))
        assert row["details"]["income"]["result"] is True

    def test_income_etc_true(self):
        row = _first(_policy(income_level="0043003"), _user(income=9999))
        assert row["details"]["income"]["result"] is True

    def test_income_empty_true(self):
        row = _first(_policy(income_level=""), _user(income=9999))
        assert row["details"]["income"]["result"] is True

    def test_income_unknown_code_fail_open_true(self):
        row = _first(_policy(income_level="9999999"), _user(income=9999))
        assert row["details"]["income"]["result"] is True

    def test_income_annual_met_true(self):
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income=2400))
        assert row["details"]["income"]["result"] is True

    def test_income_annual_not_met_false(self):
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income_level=4000))
        assert row["details"]["income"]["result"] is False
        assert row["is_eligible"] is False

    def test_income_annual_missing_user_income_none(self):
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income_level=None))
        assert row["details"]["income"]["result"] is None
        assert row["is_eligible"] is None

    def test_income_annual_missing_income_max_true(self):
        row = _first(_policy(income_level="0043002", income_max=None), _user(income=9000))
        assert row["details"]["income"]["result"] is True

    def test_income_annual_income_max_zero_true(self):
        row = _first(_policy(income_level="0043002", income_max=0), _user(income=9000))
        assert row["details"]["income"]["result"] is True

    def test_string_income_is_casted(self):
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income="2400"))
        assert row["details"]["income"]["result"] is True
        assert row["is_eligible"] is True

    def test_boolean_income_is_not_casted(self):
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income_level=False))
        assert row["details"]["income"]["result"] is None
        assert "소득 정보 없음" in row["details"]["income"]["message"]
        assert row["is_eligible"] is None

    def test_negative_income_max_logs_warning_and_passes(self, caplog):
        with caplog.at_level(logging.WARNING):
            row = _first(_policy(policy_id="NEG1", income_level="0043002", income_max=-500), _user(income=2400))
        assert row["details"]["income"]["result"] is True
        assert "비정상값" in row["details"]["income"]["message"]
        assert any(
            "income_max is negative" in rec.message
            and "policy_id=NEG1" in rec.message
            and "income_max=-500" in rec.message
            for rec in caplog.records
        )


class TestRegionRules:
    def test_seoul_wide_policy_seoul_true(self):
        row = _first(_policy(district="서울"), _user(district="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_seoul_wide_policy_seoulsi_true(self):
        row = _first(_policy(district="서울시"), _user(district="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_district_match_true(self):
        row = _first(_policy(district="강남구"), _user(district="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_district_mismatch_false(self):
        row = _first(_policy(district="강남구"), _user(district="서초구"))
        assert row["details"]["region"]["result"] is False
        assert row["is_eligible"] is False

    def test_policy_district_empty_true(self):
        row = _first(_policy(district=""), _user(district="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_user_residence_empty_none(self):
        row = _first(_policy(district="강남구"), _user(district=""))
        assert row["details"]["region"]["result"] is None
        assert row["is_eligible"] is None

    def test_district_partial_match_is_false(self):
        row = _first(_policy(district="강남구"), _user(district="강남"))
        assert row["details"]["region"]["result"] is False
        assert row["is_eligible"] is False


class TestJudgeRules:
    def test_all_eligible_true(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=27, income_level=2400, district="강남구"),
        )
        assert row["is_eligible"] is True
        assert row["reasons"] == []

    def test_only_age_false(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=45, income_level=2400, district="강남구"),
        )
        assert row["is_eligible"] is False
        assert any("나이 미충족" in reason for reason in row["reasons"])

    def test_only_income_none(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=27, income_level=None, district="강남구"),
        )
        assert row["is_eligible"] is None
        assert any("소득 정보 없음" in reason for reason in row["reasons"])

    def test_age_false_and_income_none_false_wins(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=45, income_level=None, district="강남구"),
        )
        assert row["is_eligible"] is False
        assert any("나이 미충족" in reason for reason in row["reasons"])
        assert not any("소득 정보 없음" in reason for reason in row["reasons"])

    def test_five_policies_batch(self):
        policies = [
            _policy(policy_id="P1", title="소득확인필요-서울전체", age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _policy(policy_id="P2", title="나이부적격", age_min=19, age_max=24, district="서울"),
            _policy(policy_id="P3", title="소득확인필요", income_level="0043002", income_max=3600, district="서울"),
            _policy(policy_id="P4", title="지역부적격", district="서초구"),
            _policy(policy_id="P5", title="소득확인필요-강남구", district="강남구", income_level="0043002", income_max=3600),
        ]
        user = _user(age=25, income_level=None, district="강남구")
        rows = _invoke(policies, user)

        assert isinstance(rows, list)
        assert len(rows) == 5
        assert [row["policy_id"] for row in rows] == ["P1", "P2", "P3", "P4", "P5"]
        assert [row["is_eligible"] for row in rows] == [None, False, None, False, None]
        assert any("소득 정보 없음" in reason for reason in rows[0]["reasons"])
        assert any("나이 미충족" in reason for reason in rows[1]["reasons"])
        assert any("소득 정보 없음" in reason for reason in rows[2]["reasons"])
        assert any("지역 미충족" in reason for reason in rows[3]["reasons"])
        assert any("소득 정보 없음" in reason for reason in rows[4]["reasons"])

    def test_five_policies_batch_includes_income_eligible_case(self):
        policies = [
            _policy(policy_id="Q1", title="완전적격", age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _policy(policy_id="Q2", title="나이부적격", age_min=19, age_max=24, district="서울"),
            _policy(policy_id="Q3", title="소득부적격", income_level="0043002", income_max=2000, district="서울"),
            _policy(policy_id="Q4", title="지역부적격", district="서초구"),
            _policy(policy_id="Q5", title="소득무관-적격", district="강남구", income_level="0043001"),
        ]
        user = _user(age=25, income_level=2400, district="강남구")
        rows = _invoke(policies, user)

        assert isinstance(rows, list)
        assert len(rows) == 5
        assert [row["policy_id"] for row in rows] == ["Q1", "Q5", "Q2", "Q3", "Q4"]
        assert [row["is_eligible"] for row in rows] == [True, True, False, False, False]
        assert rows[0]["reasons"] == []
        assert rows[1]["reasons"] == []
        assert any("나이 미충족" in reason for reason in rows[2]["reasons"])
        assert any("소득 미충족" in reason for reason in rows[3]["reasons"])
        assert any("지역 미충족" in reason for reason in rows[4]["reasons"])

    def test_non_dict_policy_items_are_skipped_with_warning(self, caplog):
        policies = [
            _policy(policy_id="S1", title="정상1"),
            "hello",
            123,
            _policy(policy_id="S2", title="정상2"),
        ]

        with caplog.at_level(logging.WARNING):
            rows = _invoke(policies, _user())

        assert len(rows) == 2
        assert [row["policy_id"] for row in rows] == ["S1", "S2"]

        warnings = [
            rec.message for rec in caplog.records if "invalid policy item skipped" in rec.message
        ]
        assert any("index=1" in msg and "item_type=str" in msg for msg in warnings)
        assert any("index=2" in msg and "item_type=int" in msg for msg in warnings)


class TestErrorHandling:
    def test_empty_policies_string_returns_error(self):
        data = _invoke_raw("", json.dumps(_user(), ensure_ascii=False))
        assert "error" in data
        assert data["policies_checked"] == 0

    def test_invalid_policies_json_returns_error(self):
        data = _invoke_raw("{", json.dumps(_user(), ensure_ascii=False))
        assert "error" in data
        assert data["policies_checked"] == 0

    def test_empty_user_info_string_returns_error(self):
        data = _invoke_raw(json.dumps([_policy()], ensure_ascii=False), "")
        assert "error" in data
        assert data["policies_checked"] == 0

    def test_empty_policy_list_is_valid(self):
        data = _invoke_raw("[]", json.dumps(_user(), ensure_ascii=False))
        assert isinstance(data, list)
        assert data == []

    def test_policies_json_object_returns_error(self):
        data = _invoke_raw('{"policy_id":"P001"}', json.dumps(_user(), ensure_ascii=False))
        assert "error" in data
        assert "policies는 JSON 리스트" in data["error"]
        assert data["policies_checked"] == 0

    def test_user_info_json_list_returns_error(self):
        data = _invoke_raw(json.dumps([_policy()], ensure_ascii=False), '["age", 25]')
        assert "error" in data
        assert "user_info는 JSON 객체" in data["error"]
        assert data["policies_checked"] == 0

    def test_all_mode_returns_guard_error(self):
        data = _invoke_raw(
            "all",
            json.dumps(_user(), ensure_ascii=False),
        )

        assert data["status"] == "error"
        assert "policies='all'은 지원하지 않습니다" in data["error"]
        assert data["policies_checked"] == 0


class TestNeedsFiltering:
    pass



class TestRankPolicies:
    def test_deadline_soon_policy_ranks_above_later_policy(self):
        ranked = _rank(
            [
                _eligible_row(
                    policy_id="LATE",
                    title="일반 지원 정책",
                    apply_end_date=(date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                ),
                _eligible_row(
                    policy_id="SOON",
                    title="일반 지원 정책",
                    apply_end_date=date.today() + timedelta(days=3),
                ),
            ],
            {},
        )

        assert [row["policy_id"] for row in ranked] == ["SOON", "LATE"]
        assert ranked[0]["_priority_score"] > ranked[1]["_priority_score"]

    def test_youth_policy_ranks_above_non_youth_policy(self):
        ranked = _rank(
            [
                _eligible_row(policy_id="NORMAL", title="일반 지원 정책"),
                _eligible_row(policy_id="YOUTH", title="청년 지원 정책"),
            ],
            {},
        )

        assert [row["policy_id"] for row in ranked] == ["YOUTH", "NORMAL"]

    def test_need_category_match_ranks_higher(self):
        ranked = _rank(
            [
                _eligible_row(policy_id="HOUSE", title="맞춤 정책", category="주거"),
                _eligible_row(policy_id="JOB", title="맞춤 정책", category="취업"),
            ],
            {"needs": ["취업"]},
        )

        assert [row["policy_id"] for row in ranked] == ["JOB", "HOUSE"]

    def test_string_need_is_supported(self):
        ranked = _rank(
            [
                _eligible_row(policy_id="HOUSE", title="맞춤 정책", category="주거"),
                _eligible_row(policy_id="JOB", title="맞춤 정책", category="취업"),
            ],
            {"needs": "취업"},
        )

        assert [row["policy_id"] for row in ranked] == ["JOB", "HOUSE"]

    def test_employment_status_match_ranks_higher(self):
        ranked = _rank(
            [
                _eligible_row(policy_id="CULTURE", title="문화 지원 정책"),
                _eligible_row(policy_id="JOB", title="취업 지원 정책"),
            ],
            {"employment_status": "구직중"},
        )

        assert [row["policy_id"] for row in ranked] == ["JOB", "CULTURE"]

    def test_employment_status_changup_jun_bi_matches_canonical(self):
        """창업준비 canonical value가 창업 관련 정책에 가중치를 부여한다."""
        ranked = _rank(
            [
                _eligible_row(policy_id="CULTURE", title="문화 지원 정책"),
                _eligible_row(policy_id="BIZ", title="창업 지원 정책"),
            ],
            {"employment_status": "창업준비"},
        )

        assert [row["policy_id"] for row in ranked] == ["BIZ", "CULTURE"]

    def test_employment_status_jayeongup_matches_canonical(self):
        """자영업 canonical value가 자영업 관련 정책에 가중치를 부여한다."""
        ranked = _rank(
            [
                _eligible_row(policy_id="CULTURE", title="문화 지원 정책"),
                _eligible_row(policy_id="SHOP", title="소상공인 지원 정책"),
            ],
            {"employment_status": "자영업"},
        )

        assert [row["policy_id"] for row in ranked] == ["SHOP", "CULTURE"]

    def test_employment_status_freelancer_matches_canonical(self):
        """프리랜서 canonical value가 프리랜서 관련 정책에 가중치를 부여한다."""
        ranked = _rank(
            [
                _eligible_row(policy_id="CULTURE", title="문화 지원 정책"),
                _eligible_row(policy_id="FREE", title="프리랜서 지원 정책"),
            ],
            {"employment_status": "프리랜서"},
        )

        assert [row["policy_id"] for row in ranked] == ["FREE", "CULTURE"]

    def test_employment_status_changup_does_not_get_bonus(self):
        """'창업'은 extract_info canonical value가 아니라 가중치가 적용되지 않는다.
        '창업준비'가 canonical value이며 창업 관련 정책에 가중치를 받는다."""
        ranked_changup = _rank(
            [
                _eligible_row(policy_id="CULTURE", title="문화 지원 정책"),
                _eligible_row(policy_id="BIZ", title="창업 사업 지원 정책"),
            ],
            {"employment_status": "창업"},  # non-canonical value
        )
        ranked_changup_junbi = _rank(
            [
                _eligible_row(policy_id="CULTURE", title="문화 지원 정책"),
                _eligible_row(policy_id="BIZ", title="창업 사업 지원 정책"),
            ],
            {"employment_status": "창업준비"},  # canonical value
        )

        # 창업(non-canonical)은 가중치 없어 순서 유지, 창업준비(canonical)는 BIZ가 앞으로
        assert ranked_changup[0]["policy_id"] == "CULTURE"
        assert ranked_changup_junbi[0]["policy_id"] == "BIZ"

    def test_monthly_rent_housing_bonus_applied(self):
        ranked = _rank(
            [
                _eligible_row(policy_id="GENERAL", title="일반 혜택 정책"),
                _eligible_row(policy_id="MONTHLY", title="월세 지원 정책"),
            ],
            {"housing_type": "월세"},
        )

        assert [row["policy_id"] for row in ranked] == ["MONTHLY", "GENERAL"]
        assert ranked[0]["_priority_score"] > ranked[1]["_priority_score"]

    def test_owned_housing_penalty_applied(self):
        ranked = _rank(
            [
                _eligible_row(policy_id="MONTHLY", title="월세 지원 정책"),
                _eligible_row(policy_id="GENERAL", title="일반 지원 정책"),
            ],
            {"housing_type": "자가"},
        )

        assert [row["policy_id"] for row in ranked] == ["GENERAL", "MONTHLY"]
        assert ranked[1]["_priority_score"] < ranked[0]["_priority_score"]

    def test_empty_eligible_returns_empty_list(self):
        assert _rank([], {}) == []

    def test_missing_optional_user_fields_does_not_error(self):
        ranked = _rank([_eligible_row(policy_id="SAFE", title="지원 정책")], {})

        assert [row["policy_id"] for row in ranked] == ["SAFE"]
        assert "_priority_score" in ranked[0]

    def test_priority_score_key_is_included(self):
        ranked = _rank(
            [_eligible_row(policy_id="MONEY", title="지원 정책", support_content="월 20만원 지원금")],
            {},
        )

        assert "_priority_score" in ranked[0]
        assert ranked[0]["_priority_score"] >= 25

    def test_check_eligibility_sorts_eligible_first_and_preserves_ineligible_order(self):
        policies = [
            _policy(policy_id="E1", title="일반 정책", district="서울"),
            _policy(policy_id="N1", title="나이부적격", age_min=19, age_max=24, district="서울"),
            _policy(
                policy_id="E2",
                title="청년 지원 정책",
                district="서울",
                apply_end_date=(date.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
            ),
            _policy(policy_id="N2", title="지역부적격", district="서초구"),
        ]

        rows = _invoke(policies, _user(age=25, income_level=2400, district="강남구"))

        assert [row["policy_id"] for row in rows] == ["E2", "E1", "N1", "N2"]
        assert [row["is_eligible"] for row in rows] == [True, True, False, False]
        assert rows[0]["_priority_score"] > rows[1]["_priority_score"]
        assert "_priority_score" not in rows[2]
        assert "_priority_score" not in rows[3]


class TestUserInfoCompatibilityAliases:
    def test_district_alias_is_used_for_region_check(self):
        row = _first(_policy(district="강남구"), _user(district="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_income_level_numeric_alias_is_used_when_income_missing(self):
        row = _first(
            _policy(income_level="0043002", income_max=3600, district="서울"),
            _user(income=None, income_level=2400),
        )
        assert row["details"]["income"]["result"] is True
        assert row["is_eligible"] is True


class TestOutputStructure:
    def test_result_has_required_top_level_fields(self):
        row = _first(_policy(policy_id="PX1", title="정책1"), _user())
        assert {"policy_id", "title", "is_eligible", "reasons", "details"} <= set(row.keys())

    def test_details_contains_age_income_region_result_and_message(self):
        row = _first(_policy(), _user())
        details = row["details"]

        assert {"age", "income", "region"} <= set(details.keys())
        assert {"result", "message"} <= set(details["age"].keys())
        assert {"result", "message"} <= set(details["income"].keys())
        assert {"result", "message"} <= set(details["region"].keys())

    def test_json_round_trip(self):
        raw_rows = _invoke([_policy(policy_id="PX2", title="정책2")], _user())
        encoded = json.dumps(raw_rows, ensure_ascii=False)
        decoded = json.loads(encoded)
        assert decoded == raw_rows
