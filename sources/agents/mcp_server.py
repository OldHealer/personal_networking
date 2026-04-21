"""
mcp_server.py

Точка входа для запуска MCP‑server (FastMCP) в режиме STDIO.

Tool'ы определены в `agents/mcp_app.py` (это важно: один источник правды для инструментов).

Запуск:
  poetry run python sources/agents/mcp_server.py
или:
  poetry run fastmcp run sources/agents/mcp_server.py
"""

from agents.mcp_app import mcp


if __name__ == "__main__":
    mcp.run()
