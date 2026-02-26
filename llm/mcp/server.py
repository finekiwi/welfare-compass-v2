"""복지나침반 MCP 서버 (stdio / sse)."""

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
    _host = "0.0.0.0" if _transport == "sse" else "127.0.0.1"
    mcp = FastMCP("welfare-rag", host=_host, port=_port)

    @mcp.tool()
    def search_policies(query: str, top_k: int = 10) -> dict:
        """
        정책 검색 통합 도구.
        내부적으로 rewrite -> BGE retrieve/rerank -> PostgreSQL 조회를 수행한다.
        """
        return search_policies_tool(query=query, top_k=top_k)
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

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        logger.info("MCP server starting: welfare-rag (SSE on port %d)", _port)
        mcp.run(transport="sse")
    else:
        logger.info("MCP server starting: welfare-rag (stdio)")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
