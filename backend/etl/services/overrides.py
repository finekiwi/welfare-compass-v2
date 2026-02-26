"""
정책별 필드 보정 (ETL override layer)

[BRAIN4-37 C02] 신규 파일
- POLICY_FIELD_OVERRIDES: 정책별 보정 데이터
- apply_overrides(): 보정 적용 함수

[BRAIN4-37 C08] 결정표 64건 반영 (A안 전체 승인, 2026-02-24 회의 확정)
- 소스: task-20260214-11-brain4-37-policy-decision-sheet-unique-64.md
- 코드 의미 근거: docs/API코드정보 (2).xlsx
"""
import logging

logger = logging.getLogger(__name__)


POLICY_FIELD_OVERRIDES: dict[str, dict[str, str]] = {
    # =========================================================================
    # 결정표 64건 반영 (A안 전체 승인, 2026-02-24 회의 확정)
    # 소스: task-20260214-11-brain4-37-policy-decision-sheet-unique-64.md
    # =========================================================================

    # --- job_unknown only (16건) ---
    "20250103005400210042": {
        "employment_status": "0013003,0013006",
    },
    "20250109005400110119": {
        "employment_status": "0013001",
    },
    "20250123005400110377": {
        "employment_status": "0013010",
    },
    "20250123005400110395": {
        "employment_status": "0013010",
    },
    "20250211005400110419": {
        "employment_status": "0013010",
    },
    "20250212005400110420": {
        "employment_status": "0013010",
    },
    "20250218005400210447": {
        "employment_status": "0013003,0013006",
    },
    "20250316005400210634": {
        "employment_status": "0013010",
    },
    "20250424005400210720": {
        "employment_status": "0013003",
    },
    "20250514005400110812": {
        "employment_status": "0013001,0013002,0013004",
    },
    "20250612005400110912": {
        "employment_status": "0013003,0013006",
    },
    "20250612005400110913": {
        "employment_status": "0013001",
    },
    "20250620005400111085": {
        "employment_status": "0013001",
    },
    "20250623005400111115": {
        "employment_status": "0013001,0013002,0013004",
    },
    "20250715005400211255": {
        "employment_status": "0013001,0013002,0013004",
    },
    "20250908005400211676": {
        "employment_status": "0013002,0013006",
    },

    # --- education_unknown only (24건) ---
    "20250107005400110063": {
        "education_status": "0049010",
    },
    "20250109005400110127": {
        "education_status": "0049005,0049006,0049007,0049008",
    },
    "20250109005400110128": {
        "education_status": "0049002,0049003,0049004,0049005,0049006,0049007,0049008",
    },
    "20250113005400110179": {
        "education_status": "0049006",
    },
    "20250114005400110232": {
        "education_status": "0049010",
    },
    "20250211005400110416": {
        "education_status": "0049010",
    },
    "20250227005400110566": {
        "education_status": "0049007,0049008",
    },
    "20250304005400210583": {
        "education_status": "0049005,0049006",
    },
    "20250304005400210588": {
        "education_status": "0049007,0049008",
    },
    "20250331005400110677": {
        "education_status": "0049001,0049002,0049003,0049004,0049005,0049006,0049007,0049008",
    },
    "20250618005400111018": {
        "education_status": "0049010",
    },
    "20250618005400111021": {
        "education_status": "0049010",
    },
    "20250618005400111025": {
        "education_status": "0049010",
    },
    "20250618005400111026": {
        "education_status": "0049010",
    },
    "20250618005400111029": {
        "education_status": "0049010",
    },
    "20250618005400111037": {
        "education_status": "0049010",
    },
    "20250618005400111038": {
        "education_status": "0049010",
    },
    "20250618005400111039": {
        "education_status": "0049010",
    },
    "20250618005400111040": {
        "education_status": "0049010",
    },
    "20250618005400111042": {
        "education_status": "0049010",
    },
    "20250620005400111082": {
        "education_status": "0049005,0049006,0049007,0049008",
    },
    "20250626005400111137": {
        "education_status": "0049001,0049002,0049003,0049004",
    },
    "20250717005400211358": {
        "education_status": "0049007,0049008",
    },
    "20251124005400211938": {
        "education_status": "0049010",
    },

    # --- education_gap only (12건) ---
    "20250110005400110148": {
        "education_status": "0049005,0049006,0049007",
    },
    "20250305005400110591": {
        "education_status": "0049004,0049005,0049006,0049007,0049008",
    },
    "20250305005400110592": {
        "education_status": "0049004,0049005,0049006,0049007,0049008",
    },
    "20250305005400110593": {
        "education_status": "0049004,0049005,0049006,0049007",
    },
    "20250315005400210616": {
        "education_status": "0049001,0049002,0049003,0049004,0049005,0049006,0049007,0049008",
    },
    "20250519005400210850": {
        "education_status": "0049004,0049005,0049006,0049007",
    },
    "20250610005400110900": {
        "education_status": "0049002,0049003,0049004,0049005",
    },
    "20250612005400110909": {
        "education_status": "0049005,0049006,0049007,0049008",
    },
    "20250616005400110940": {
        "education_status": "0049005,0049006,0049007,0049008",
    },
    "20250617005400110962": {
        "education_status": "0049004,0049005,0049006,0049007,0049008",
    },
    "20250619005400111077": {
        "education_status": "0049005,0049006,0049007,0049008",
    },
    "20250625005400111136": {
        "education_status": "0049004,0049005,0049006,0049007",
    },

    # --- education_unknown + education_gap (1건) ---
    # draft_education_target + gap_missing_codes 합집합
    "20250113005400110180": {
        "education_status": "0049001,0049002,0049003,0049004,0049005,0049006,0049007,0049008",
    },

    # --- education_unknown + job_unknown (10건) ---
    "20250110005400110147": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250123005400110393": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250211005400110413": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250212005400110425": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250212005400110426": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250609005400110889": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250612005400110919": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250618005400111024": {
        "education_status": "0049005,0049006",
        "employment_status": "0013010",
    },
    "20250619005400111066": {
        "education_status": "0049010",
        "employment_status": "0013010",
    },
    "20250621005400111098": {
        "education_status": "0049005",
        "employment_status": "0013010",
    },

    # --- job_unknown + education_gap (1건) ---
    # education: draft_education_target (gap codes already included)
    "20250624005400111124": {
        "education_status": "0049002,0049003,0049004,0049005,0049006,0049007,0049008",
        "employment_status": "0013001,0013003",
    },
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
