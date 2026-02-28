"""
check_eligibility 룰베이스 테스트

요구사항:
- 입력/출력은 JSON 문자열
- 나이/소득/지역 3단 판정
- 종합 판정 우선순위: False > None > True
"""

import json
import logging


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
        "income": 2400,
        "residence": "강남구",
    }
    user.update(overrides)
    return user


def _invoke(policies, user_info):
    from llm.agents.tools.check_eligibility import check_eligibility

    raw = check_eligibility.invoke(
        {
            "policies": json.dumps(policies, ensure_ascii=False),
            "user_info": json.dumps(user_info, ensure_ascii=False),
        }
    )
    assert isinstance(raw, str)
    return json.loads(raw)


def _invoke_raw(policies_raw: str, user_info_raw: str):
    from llm.agents.tools.check_eligibility import check_eligibility

    raw = check_eligibility.invoke(
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
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income=4000))
        assert row["details"]["income"]["result"] is False
        assert row["is_eligible"] is False

    def test_income_annual_missing_user_income_none(self):
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income=None))
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
        row = _first(_policy(income_level="0043002", income_max=3600), _user(income=False))
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
        row = _first(_policy(district="서울"), _user(residence="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_seoul_wide_policy_seoulsi_true(self):
        row = _first(_policy(district="서울시"), _user(residence="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_district_match_true(self):
        row = _first(_policy(district="강남구"), _user(residence="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_district_mismatch_false(self):
        row = _first(_policy(district="강남구"), _user(residence="서초구"))
        assert row["details"]["region"]["result"] is False
        assert row["is_eligible"] is False

    def test_policy_district_empty_true(self):
        row = _first(_policy(district=""), _user(residence="강남구"))
        assert row["details"]["region"]["result"] is True

    def test_user_residence_empty_none(self):
        row = _first(_policy(district="강남구"), _user(residence=""))
        assert row["details"]["region"]["result"] is None
        assert row["is_eligible"] is None

    def test_district_partial_match_is_false(self):
        row = _first(_policy(district="강남구"), _user(residence="강남"))
        assert row["details"]["region"]["result"] is False
        assert row["is_eligible"] is False


class TestJudgeRules:
    def test_all_eligible_true(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=27, income=2400, residence="강남구"),
        )
        assert row["is_eligible"] is True
        assert row["reasons"] == []

    def test_only_age_false(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=45, income=2400, residence="강남구"),
        )
        assert row["is_eligible"] is False
        assert any("나이 미충족" in reason for reason in row["reasons"])

    def test_only_income_none(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=27, income=None, residence="강남구"),
        )
        assert row["is_eligible"] is None
        assert any("소득 정보 없음" in reason for reason in row["reasons"])

    def test_age_false_and_income_none_false_wins(self):
        row = _first(
            _policy(age_min=19, age_max=34, income_level="0043002", income_max=3600, district="서울"),
            _user(age=45, income=None, residence="강남구"),
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
        user = _user(age=25, income=None, residence="강남구")
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
        user = _user(age=25, income=2400, residence="강남구")
        rows = _invoke(policies, user)

        assert isinstance(rows, list)
        assert len(rows) == 5
        assert [row["policy_id"] for row in rows] == ["Q1", "Q2", "Q3", "Q4", "Q5"]
        assert [row["is_eligible"] for row in rows] == [True, False, False, False, True]
        assert rows[0]["reasons"] == []
        assert any("나이 미충족" in reason for reason in rows[1]["reasons"])
        assert any("소득 미충족" in reason for reason in rows[2]["reasons"])
        assert any("지역 미충족" in reason for reason in rows[3]["reasons"])
        assert rows[4]["reasons"] == []

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
