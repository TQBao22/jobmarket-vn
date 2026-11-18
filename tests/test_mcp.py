"""MCP server 2026-07-28 (`docs/research/mcp-spec.md`): gửi từng dòng JSON-RPC vào `server.handle`, kiểm response."""
import json
import os
import subprocess
import sys

import pytest

from jobmarket import db, query
from jobmarket.mcp import server
from jobmarket.mcp import tools as mcp_tools
from test_query import TODAY, _db

META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}


def call(line, tools=None):
    out = server.handle(line if isinstance(line, str) else json.dumps(line), tools or {})
    return None if out is None else json.loads(out)


def req(method, params=None, id_=1, meta=META):
    p = dict(params or {})
    if meta is not None:
        p["_meta"] = meta
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": p}


# ---- giao thức (Task 3) ----

def test_parse_error_has_no_id():
    r = call("{không phải json")
    assert r["error"]["code"] == -32700 and "id" not in r


def test_unknown_method():
    r = call(req("khong/co", id_=7))
    assert r["id"] == 7 and r["error"]["code"] == -32601


def test_notification_gets_no_response():
    assert call({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}}) is None


def test_request_without_method_is_invalid_request():
    assert call({"jsonrpc": "2.0", "id": 1})["error"]["code"] == -32600


def test_discover_returns_version_capabilities_and_cache_fields():
    r = call(req("server/discover", id_="server-discover-probe-1"))
    res = r["result"]
    assert r["id"] == "server-discover-probe-1"
    assert res["supportedVersions"] == ["2026-07-28"] and "tools" in res["capabilities"]
    assert res["resultType"] == "complete" and res["cacheScope"] in ("public", "private") and res["ttlMs"] >= 0
    assert res["_meta"]["io.modelcontextprotocol/serverInfo"]["name"]


@pytest.mark.parametrize("meta", [None, {}, {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}])
def test_missing_meta_fields_is_invalid_params(meta):
    assert call(req("tools/list", meta=meta))["error"]["code"] == -32602


def test_wrong_protocol_version_is_unsupported_version():
    r = call(req("tools/list", meta={**META, "io.modelcontextprotocol/protocolVersion": "2025-11-25"}))
    assert r["error"]["code"] == -32022
    assert r["error"]["data"] == {"supported": ["2026-07-28"], "requested": "2025-11-25"}


def test_initialize_is_not_supported_and_names_version():
    r = call({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}})
    assert r["error"]["code"] == -32601 and "2026-07-28" in r["error"]["message"]


# ---- tools (Task 4) ----

@pytest.fixture
def db_tools(tmp_path, monkeypatch):
    _db(tmp_path, [
        ("a", "2026-10-01", "2026-12-01", ["Python", "Docker"]),
        ("b", "2026-11-05", "", ["Python", "SQL"]),
        ("c", "2026-11-10", "2026-11-01", ["Python", "Kubernetes"]),  # đã hết hạn
    ]).close()
    monkeypatch.setenv("JOBMARKET_DB", str(tmp_path / "t.db"))
    return mcp_tools.make_tools(today=lambda: TODAY), db.connect(tmp_path / "t.db")


def tool_call(tools, name, arguments, id_=1):
    return call(req("tools/call", {"name": name, "arguments": arguments}, id_), tools)


def payload(r):
    res = r["result"]
    assert res["isError"] is False and res["resultType"] == "complete", r
    assert json.loads(res["content"][0]["text"]) == res["structuredContent"]
    return res["structuredContent"]


def tool_error(r) -> str:
    assert r["result"]["isError"] is True, r
    return r["result"]["content"][0]["text"]


def test_tools_list_returns_three_readonly_tools(db_tools):
    tools, _ = db_tools
    res = call(req("tools/list"), tools)["result"]
    assert res["resultType"] == "complete" and res["ttlMs"] >= 0 and res["cacheScope"] in ("public", "private")
    listed = {t["name"]: t for t in res["tools"]}
    assert list(listed) == ["top_skills", "search_jobs", "match_skills"]  # thứ tự cố định
    assert all(t["description"] and t["inputSchema"]["type"] == "object" for t in listed.values())
    assert all(t["annotations"]["readOnlyHint"] is True for t in listed.values())
    assert listed["match_skills"]["inputSchema"]["required"] == ["skills"]


