# Teacher `think` + MCP server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đo Qwen3-8B `think=true` trên 20 JD dev để chọn teacher v2, và viết MCP server stdio (3 tool) đạt tiêu chí v3.

**Architecture:** Phần A thêm cờ vào runner Ollama có sẵn, kết quả lưu dưới tên model riêng nên cache/eval hiện có dùng lại nguyên vẹn. Phần B là package `jobmarket.mcp`: một hàm thuần `handle(line) -> str | None` xử lý một message JSON-RPC, vòng lặp stdin/stdout mỏng bên ngoài; tool gọi thẳng `jobmarket.query`.

**Tech Stack:** Python ≥3.12 stdlib (`json`, `sys`, `sqlite3`, `urllib`), pytest, Ollama 0.40, Claude Code CLI.

**Spec:** `docs/superpowers/specs/2026-11-18-teacher-think-va-mcp-design.md`

## Global Constraints
- Không MCP SDK; stdout chỉ chứa message JSON-RPC, log ra stderr.
- DB mở `file:<path>?mode=ro`, đường dẫn từ `JOBMARKET_DB`, mặc định `data/jobs.db`.
- SQL chỉ qua `query.py`; tool không nhận SQL thô; `limit`/`top_k` ≤ 50.
- Lỗi giao thức → lỗi JSON-RPC (`code`, `message`); lỗi khi tool chạy → `result.isError: true`, thông báo tiếng Việt. Server chạy tiếp.
- Không chạy Claude trên JD; chạy model local không tốn hạn mức. Không chấm nửa test của gold.
- Không sửa dòng cũ `eval/RESULTS.md`. Commit trên nhánh feature khi `pytest` xanh; push/PR cần người dùng.
- Nhánh: Task 1, 6 trên `eval/teacher-think` (tách từ `main`); Task 2–5 trên `feat/mcp`.

## Review Focus
1. Output tiếng Việt qua stdout trên Windows (console cp1252) → phải ra UTF-8, không `UnicodeEncodeError` (test subprocess, Task 3).
2. Agent gửi `limit` dạng chuỗi `"10"` hoặc số âm → lỗi `-32602`, không crash (Task 4).
3. `match_skills` với danh sách rỗng → `isError` "Cần ít nhất một kỹ năng", không trả 10 JD điểm 0 (Task 4).
4. Notification (không có `id`) → không ghi gì ra stdout (Task 3).
5. File DB không tồn tại → `isError` "Không mở được DB …", server vẫn trả lời request sau (Task 4).

---

### Task 1: Cờ `--think` cho runner Ollama

**Files:**
- Modify: `src/jobmarket/extract/local.py`
- Test: `tests/test_extract_local.py`

**Interfaces:**
- Produces: `ollama_runner(model: str, post=_post, think: bool = False, num_predict: int | None = None)`; hằng `THINK_NUM_CTX = 12288`, `THINK_MAX_OUTPUT = 4096`. CLI: `--think`, `--num-predict N`; khi `--think`, kết quả lưu dưới model `f"{args.model}-think"`.

- [ ] **Step 1: Test hỏng** — `test_think_runner_requests_thinking_with_larger_budget`: body có `think is True`, `options.num_predict == THINK_MAX_OUTPUT`, `options.num_ctx == THINK_NUM_CTX`, vẫn có `format`. `test_num_predict_override`: `ollama_runner("m", post, think=True, num_predict=8192)` → `options.num_predict == 8192`. Test cũ (`think` False, `MAX_OUTPUT`) giữ nguyên.
- [ ] **Step 2:** `pytest tests/test_extract_local.py -q` → FAIL (`unexpected keyword 'think'`).
- [ ] **Step 3:** Thêm tham số; CLI truyền `store_model = f"{model}-think" if think else model` làm đối số `model` của `llm.extract` (runner vẫn gọi model gốc).
- [ ] **Step 4:** `pytest -q` → toàn bộ PASS.
- [ ] **Step 5:** Commit `feat(extract): cờ --think cho model local, lưu tách tên model`.

### Task 2: Ghi nhận phiên bản giao thức Claude Code gửi lên

