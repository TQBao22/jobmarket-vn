"""Ba tool chỉ đọc cho MCP server, gọi thẳng `jobmarket.query` (dùng chung với REST API).

Tham số sai giá trị/kiểu, tháng không có, thiếu DB, danh sách rỗng → `isError: true` để model đọc và gọi lại
(spec SEP-1303, `docs/research/mcp-spec.md` mục 4). Tool lạ là lỗi giao thức, xử lý ở `server.py`.
"""
import datetime
import json
import os
import sqlite3
from pathlib import Path
from typing import Callable

from jobmarket import query
from jobmarket.mcp.server import Tool

MAX_ROWS = 50
READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}


class ToolError(Exception):
    """Lỗi khi tool chạy: trả về cho model đọc (isError), không phải lỗi giao thức."""


def _int(args: dict, name: str, default: int) -> int:
    v = args.get(name, default)
    if type(v) is not int or not 1 <= v <= MAX_ROWS:  # type() để loại bool
        raise ToolError(f"{name} phải là số nguyên 1–{MAX_ROWS}")
    return v


def _str(args: dict, name: str) -> str | None:
    v = args.get(name)
    if v is not None and (not isinstance(v, str) or not v.strip()):
        raise ToolError(f"{name} phải là chuỗi không rỗng")
    return v


def _bool(args: dict, name: str, default: bool) -> bool:
    v = args.get(name, default)
    if not isinstance(v, bool):
        raise ToolError(f"{name} phải là true/false")
    return v


def _connect() -> sqlite3.Connection:
    path = Path(os.environ.get("JOBMARKET_DB", "data/jobs.db")).resolve()
    try:
        return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        raise ToolError(f"Không mở được DB {path}. Kiểm tra biến JOBMARKET_DB.")


def _run(fn: Callable[[sqlite3.Connection], dict]) -> dict:
    conn = _connect()
    try:
        return fn(conn)
    finally:
        conn.close()


def _tool(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
    """Bọc tool: ToolError → isError; kết quả → structuredContent + bản JSON trong content text (SHOULD của spec)."""
    def wrapped(args: dict) -> dict:
        try:
            data = fn(args)
        except ToolError as e:
            return {"content": [{"type": "text", "text": str(e)}], "isError": True}
        return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
                "structuredContent": data, "isError": False}
    return wrapped


def make_tools(today: Callable[[], str] = lambda: datetime.date.today().isoformat()) -> dict[str, Tool]:
    def top_skills(args: dict) -> dict:
        month, limit = _str(args, "month"), _int(args, "limit", 20)

        def q(conn):
            try:
                return query.top_skills(conn, month, limit)
            except query.NotFound:
                raise ToolError(f"Không có dữ liệu cho tháng {month}. Gọi lại không kèm month để xem các tháng có dữ liệu.")
        return _run(q)

    def search_jobs(args: dict) -> dict:
        skill, open_only, limit = _str(args, "skill"), _bool(args, "open_only", True), _int(args, "limit", 20)
        return _run(lambda conn: query.jobs(conn, skill, open_only, limit, today()))

    def match_skills(args: dict) -> dict:
        skills = args.get("skills")
        if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
            raise ToolError("skills phải là danh sách chuỗi")
        top_k = _int(args, "top_k", 10)

        def q(conn):
            if not [s for s in skills if s.strip()]:
                raise ToolError("Cần ít nhất một kỹ năng trong skills.")
            return {"matches": query.match(conn, skills, top_k, today())}
        return _run(q)

    limit = {"type": "integer", "minimum": 1, "maximum": MAX_ROWS}
    return {
        "top_skills": ({
            "name": "top_skills",
            "description": "Kỹ năng được tuyển nhiều nhất trong tin tuyển dụng AI/Data trên ITviec (Việt Nam). "
                           "Trả months (các tháng có dữ liệu), jd_total, và skills [{skill, jd_count, share}].",
            "inputSchema": {"type": "object", "properties": {
                "month": {"type": "string", "description": "Tháng đăng tin YYYY-MM; bỏ trống = mọi tháng"},
                "limit": {**limit, "default": 20}}},
            "annotations": READ_ONLY,
        }, _tool(top_skills)),
        "search_jobs": ({
            "name": "search_jobs",
            "description": "Tìm tin tuyển dụng AI/Data theo kỹ năng (đã chuẩn hoá tên, không phân biệt hoa thường), mới nhất trước. "
                           "Trả total (số tin khớp) và jobs [{url, title, company, date_posted, valid_through, skills}].",
            "inputSchema": {"type": "object", "properties": {
                "skill": {"type": "string", "description": "Tên kỹ năng, vd. Docker; bỏ trống = mọi tin"},
                "open_only": {"type": "boolean", "default": True, "description": "Chỉ tin còn hạn"},
                "limit": {**limit, "default": 20}}},
            "annotations": READ_ONLY,
        }, _tool(search_jobs)),
        "match_skills": ({
            "name": "match_skills",
            "description": "Xếp hạng tin tuyển dụng đang mở theo mức khớp với một bộ kỹ năng; kỹ năng hiếm có trọng số cao hơn. "
                           "Trả matches [{url, title, company, score 0–1, matched, missing}].",
            "inputSchema": {"type": "object", "required": ["skills"], "properties": {
                "skills": {"type": "array", "items": {"type": "string"}, "description": "Kỹ năng của ứng viên"},
                "top_k": {**limit, "default": 10}}},
            "annotations": READ_ONLY,
        }, _tool(match_skills)),
    }
