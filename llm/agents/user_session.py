"""
사용자 세션 store (멀티턴 사용자 정보 유지)

agent.py와 tools 양쪽에서 import할 수 있도록 독립 모듈로 분리.
순환 의존 방지: 이 모듈은 agent.py 또는 tools를 import하지 않는다.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_user_info_store: dict[str, dict] = {}
_user_info_store_lock = threading.Lock()
_current_thread_id = threading.local()  # run_agent()에서 세팅, tools에서 읽기

# 서비스 범위 외 사용자에게 안내할 대안 서비스 (tools + 프롬프트 단일 출처)
OUT_OF_SCOPE_SERVICES = "복지로(bokjiro.go.kr), 정부24(gov.kr), 129 복지상담전화"
OUT_OF_SCOPE_SERVICES_BULLET = (
    "   - 복지로(bokjiro.go.kr) — 전 연령 복지 정보 통합\n"
    "   - 정부24(gov.kr) — 정부 지원 서비스 검색\n"
    "   - 129 복지상담전화 — 보건복지부 상담 콜센터"
)

_USER_INFO_LABEL = {
    "age": "나이",
    "district": "거주지",
    "employment_status": "취업상태",
    "income_level": "연소득(만원)",
    "housing_type": "주거형태",
    "household_size": "가구원수",
}


def merge_user_info(thread_id: str, new_info: dict) -> None:
    """extract_info 결과를 store에 누적. None은 기존값을 유지한다."""
    with _user_info_store_lock:
        existing = _user_info_store.setdefault(thread_id, {})
        for k, v in new_info.items():
            if v is not None:
                existing[k] = v
    logger.debug("[merge_user_info] thread_id=%r store=%r", thread_id, get_user_info(thread_id))


def get_user_info(thread_id: str) -> dict:
    with _user_info_store_lock:
        return dict(_user_info_store.get(thread_id, {}))


def clear_user_info(thread_id: str) -> None:
    with _user_info_store_lock:
        _user_info_store.pop(thread_id, None)
