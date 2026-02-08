"""복지나침반 MCP 서버 (stdio)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)

from llm.mcp.tools.rag_pipeline import rag_pipeline_tool
from llm.mcp.tools.rewrite import rewrite_query_tool
from llm.mcp.tools.search import search_policies_tool

load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger(__name__)

if FastMCP is not None:
    mcp = FastMCP("welfare-rag")

    @mcp.tool()
    def rewrite_query(query: str) -> str:
        """검색 최적화를 위한 질의 리라이트."""
        return rewrite_query_tool(query)

    @mcp.tool()
    def search_policies(query: str, top_k: int = 10) -> list[dict]:
        """
        정책 검색 + BGE 리랭킹 + 정책 원문(PostgreSQL) 조회.
        """
        return search_policies_tool(query=query, top_k=top_k)

    @mcp.tool()
    def rag_pipeline(query: str, top_k: int = 10) -> dict:
        """
        통합 RAG 파이프라인.
        rewrite -> retrieve/BGE-rerank -> PostgreSQL 원문 조회.
        """
        return rag_pipeline_tool(query=query, top_k=top_k)
else:  # pragma: no cover
    mcp = None


def main() -> None:
    if mcp is None:
        raise RuntimeError("mcp 패키지가 설치되지 않았습니다. `uv sync` 후 실행하세요.")

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("MCP server starting: welfare-rag (stdio)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
