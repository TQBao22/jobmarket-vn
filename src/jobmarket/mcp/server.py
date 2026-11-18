"""MCP server tự viết: JSON-RPC 2.0 qua stdio, stdlib, không SDK, spec 2026-07-28 (stateless).

Quy tắc: `.claude/rules/mcp-server.md`; spec và nguồn: `docs/research/mcp-spec.md`.
`handle` xử lý một dòng, trả một dòng (hoặc None cho notification); `main` chỉ là vòng lặp stdin/stdout.
stdout chỉ chứa message JSON-RPC; log ra stderr.
"""
import json
import sys
from typing import Callable

PROTOCOL = "2026-07-28"
SERVER_INFO = {"name": "jobmarket-vn", "version": "0.1.0"}
TOOLS_TTL_MS = 3_600_000  # danh sách tool chỉ đổi khi sửa code

# Tool = (định nghĩa trả cho tools/list, hàm nhận arguments trả result của tools/call)
Tool = tuple[dict, Callable[[dict], dict]]

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603
UNSUPPORTED_VERSION = -32022
_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
_CAPS_KEY = "io.modelcontextprotocol/clientCapabilities"


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def _error(msg: dict, code: int, message: str, data: dict | None = None) -> str:
    err = {"code": code, "message": message, **({"data": data} if data is not None else {})}
    out = {"jsonrpc": "2.0", **({"id": msg["id"]} if "id" in msg else {}), "error": err}  # id không đọc được → bỏ trường
    return json.dumps(out, ensure_ascii=False)


def _check_meta(params: dict) -> None:
    meta = params.get("_meta")
    if not isinstance(meta, dict) or _VERSION_KEY not in meta or _CAPS_KEY not in meta:
        raise RpcError(INVALID_PARAMS, f"Thiếu _meta {_VERSION_KEY} hoặc {_CAPS_KEY}")
    if meta[_VERSION_KEY] != PROTOCOL:
        raise RpcError(UNSUPPORTED_VERSION, "Unsupported protocol version",
                       {"supported": [PROTOCOL], "requested": meta[_VERSION_KEY]})


def _dispatch(method: str, params: dict, tools: dict[str, Tool]) -> dict:
    if method == "initialize":  # server chỉ modern: nêu phiên bản hỗ trợ (SHOULD)
        raise RpcError(METHOD_NOT_FOUND, f"initialize không được hỗ trợ; phiên bản hỗ trợ: {PROTOCOL}")
    _check_meta(params)
    if method == "server/discover":
        return {"supportedVersions": [PROTOCOL], "capabilities": {"tools": {}},
                "ttlMs": TOOLS_TTL_MS, "cacheScope": "public"}
    if method == "tools/list":
        return {"tools": [schema for schema, _ in tools.values()], "ttlMs": TOOLS_TTL_MS, "cacheScope": "public"}
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments", {})
        if name not in tools:
            raise RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        if not isinstance(args, dict):
            raise RpcError(INVALID_PARAMS, "arguments phải là object")
        return tools[name][1](args)
    raise RpcError(METHOD_NOT_FOUND, f"Không có method: {method}")


def handle(line: str, tools: dict[str, Tool]) -> str | None:
    try:
        msg = json.loads(line)
    except (ValueError, RecursionError):  # JSON lồng quá sâu ném RecursionError, không phải ValueError
        return _error({}, PARSE_ERROR, "JSON không hợp lệ")
    if not isinstance(msg, dict):
        return _error({}, INVALID_REQUEST, "Message phải là object JSON-RPC")
    if "id" not in msg:  # notification (vd. notifications/cancelled): không trả lời
        return None
    if not isinstance(msg.get("method"), str):
        return _error(msg, INVALID_REQUEST, "Thiếu method")
    params = msg.get("params", {})
    if not isinstance(params, dict):
        return _error(msg, INVALID_PARAMS, "params phải là object")
    try:
        result = _dispatch(msg["method"], params, tools)
    except RpcError as e:
        return _error(msg, e.code, e.message, e.data)
    except Exception as e:  # lỗi không lường trước: báo lỗi, server chạy tiếp
        print(f"lỗi nội bộ: {e!r}", file=sys.stderr)
        return _error(msg, INTERNAL_ERROR, "Lỗi nội bộ của server")
    result = {"resultType": "complete", **result, "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO}}
    return json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}, ensure_ascii=False)


def main(tools: dict[str, Tool]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252, không in được tiếng Việt
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")  # byte hỏng → dòng đó lỗi parse, server chạy tiếp
    for line in sys.stdin:  # hết stdin → thoát (spec: SHOULD exit promptly)
        if not line.strip():
            continue
        out = handle(line, tools)
        if out is not None:
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
