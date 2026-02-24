"""MCP search_policies 도구 (BGE-only: retrieve + rerank + PostgreSQL 원문 조회)."""

from __future__ import annotations

import contextlib
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Optional

from .rewrite import rewrite_query_tool

DEFAULT_TOP_K = 10
MAX_TOP_K = 20
_BACKEND: Optional[Callable[..., Any]] = None
_DJANGO_READY = False
logger = logging.getLogger(__name__)


def _ensure_paths() -> tuple[Path, Path]:
    """프로젝트/백엔드 루트 경로를 sys.path에 보장."""
    project_root = Path(__file__).resolve().parents[3]
    backend_root = project_root / "backend"

    project_root_str = str(project_root)
    backend_root_str = str(backend_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)

    return project_root, backend_root


def _load_backend() -> Callable[..., Any]:
    """BGE 검색 백엔드 lazy import."""
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND

    _ensure_paths()
    try:
        from llm.embeddings.ensemble_retriever_bge import ensemble_search_with_bge as bge_search
    except ModuleNotFoundError:
        # fallback: llm 디렉토리가 CWD인 실행 경로 호환
        from embeddings.ensemble_retriever_bge import ensemble_search_with_bge as bge_search

    _BACKEND = bge_search
    return _BACKEND


def _setup_django() -> bool:
    """Django ORM 사용 준비."""
    global _DJANGO_READY
    if _DJANGO_READY:
        return True

    try:
        _, _ = _ensure_paths()
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

        import django

        django.setup()
        _DJANGO_READY = True
        return True
    except Exception:
        logger.error("Django setup 실패", exc_info=True)
        return False


def _run_search_docs(query: str, top_k: int) -> list[Any]:
    """BGE retrieve + rerank 결과 문서 반환."""
    try:
        parsed = int(top_k)
    except (TypeError, ValueError):
        parsed = DEFAULT_TOP_K
    top_k = min(max(1, parsed), MAX_TOP_K)

    try:
        backend = _load_backend()
    except Exception:
        logger.error("BGE backend 로드 실패", exc_info=True)
        return []

    try:
        # stdout 오염 방지: MCP stdio 프로토콜 보호
        with contextlib.redirect_stdout(sys.stderr):
            docs = backend(
                query=query,
                top_k=top_k,
                return_metadata=False,
                verbose=False,
            )
    except Exception:
        logger.error("BGE 검색 실패", exc_info=True)
        return []

    return list(docs or [])


def _extract_policy_ids(docs: list[Any]) -> list[str]:
    """검색 문서에서 policy_id(plcyNo) 순서 보존 추출."""
    ids: list[str] = []
    seen = set()
    for doc in docs:
        metadata = getattr(doc, "metadata", {}) or {}
        policy_id = (metadata.get("plcyNo") or "").strip()
        if policy_id and policy_id not in seen:
            seen.add(policy_id)
            ids.append(policy_id)
    return ids


def _to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _compose_full_text(title: str, description: str, support_content: str, apply_method: str) -> str:
    parts = [
        title.strip(),
        description.strip(),
        support_content.strip(),
        apply_method.strip(),
    ]
    return "\n\n".join(part for part in parts if part)


def _policy_to_dict(policy: Any) -> dict:
    """Policy ORM 객체 -> MCP 응답 dict."""
    description = policy.description or ""
    support_content = policy.support_content or ""
    apply_method = policy.apply_method or ""
    title = policy.title or ""

    return {
        "policy_id": policy.policy_id,
        "title": title,
        "description": description,
        "support_content": support_content,
        "apply_method": apply_method,
        "apply_url": policy.apply_url or "",
        "district": policy.district,
        "category": policy.category or "",
        "subcategory": policy.subcategory or "",
        "age_min": policy.age_min,
        "age_max": policy.age_max,
        "income_level": policy.income_level or "",
        "apply_start_date": _to_iso(policy.apply_start_date),
        "apply_end_date": _to_iso(policy.apply_end_date),
        "business_start_date": _to_iso(policy.business_start_date),
        "business_end_date": _to_iso(policy.business_end_date),
        "full_text": _compose_full_text(title, description, support_content, apply_method),
        "source": "postgres",
    }