def test_top_skills_matches_query(db_tools):
    tools, conn = db_tools
    assert payload(tool_call(tools, "top_skills", {"limit": 2})) == query.top_skills(conn, None, 2)


def test_top_skills_unknown_month_is_tool_error(db_tools):
    tools, _ = db_tools
    assert "2020-01" in tool_error(tool_call(tools, "top_skills", {"month": "2020-01"}))


def test_search_jobs_filters_by_skill_and_open(db_tools):
    tools, _ = db_tools
    out = payload(tool_call(tools, "search_jobs", {"skill": "python"}))
    assert out["total"] == 2 and all("Python" in j["skills"] for j in out["jobs"])


def test_match_skills_returns_missing(db_tools):
    tools, conn = db_tools
    out = payload(tool_call(tools, "match_skills", {"skills": ["Python"], "top_k": 5}))
    assert out == {"matches": query.match(conn, ["Python"], 5, TODAY)}
    assert out["matches"][0]["missing"]


def test_match_skills_empty_list_is_tool_error(db_tools):
    tools, _ = db_tools
    tool_error(tool_call(tools, "match_skills", {"skills": [" "]}))


@pytest.mark.parametrize("bad", ["10", -1, 51, True, 2.5])
def test_limit_wrong_value_is_tool_error_naming_param(db_tools, bad):
    tools, _ = db_tools
    assert "limit" in tool_error(tool_call(tools, "top_skills", {"limit": bad}))


def test_skills_must_be_list_of_strings(db_tools):
    tools, _ = db_tools
    assert "skills" in tool_error(tool_call(tools, "match_skills", {"skills": "Python"}))


def test_unknown_tool_is_invalid_params(db_tools):
    tools, _ = db_tools
    assert tool_call(tools, "xoa_db", {})["error"]["code"] == -32602


def test_arguments_not_object_is_invalid_params(db_tools):
    tools, _ = db_tools
    assert call(req("tools/call", {"name": "top_skills", "arguments": [1]}), tools)["error"]["code"] == -32602


def test_missing_db_is_tool_error_and_server_continues(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBMARKET_DB", str(tmp_path / "khong-co.db"))
    tools = mcp_tools.make_tools(today=lambda: TODAY)
    assert "DB" in tool_error(tool_call(tools, "top_skills", {}))
    assert "result" in call(req("tools/list", id_=2), tools)


def test_stdio_roundtrip_utf8(db_tools):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}  # như Claude Code khởi động server
    env["PYTHONPATH"] = "src"
    reqs = [req("server/discover", id_="p"),
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": "x"}},
            req("tools/call", {"name": "top_skills", "arguments": {"month": "1999-01"}}, id_=2)]
    p = subprocess.run([sys.executable, "-m", "jobmarket.mcp"], input="\n".join(json.dumps(r) for r in reqs) + "\n",
                       capture_output=True, env=env, encoding="utf-8", timeout=30)
    lines = p.stdout.splitlines()
    assert len(lines) == 2 and "Traceback" not in p.stderr  # notification không có dòng trả lời
    assert "tháng" in json.loads(lines[1])["result"]["content"][0]["text"]  # tiếng Việt qua stdout nguyên vẹn


def test_deeply_nested_json_is_parse_error_not_crash():
    assert call("[" * 100000)["error"]["code"] == -32700


def test_invalid_utf8_on_stdin_does_not_kill_server():
    env = {**os.environ, "PYTHONPATH": "src"}
    good = json.dumps(req("server/discover", id_=2)).encode()
    p = subprocess.run([sys.executable, "-m", "jobmarket.mcp"], input=b"\xff\xfe\n" + good + b"\n",
                       capture_output=True, env=env, timeout=30)
    assert b"Traceback" not in p.stderr
    assert json.loads(p.stdout.decode("utf-8").splitlines()[-1])["id"] == 2  # vẫn trả lời request sau dòng hỏng
