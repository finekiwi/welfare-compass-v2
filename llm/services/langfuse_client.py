from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langfuse.langchain import CallbackHandler

logger = logging.getLogger(__name__)


def get_langfuse_handler(
    session_id: str | None = None,
    user_id: str | None = None,
) -> "CallbackHandler | None":
    """
    LangFuse CallbackHandler 생성.

    환경변수(LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY)가 없으면 None 반환 (graceful degradation).

    Args:
        session_id: LangFuse 세션 ID (trace 그룹핑용)
        user_id: LangFuse 사용자 ID

    Returns:
        CallbackHandler | None
    """
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")

    if not secret_key or not public_key:
        return None

    try:
        from langfuse.langchain import CallbackHandler

        # v4: secret_key/host/session_id/user_id는 환경변수에서 자동으로 읽힘
        # LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL
        return CallbackHandler()
    except Exception:
        logger.warning("LangFuse CallbackHandler 생성 실패 — tracing 비활성화", exc_info=True)
        return None