def _doc_to_fallback(doc: Any) -> dict:
    """PostgreSQL 조회 실패 시 retriever 메타데이터 기반 fallback."""
    metadata = getattr(doc, "metadata", {}) or {}
    page_content = getattr(doc, "page_content", "") or ""
    title = metadata.get("plcyNm", "")
    description = page_content[:1200]
    support_content = metadata.get("plcySprtCn", "")

    return {
        "policy_id": metadata.get("plcyNo", ""),
        "title": title,
        "description": description,
        "support_content": support_content,
        "apply_method": "",
        "apply_url": metadata.get("aplyUrlAddr", ""),
        "district": metadata.get("region", ""),
        "category": metadata.get("lclsfNm", ""),
        "subcategory": metadata.get("mclsfNm", ""),
        "age_min": metadata.get("minAge"),
        "age_max": metadata.get("maxAge"),
        "income_level": metadata.get("earnCndSeCd", ""),
        "apply_start_date": None,
        "apply_end_date": None,
        "business_start_date": None,
        "business_end_date": None,
        "full_text": _compose_full_text(title, description, support_content, ""),
        "source": "retriever_fallback",
    }


def _fetch_policies_by_ids(policy_ids: list[str]) -> dict[str, dict]:
    """policy_id 리스트로 정책 원문 조회."""
    if not policy_ids:
        return {}
    if not _setup_django():
        return {}

    try:
        from policies.models import Policy

        queryset = Policy.objects.filter(policy_id__in=policy_ids)
        return {policy.policy_id: _policy_to_dict(policy) for policy in queryset}
    except Exception:
        logger.error("PostgreSQL 정책 조회 실패", exc_info=True)
        return {}


def _merge_docs_with_policy_records(docs: list[Any], policy_map: dict[str, dict]) -> list[dict]:
    """retriever 순서를 기준으로 PostgreSQL 정책 원문 병합."""
    merged: list[dict] = []
    added_ids = set()

    for doc in docs:
        metadata = getattr(doc, "metadata", {}) or {}
        policy_id = (metadata.get("plcyNo") or "").strip()
        if not policy_id:
            merged.append(_doc_to_fallback(doc))
            continue
        if policy_id in added_ids:
            continue

        row = policy_map.get(policy_id)
        if row:
            row_copy = dict(row)
            row_copy["retrieval_score"] = metadata.get("score")
            row_copy["rerank_score"] = metadata.get("rerank_score")
            merged.append(row_copy)
        else:
            merged.append(_doc_to_fallback(doc))

        added_ids.add(policy_id)

    return merged


def search_policies_tool(query: str, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    """
    MCP 검색 도구.

    입력 쿼리를 내부에서 rewrite 후 BGE retrieve+rerank를 수행하고,
    policy_id로 PostgreSQL 원문 정책을 조회해 반환한다.
    """
    original_query = (query or "").strip()
    if not original_query:
        return {
            "original_query": "",
            "rewritten_query": "",
            "result_count": 0,
            "policies": [],
        }

    rewritten_query = rewrite_query_tool(original_query)
    rewritten_query = (rewritten_query or "").strip() or original_query

    try:
        parsed = int(top_k)
    except (TypeError, ValueError):
        parsed = DEFAULT_TOP_K
    top_k = min(max(1, parsed), MAX_TOP_K)

    docs = _run_search_docs(query=rewritten_query, top_k=top_k)
    policy_ids = _extract_policy_ids(docs)
    policy_map = _fetch_policies_by_ids(policy_ids)
    policies = _merge_docs_with_policy_records(docs, policy_map)[:top_k]
    return {
        "original_query": original_query,
        "rewritten_query": rewritten_query,
        "result_count": len(policies),
        "policies": policies,
    }
