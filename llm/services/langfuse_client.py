from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langfuse.langchain import CallbackHandler

logger = logging.getLogger(__name__)

_LANGFUSE_AVAILABLE: bool | None = None  # None=미확인, True=사용 가능, False=import 실패


def _is_langfuse_enabled() -> bool:
    """환경변수 설정 여부 확인 (캐시 없음 — 런타임 변경 반영)."""
    return bool(os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"))


def get_langfuse_handler() -> "CallbackHandler | None":
    """
    LangFuse CallbackHandler 생성.

    환경변수(LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY)가 없으면 None 반환 (graceful degradation).
    import 실패 시 이후 호출은 재시도하지 않습니다.

    session_id / user_id는 langfuse_session()으로 전파하세요.

    Returns:
        CallbackHandler | None
    """
    global _LANGFUSE_AVAILABLE
    if not _is_langfuse_enabled():
        return None
    if _LANGFUSE_AVAILABLE is False:
        return None

    try:
        from langfuse.langchain import CallbackHandler

        _LANGFUSE_AVAILABLE = True
        return CallbackHandler()
    except ImportError:
        _LANGFUSE_AVAILABLE = False
        logger.warning("LangFuse 패키지 없음 — tracing 비활성화")
        return None
    except Exception:
        _LANGFUSE_AVAILABLE = False
        logger.warning("LangFuse CallbackHandler 생성 실패 — tracing 비활성화", exc_info=True)
        return None


@contextmanager
def langfuse_session(
    session_id: str | None = None,
    user_id: str | None = None,
):
    """
    LangFuse session_id / user_id를 하위 모든 trace에 전파하는 context manager.

    v4에서 session_id / user_id는 propagate_attributes()로 설정합니다.

    Usage:
        with langfuse_session(session_id="thread-123", user_id="user-456"):
            result = agent.invoke(inputs, config=config)
    """
    global _LANGFUSE_AVAILABLE
    if not (session_id or user_id) or not _is_langfuse_enabled():
        yield
        return
    if _LANGFUSE_AVAILABLE is False:
        yield
        return

    try:
        from langfuse import propagate_attributes

        with propagate_attributes(session_id=session_id, user_id=user_id):
            yield
    except ImportError:
        _LANGFUSE_AVAILABLE = False
        logger.warning("LangFuse 패키지 없음 — session 없이 진행")
        yield
    except Exception:
        logger.warning("LangFuse session 설정 실패 — session 없이 진행", exc_info=True)
        yield
