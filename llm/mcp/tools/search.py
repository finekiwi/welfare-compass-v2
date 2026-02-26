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
CANDIDATE_MULTIPLIER = 4
MIN_CANDIDATE_K = 8
_BACKEND: Optional[Callable[..., Any]] = None
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


def _run_bm25_docs(query: str, top_k: int) -> list[Any]:
    """BM25 보강 검색 결과 문서 반환."""
    try:
        parsed = int(top_k)
    except (TypeError, ValueError):
        parsed = DEFAULT_TOP_K
    top_k = min(max(1, parsed), MAX_TOP_K)

    try:
        from llm.embeddings.bm25_retriever import search_policies_bm25
    except ModuleNotFoundError:
        from embeddings.bm25_retriever import search_policies_bm25

    try:
        # stdout 오염 방지: MCP stdio 프로토콜 보호
        with contextlib.redirect_stdout(sys.stderr):
            docs = search_policies_bm25(query, k=top_k)
    except Exception:
        logger.error("BM25 검색 실패", exc_info=True)
        return []

    return list(docs or [])


def _extract_policy_id(metadata: dict[str, Any]) -> str:
    """메타데이터에서 policy_id 추출 (신/구 키 호환)."""
    return (metadata.get("plcyNo") or metadata.get("policy_id") or "").strip()


def _extract_policy_ids(docs: list[Any]) -> list[str]:
    """검색 문서에서 policy_id(plcyNo) 순서 보존 추출."""
    ids: list[str] = []
    seen = set()
    for doc in docs:
        metadata = getattr(doc, "metadata", {}) or {}
        policy_id = _extract_policy_id(metadata)
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



def _doc_to_fallback(doc: Any) -> dict:
    """PostgreSQL 조회 실패 시 retriever 메타데이터 기반 fallback."""
    metadata = getattr(doc, "metadata", {}) or {}
    page_content = getattr(doc, "page_content", "") or ""
    title = metadata.get("plcyNm", "")
    description = page_content[:1200]
    support_content = metadata.get("plcySprtCn", "")

    return {
        "policy_id": _extract_policy_id(metadata),
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


def _get_db_connection():
    """psycopg2 연결 생성 (환경변수 기반)."""
    import psycopg2

    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "welfare"),
        user=os.environ.get("DB_USER", "welfare_user"),
        password=os.environ.get("DB_PASSWORD", "welfare1234"),
    )


_POLICY_COLUMNS = [
    "policy_id", "title", "description", "support_content",
    "apply_method", "apply_url", "district", "category", "subcategory",
    "age_min", "age_max", "income_level",
    "apply_start_date", "apply_end_date",
    "business_start_date", "business_end_date",
]


def _row_to_dict(row: tuple) -> dict:
    """SQL 결과 row → MCP 응답 dict."""
    d = dict(zip(_POLICY_COLUMNS, row))
    title = d.get("title") or ""
    description = d.get("description") or ""
    support_content = d.get("support_content") or ""
    apply_method = d.get("apply_method") or ""

    return {
        "policy_id": d["policy_id"],
        "title": title,
        "description": description,
        "support_content": support_content,
        "apply_method": apply_method,
        "apply_url": d.get("apply_url") or "",
        "district": d.get("district"),
        "category": d.get("category") or "",
        "subcategory": d.get("subcategory") or "",
        "age_min": d.get("age_min"),
        "age_max": d.get("age_max"),
        "income_level": d.get("income_level") or "",
        "apply_start_date": _to_iso(d.get("apply_start_date")),
        "apply_end_date": _to_iso(d.get("apply_end_date")),
        "business_start_date": _to_iso(d.get("business_start_date")),
        "business_end_date": _to_iso(d.get("business_end_date")),
        "full_text": _compose_full_text(title, description, support_content, apply_method),
        "source": "postgres",
    }


def _fetch_policies_by_ids(policy_ids: list[str]) -> dict[str, dict]:
    """policy_id 리스트로 정책 원문 조회 (psycopg2 직접 쿼리)."""
    if not policy_ids:
        return {}

    try:
        cols = ", ".join(_POLICY_COLUMNS)
        placeholders = ", ".join(["%s"] * len(policy_ids))
        query = f"SELECT {cols} FROM policy WHERE policy_id IN ({placeholders})"

        conn = _get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, policy_ids)
                rows = cur.fetchall()
        finally:
            conn.close()

        return {row[0]: _row_to_dict(row) for row in rows}
    except Exception:
        logger.error("PostgreSQL 정책 조회 실패", exc_info=True)
        return {}


def _merge_docs_with_policy_records(docs: list[Any], policy_map: dict[str, dict]) -> list[dict]:
    """retriever 순서를 기준으로 PostgreSQL 정책 원문 병합."""
    merged: list[dict] = []
    added_ids = set()

    for doc in docs:
        metadata = getattr(doc, "metadata", {}) or {}
        policy_id = _extract_policy_id(metadata)
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


def _count_postgres_hits(policy_ids: list[str], policy_map: dict[str, dict]) -> int:
    """현재 후보 중 PostgreSQL 원문 조회가 가능한 정책 수."""
    return sum(1 for pid in policy_ids if pid in policy_map)


def _merge_unique_docs(primary_docs: list[Any], secondary_docs: list[Any], max_docs: int) -> list[Any]:
    """문서 리스트를 policy_id 기준으로 중복 제거하며 병합."""
    merged: list[Any] = []
    seen_ids: set[str] = set()

    for group in (primary_docs, secondary_docs):
        for doc in group:
            metadata = getattr(doc, "metadata", {}) or {}
            policy_id = _extract_policy_id(metadata)
            if policy_id and policy_id in seen_ids:
                continue
            if policy_id:
                seen_ids.add(policy_id)
            merged.append(doc)
            if len(merged) >= max_docs:
                return merged

    return merged


def _prioritize_postgres_records(records: list[dict], top_k: int) -> list[dict]:
    """PostgreSQL 원문(source=postgres)을 우선 반환."""
    postgres_records = [record for record in records if record.get("source") == "postgres"]
    fallback_records = [record for record in records if record.get("source") != "postgres"]
    return (postgres_records + fallback_records)[:top_k]


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
    candidate_k = min(MAX_TOP_K, max(top_k * CANDIDATE_MULTIPLIER, MIN_CANDIDATE_K))
    candidate_k = max(candidate_k, top_k)
    max_merged_docs = min(MAX_TOP_K * 2, candidate_k * 2)

    docs = _run_search_docs(query=rewritten_query, top_k=candidate_k)
    policy_ids = _extract_policy_ids(docs)
    policy_map = _fetch_policies_by_ids(policy_ids)
    postgres_hits = _count_postgres_hits(policy_ids, policy_map)

    # stale dense index 등으로 PostgreSQL 매칭이 부족하면 BM25(최신 raw 기준)로 후보 보강
    if postgres_hits < top_k:
        bm25_docs = _run_bm25_docs(query=rewritten_query, top_k=candidate_k)
        if bm25_docs:
            docs = _merge_unique_docs(
                primary_docs=bm25_docs,
                secondary_docs=docs,
                max_docs=max_merged_docs,
            )
            policy_ids = _extract_policy_ids(docs)
            policy_map = _fetch_policies_by_ids(policy_ids)

    merged = _merge_docs_with_policy_records(docs, policy_map)
    policies = _prioritize_postgres_records(merged, top_k=top_k)
    return {
        "original_query": original_query,
        "rewritten_query": rewritten_query,
        "result_count": len(policies),
        "policies": policies,
    }