**Files:**
- Create: `docs/research/mcp-spec.md`
- Modify: `.claude/rules/mcp-server.md` (dòng "Lỗi trả về…"), `CLAUDE.md` (ngoại lệ "làm tuần tự": FastAPI + FE + MCP song song v2, nhánh riêng, merge độc lập khi `pytest` xanh)

**Interfaces:**
- Produces: danh sách method server phải hỗ trợ + `protocolVersion` + hình dạng response `initialize`/`server/discover`, `tools/list`, `tools/call` (ghi trong `docs/research/mcp-spec.md`, Task 3 đọc).

- [ ] **Step 1:** Script tạm (scratchpad) ghi mọi dòng stdin ra file, không trả lời. Chạy `claude -p "ping" --mcp-config <cfg trỏ script> --strict-mcp-config --max-turns 1` một lần (1 lời gọi nhỏ, không JD). Kết quả: file có message đầu tiên Claude Code gửi.
- [ ] **Step 2:** Đọc spec đúng phiên bản đó trên modelcontextprotocol.io (skill `mattpocock-skills:research`); ghi `docs/research/mcp-spec.md`: version, method bắt buộc, schema `tools/list`/`tools/call`, mã lỗi, phân loại lỗi giao thức vs `isError`, nguồn từng ý.
- [ ] **Step 3:** Sửa 2 file quy tắc ở trên. Commit `docs: ghi nhận phiên bản MCP của Claude Code, cho MCP làm song song v2`.

### Task 3: Lõi JSON-RPC (`handle` + vòng lặp stdio)

**Files:**
- Create: `src/jobmarket/mcp/__init__.py`, `src/jobmarket/mcp/__main__.py`, `src/jobmarket/mcp/server.py`
- Test: `tests/test_mcp.py`

**Interfaces:**
- Consumes: method list + `protocolVersion` từ `docs/research/mcp-spec.md`.
- Produces: `handle(line: str, tools: dict[str, Tool]) -> str | None`; `Tool = (schema: dict, fn: Callable[[dict], dict])`; `main() -> None` (đặt `sys.stdout.reconfigure(encoding="utf-8")`, đọc từng dòng stdin, ghi response + `\n`, flush).

- [ ] **Step 1: Test hỏng:**
  - `test_handshake_returns_protocol_version_and_tools_capability` (method từ Task 2).
  - `test_tools_list_returns_registered_tools` (tool giả 1 cái).
  - `test_parse_error` → `error.code == -32700`, `id is None`.
  - `test_unknown_method` → `-32601`.
  - `test_notification_gets_no_response` → `handle(...) is None`.
  - `test_stdio_roundtrip_utf8`: subprocess `python -m jobmarket.mcp` (env `PYTHONIOENCODING` không đặt), gửi handshake + `tools/list`, stdout giải mã UTF-8 được, mỗi dòng là JSON, stderr không chứa traceback.
- [ ] **Step 2:** `pytest tests/test_mcp.py -q` → FAIL (`No module named jobmarket.mcp`).
- [ ] **Step 3:** Viết `handle`/`main`; `__main__.py` gọi `main()` với registry thật (Task 4 thêm tool; tới lúc đó registry rỗng).
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit `feat(mcp): lõi JSON-RPC qua stdio`.

### Task 4: Ba tool trên `query.py`

**Files:**
- Create: `src/jobmarket/mcp/tools.py`
- Modify: `src/jobmarket/mcp/__main__.py`
- Test: `tests/test_mcp.py` (DB tạm dựng như `tests/test_query.py`)

**Interfaces:**
- Consumes: `query.top_skills(conn, month, limit)`, `query.jobs(conn, skill, open_only, limit, today)`, `query.match(conn, cv_skills, top_k, today)`, `query.NotFound`.
- Produces: `TOOLS: dict[str, Tool]` với `top_skills {month?: str, limit?: int=20}`, `search_jobs {skill?: str, open_only?: bool=true, limit?: int=20}`, `match_skills {skills: list[str], top_k?: int=10}`; mỗi `fn` mở DB `mode=ro` mỗi lần gọi; result `content: [{"type": "text", "text": <json.dumps(..., ensure_ascii=False)>}]` (hình dạng chính xác theo `docs/research/mcp-spec.md`).

