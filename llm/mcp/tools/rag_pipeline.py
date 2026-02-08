"""MCP RAG 파이프라인 도구."""

from __future__ import annotations

from .rewrite import rewrite_query_tool
from .search import search_policies_tool


def rag_pipeline_tool(query: str, top_k: int = 10) -> dict:
    """
    RAG 파이프라인 통합 도구.

    Steps:
    1) rewrite_query
    2) retrieve + rerank
    3) policy_id 기반 PostgreSQL 원문 조회
    """
    rewritten_query = rewrite_query_tool(query)
    policies = search_policies_tool(
        query=rewritten_query,
        top_k=top_k,
    )
    return {
        "original_query": query,
        "rewritten_query": rewritten_query,
        "result_count": len(policies),
        "policies": policies,
    }
