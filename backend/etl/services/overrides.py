"""
정책별 필드 보정 (ETL override layer)

[BRAIN4-37 C02] 신규 파일
- POLICY_FIELD_OVERRIDES: 정책별 보정 데이터 (C03~C05에서 채움)
- apply_overrides(): 보정 적용 함수
"""
import logging

logger = logging.getLogger(__name__)


POLICY_FIELD_OVERRIDES: dict[str, dict[str, str]] = {
    # C03~C05에서 채움
    # 예시:
    # "20250123005400110393": {
    #     "education_status": "0049010",
    #     "employment_status": "0013010",
    # },
}


def apply_overrides(
    policy_id: str, fields: dict[str, str]
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """
    정책별 override 적용.

    Args:
        policy_id: 정책 ID
        fields: {"education_status": "0049009", "employment_status": "0013009"}

    Returns:
        (updated_fields, change_logs)
    """
    overrides = POLICY_FIELD_OVERRIDES.get(policy_id)
    if not overrides:
        return fields, []

    updated = dict(fields)
    logs = []

    for field, target_value in overrides.items():
        if field not in updated:
            logger.warning(
                f"Override 키 오류: {policy_id} 의 '{field}' 필드가 "
                f"대상에 존재하지 않음 (무시됨)"
            )
            continue

        before = updated[field]
        if before != target_value:
            updated[field] = target_value
            logs.append({
                "policy_id": policy_id,
                "field": field,
                "before": before,
                "after": target_value,
                "reason": "decision_sheet approved",
            })
            logger.info(
                f"Override 적용: {policy_id} {field} "
                f"'{before}' → '{target_value}'"
            )

    return updated, logs
