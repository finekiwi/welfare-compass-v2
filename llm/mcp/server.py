"""Welfare MCP server (stdio / sse)."""

from __future__ import annotations

import logging
import os
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

from llm.mcp.tools.search import search_policies_tool

load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger(__name__)

if FastMCP is not None:
    _transport = os.getenv("MCP_TRANSPORT", "stdio")
    _port = int(os.getenv("MCP_PORT", "8001"))
    _host = os.getenv("MCP_BIND_HOST", "0.0.0.0" if _transport == "sse" else "127.0.0.1")
    mcp = FastMCP("welfare-rag", host=_host, port=_port)

    @mcp.tool()
    def search_policies(query: str, top_k: int = 10) -> dict:
        """
        Policy search tool.
        Internally runs rewrite -> retrieve/rerank -> PostgreSQL lookup.
        """
        return search_policies_tool(query=query, top_k=top_k)
else:  # pragma: no cover
    mcp = None


def _warmup() -> None:
    """서버 시작 시 리트리버/리랭커를 미리 로드하여 첫 요청 지연 방지."""
    import time
    start = time.time()
    logger.info("🔥 워밍업 시작: 리트리버 + 리랭커 사전 로드...")
    try:
        search_policies_tool(query="워밍업", top_k=1)
        logger.info("✅ 워밍업 완료 (%.1fs)", time.time() - start)
    except Exception:
        logger.warning("⚠️ 워밍업 실패 (%.1fs) — 첫 요청에서 초기화됩니다.", time.time() - start, exc_info=True)


def main() -> None:
    if mcp is None:
        raise RuntimeError("mcp package is not installed. Run `uv sync` first.")

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        logger.info("MCP server starting: welfare-rag (SSE on port %d)", _port)
        _warmup()
        mcp.run(transport="sse")
    else:
        logger.info("MCP server starting: welfare-rag (stdio)")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
