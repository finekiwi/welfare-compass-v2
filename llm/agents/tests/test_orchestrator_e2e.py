"""BRAIN4-42 fetcher 패턴 E2E(mock) 테스트."""

from __future__ import annotations

import json


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


def _user_info(**overrides) -> str:
    user = {
        "age": 27,
        "income_level": 2400,
        "district": "강남구",
    }
    user.update(overrides)
    return json.dumps(user, ensure_ascii=False)


def test_matching_policies_all_calls_fetcher():
    from llm.agents.tools.check_eligibility import create_check_eligibility

    calls = []

    def fetcher(policy_ids):
        calls.append(policy_ids)
        return []

    tool = create_check_eligibility(fetcher)
    raw = tool.invoke({"policies": "all", "user_info": _user_info()})

    assert calls == [None]
    data = json.loads(raw)
    assert "error" in data


def test_matching_policies_all_policies_alias():
    from llm.agents.tools.check_eligibility import create_check_eligibility

    calls = []

    def fetcher(policy_ids):
        calls.append(policy_ids)
        return []

    tool = create_check_eligibility(fetcher)
    raw = tool.invoke({"policies": "all_policies", "user_info": _user_info()})

    assert calls == [None]
    data = json.loads(raw)
    assert "error" in data


def test_matching_policies_all_returns_results():
    from llm.agents.tools.check_eligibility import create_check_eligibility

    def fetcher(_policy_ids):
        return [_policy(policy_id="P100", title="전체 매칭 정책")]

    tool = create_check_eligibility(fetcher)
    raw = tool.invoke({"policies": "all", "user_info": _user_info(age=27)})
    rows = json.loads(raw)

    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["policy_id"] == "P100"
    assert rows[0]["is_eligible"] is True


def test_explore_flow_ignores_fetcher():
    from llm.agents.tools.check_eligibility import create_check_eligibility

    called = False

    def fetcher(_policy_ids):
        nonlocal called
        called = True
        return []

    tool = create_check_eligibility(fetcher)
    raw = tool.invoke(
        {
            "policies": json.dumps([_policy(policy_id="P200")], ensure_ascii=False),
            "user_info": _user_info(),
        }
    )
    rows = json.loads(raw)

    assert called is False
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["policy_id"] == "P200"


def test_default_fetcher_returns_empty():
    from llm.agents.tools import create_tools

    tools = create_tools()
    check_eligibility_tool = next(
        tool for tool in tools if getattr(tool, "name", "") == "check_eligibility"
    )

    raw = check_eligibility_tool.invoke({"policies": "all", "user_info": _user_info()})
    data = json.loads(raw)
    assert "error" in data


def test_matching_policies_all_fetcher_exception_returns_error():
    from llm.agents.tools.check_eligibility import create_check_eligibility

    def fetcher(_policy_ids):
        raise RuntimeError("db unavailable")

    tool = create_check_eligibility(fetcher)
    raw = tool.invoke({"policies": "all", "user_info": _user_info()})
    data = json.loads(raw)

    assert "error" in data
    assert "전체 정책 조회 실패" in data["error"]
    assert data["policies_checked"] == 0