- [ ] **Step 1: Test hỏng** (qua `handle` + `tools/call`):
  - `test_top_skills_matches_query` — kết quả bằng `query.top_skills` trên cùng DB.
  - `test_top_skills_unknown_month_is_tool_error` → `result.isError is True`, text chứa "2020-01".
  - `test_search_jobs_filters_by_skill` — mọi JD trả về có skill đã chuẩn hoá.
  - `test_match_skills_returns_missing` — JD đầu có `missing` đúng như `query.match`.
  - `test_match_skills_empty_list_is_tool_error`.
  - `test_limit_wrong_type_is_invalid_params` (`"10"`, `-1`, `51`) → `-32602`.
  - `test_unknown_tool_is_invalid_params` → `-32602`.
  - `test_missing_db_is_tool_error_and_server_continues` (`JOBMARKET_DB` trỏ file không có; request sau vẫn trả lời).
- [ ] **Step 2:** `pytest tests/test_mcp.py -q` → FAIL.
- [ ] **Step 3:** Viết `tools.py`: kiểm kiểu bằng tay theo `inputSchema` (không thêm thư viện), `today = datetime.date.today().isoformat()`.
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit `feat(mcp): tool top_skills, search_jobs, match_skills`.

### Task 5: Kết nối Claude Code + 5 câu hỏi demo

**Files:**
- Create: `.mcp.json`, `docs/mcp-demo.md`
- Modify: `docs/architecture.md` (hàng `mcp/`), `CLAUDE.md` (dòng "Đang ở", lệnh chạy MCP), `README.md` (lộ trình v3)

**Interfaces:**
- Consumes: `python -m jobmarket.mcp` từ Task 3–4.

- [ ] **Step 1:** `.mcp.json`: server `jobmarket`, command `.venv/Scripts/python`, args `["-m", "jobmarket.mcp"]`, env `PYTHONPATH=src`. Kiểm: `claude mcp list` hiện `jobmarket` connected.
- [ ] **Step 2:** Soạn 5 câu hỏi (ít nhất 1 câu mỗi tool, 1 câu cần 2 tool). Đáp án tính bằng SQL/`query` trực tiếp trên DB thật, ghi ngày. **Người dùng duyệt 5 câu trước khi chạy demo.**
- [ ] **Step 3:** Hỏi Claude Code từng câu (5 lời gọi Claude, không JD); ghi câu trả lời + đúng/sai vào `docs/mcp-demo.md`. Đủ 5/5 → xong; sai → sửa mô tả tool/schema, tối đa 3 lần (quy tắc chung).
- [ ] **Step 4:** `pytest -q` → PASS. Commit `feat(mcp): kết nối Claude Code, 5 câu hỏi demo`.

### Task 6: Chạy teacher `think` trên dev và quyết định

**Files:**
- Modify: `eval/RESULTS.md` (thêm dòng), `docs/adr/0003-v2-teacher-model-mo.md`, `CLAUDE.md` (dòng "Đang ở")

**Interfaces:**
- Consumes: CLI Task 1.

- [ ] **Step 1:** Chạy nền ngay sau Task 1: `python -m jobmarket.extract.local --model qwen3:8b --think --gold dev`. Kiểm JD đầu: không lỗi `format`+`think`. Ghi tổng thời gian.
- [ ] **Step 2:** JD lỗi do cắt → chạy lại `--think --num-predict 8192 --gold dev` (cache bỏ qua JD đã xong).
- [ ] **Step 3:** `python -m jobmarket.evaluate --model qwen3:8b-think --split dev --append --note "think=true, <s/JD>, <số JD bị cắt>"`.
- [ ] **Step 4:** Quyết định theo quy tắc spec (ΔF1 ≥ 0,05 so với 0,573 và 88 JD × s/JD ≤ 8 giờ); ghi vào ADR 0003 mục Hệ quả, kèm số đo. Cập nhật "Đang ở".
- [ ] **Step 5:** `pytest -q` → PASS. Commit `eval: Qwen3-8B think trên gold dev, chọn teacher`.
