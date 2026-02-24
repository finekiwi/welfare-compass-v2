"""MCP rewrite_query 도구."""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)

try:
    from llm.agents.tools.rewrite_query import rewrite_query
except ImportError:
    rewrite_query = None
    logger.error("rewrite_query import 실패 — llm.agents.tools.rewrite_query 경로 확인 필요")
except Exception:
    rewrite_query = None
    logger.error("rewrite_query 초기화 실패", exc_info=True)


def rewrite_query_tool(query: str) -> str:
    """
    질의 리라이트.

    현재는 기존 에이전트 도구 구현을 그대로 재사용한다.
    """
    if not query:
        return ""

    if rewrite_query is None:
        return query

    try:
        return rewrite_query.invoke(query)
    except Exception:
        # 리라이터 실패 시 원문 그대로 전달
        logger.error("rewrite_query 실행 실패", exc_info=True)
        return query
