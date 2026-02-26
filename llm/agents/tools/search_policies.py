"""search_policies tool with backend adapter."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from .search_backend import DEFAULT_TOP_K, get_search_backend, normalize_top_k

logger = logging.getLogger(__name__)


def _shorten(text: str, limit: int = 180) -> str:
    """Shorten text for compact orchestrator output."""
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit - 3]}..."


def _format_for_orchestrator(result: dict[str, Any]) -> str:
    """Format backend payload to an LLM-friendly text block."""
    policies = result.get("policies") or []
    if not policies:
        return "검색 결과 없음"

    original_query = result.get("original_query", "")
    rewritten_query = result.get("rewritten_query", "")
    result_count = result.get("result_count", len(policies))

    lines = [
        f"원문 쿼리: {original_query}",
        f"변환 쿼리: {rewritten_query}",
        f"검색 결과: {result_count}건",
        "",
        "[정책 목록]",
    ]

    for idx, policy in enumerate(policies, start=1):
        policy_id = policy.get("policy_id") or "N/A"
        title = policy.get("title") or "제목 없음"
        category = policy.get("category") or "미분류"
        region = policy.get("district") or "정보 없음"
        apply_url = policy.get("apply_url") or ""
        description = _shorten(policy.get("description", ""))

        min_age = policy.get("age_min", 0)
        max_age = policy.get("age_max", 99)
        age_text = f"{min_age}~{max_age}세"

        lines.append(f"{idx}. {title} ({policy_id})")
        lines.append(f"   - 카테고리: {category} | 지역: {region} | 나이: {age_text}")
        if description:
            lines.append(f"   - 설명: {description}")
        if apply_url:
            lines.append(f"   - 신청: {apply_url}")

    return "\n".join(lines)


@tool
def search_policies(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """Search policies via selected backend and return orchestrator-formatted text."""
    normalized_top_k = normalize_top_k(top_k)
    backend = get_search_backend()

    try:
        result = backend.search(query=query, top_k=normalized_top_k)
    except NotImplementedError:
        logger.error("Search backend is not implemented for current configuration.")
        return "검색 백엔드가 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요."
    except Exception:
        logger.exception("Policy search backend call failed.")
        return "검색 중 오류가 발생했습니다"

    return _format_for_orchestrator(result)
