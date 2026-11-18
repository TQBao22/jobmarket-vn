"""Chạy: python -m jobmarket.mcp (DB: biến JOBMARKET_DB, mặc định data/jobs.db)."""
from jobmarket.mcp import server, tools

server.main(tools.make_tools())
