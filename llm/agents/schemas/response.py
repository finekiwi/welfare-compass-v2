from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
import re
from typing import Any


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCERTAIN = "uncertain"


def _coerce_eligibility(value: Any) -> EligibilityStatus:
    if isinstance(value, EligibilityStatus):
        return value
    if value is True:
        return EligibilityStatus.ELIGIBLE
    if value is False:
        return EligibilityStatus.INELIGIBLE
    if value is None:
        return EligibilityStatus.UNCERTAIN
    if isinstance(value, str):
        normalized = value.strip().lower()
        for status in EligibilityStatus:
            if normalized == status.value:
                return status
    raise ValueError(f"Unsupported eligibility value: {value!r}")


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    return cleaned or None


def _collapse_summary(*values: Any) -> str:
    for value in values:
        text = _normalize_optional_text(value)
        if text:
            return re.sub(r"\s+", " ", text)
    return ""


def _normalize_iso_date(value: Any) -> str | None:
    text = _normalize_optional_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _calculate_dday(deadline: str | None, today: date | None = None) -> int | None:
    normalized = _normalize_iso_date(deadline)
    if normalized is None:
        return None
    base_date = today or date.today()
    return (date.fromisoformat(normalized) - base_date).days


def _get_first(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


@dataclass
class PolicyResult:
    # API 응답용 구조이며 state.PolicyInfo와 의도적으로 다르다:
    # policy_id/title/apply_end_date 등 내부 필드를 plcy_no/plcy_nm/summary/deadline으로 재구성한다.
    plcy_no: str
    plcy_nm: str
    category: str
    summary: str
    eligibility: EligibilityStatus
    ineligible_reasons: list[str] = field(default_factory=list)
    deadline: str | None = None
    dday: int | None = None
    apply_url: str | None = None
    detail_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["eligibility"] = self.eligibility.value
        return data

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        today: date | None = None,
    ) -> "PolicyResult":
        deadline = _normalize_iso_date(_get_first(data, "deadline", "aply_end_dt"))
        dday = data.get("dday")
        if dday is None:
            dday = _calculate_dday(deadline, today=today)

        reasons = data.get("ineligible_reasons")
        if not isinstance(reasons, list):
            reasons = []

        return cls(
            # TODO: LLM이 plcy_no를 누락하면 빈 문자열이 됨 — 의도치 않은 빈 정책 카드 방지 로직 추가 필요
            plcy_no=str(_get_first(data, "plcy_no", "policy_id") or ""),
            plcy_nm=str(_get_first(data, "plcy_nm", "title") or ""),
            category=str(_get_first(data, "category", "category_name") or ""),
            summary=_collapse_summary(data.get("summary"), data.get("plcy_expln_cn")),
            eligibility=_coerce_eligibility(data.get("eligibility")),
            ineligible_reasons=[str(reason) for reason in reasons],
            deadline=deadline,
            dday=dday,
            apply_url=_normalize_optional_text(_get_first(data, "apply_url", "aply_url_addr")),
            detail_url=_normalize_optional_text(data.get("detail_url")),
        )


@dataclass
class ChatResponse:
    message: str
    policies: list[PolicyResult] = field(default_factory=list)
    follow_up: str | None = None
    # SSE 스트리밍 시 단계 표시용 (현재 미사용, 향후 SSE PR에서 활성화 예정)
    stage: str = "complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "policies": [policy.to_dict() for policy in self.policies],
            "follow_up": self.follow_up,
            "stage": self.stage,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        today: date | None = None,
    ) -> "ChatResponse":
        policies = data.get("policies")
        if not isinstance(policies, list):
            policies = []

        return cls(
            message=str(data.get("message") or ""),
            policies=[
                PolicyResult.from_dict(policy, today=today)
                for policy in policies
                if isinstance(policy, dict)
            ],
            follow_up=_normalize_optional_text(data.get("follow_up")),
            stage=str(data.get("stage") or "complete"),
        )


def policy_info_to_result(
    policy: dict[str, Any],
    eligibility_result: dict[str, Any],
    *,
    today: date | None = None,
) -> PolicyResult:
    if not isinstance(policy, dict):
        raise TypeError("policy must be a dict")
    if not isinstance(eligibility_result, dict):
        raise TypeError("eligibility_result must be a dict")

    deadline = _normalize_iso_date(_get_first(policy, "deadline", "apply_end_date"))
    reasons = _get_first(eligibility_result, "ineligible_reasons", "reasons")
    if not isinstance(reasons, list):
        reasons = []

    detail_url = _normalize_optional_text(_get_first(policy, "detail_url", "link"))

    return PolicyResult(
        # TODO: policy에 plcy_no/policy_id가 없으면 빈 문자열이 됨 — 의도치 않은 빈 정책 카드 방지 로직 추가 필요
        plcy_no=str(_get_first(policy, "plcy_no", "policy_id") or ""),
        plcy_nm=str(_get_first(policy, "plcy_nm", "title") or ""),
        category=str(_get_first(policy, "category", "category_name") or ""),
        summary=_collapse_summary(
            policy.get("summary"),
            policy.get("support_content"),
            policy.get("description"),
            policy.get("plcy_expl"),
        ),
        eligibility=_coerce_eligibility(eligibility_result.get("is_eligible")),
        ineligible_reasons=[str(reason) for reason in reasons],
        deadline=deadline,
        dday=_calculate_dday(deadline, today=today),
        apply_url=_normalize_optional_text(policy.get("apply_url")),
        detail_url=detail_url,
    )


def build_chat_response(
    message: str,
    policies: list[dict[str, Any]],
    eligibility_results: list[dict[str, Any]],
    follow_up: str | None = None,
    *,
    today: date | None = None,
) -> ChatResponse:
    if len(policies) != len(eligibility_results):
        raise ValueError("policies and eligibility_results must have the same length")

    return ChatResponse(
        message=message,
        policies=[
            policy_info_to_result(policy, eligibility_result, today=today)
            for policy, eligibility_result in zip(policies, eligibility_results)
        ],
        follow_up=_normalize_optional_text(follow_up),
        stage="complete",
    )
