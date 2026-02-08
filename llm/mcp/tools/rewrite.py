"""MCP rewrite_query 도구."""

from __future__ import annotations


def rewrite_query_tool(query: str) -> str:
    """
    질의 리라이트.

    현재는 기존 에이전트 도구 구현을 그대로 재사용한다.
    """
    if not query:
        return ""

    try:
        from llm.agents.tools.rewrite_query import rewrite_query

        return rewrite_query.invoke(query)
    except Exception:
        # 리라이터 실패 시 원문 그대로 전달
        return query

