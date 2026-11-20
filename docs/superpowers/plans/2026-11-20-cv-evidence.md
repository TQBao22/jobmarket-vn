# Khớp CV có bằng chứng — kế hoạch

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps dùng checkbox.

**Goal:** kỹ năng CV có bằng chứng project nặng hơn kỹ năng chỉ liệt kê, giao diện hiện câu trích.
**Architecture:** prompt + schema CV riêng qua `ollama_runner`; `query.match` thêm `listed`; API trả `cv_skills` có cấu trúc; FE hiện 2 nhóm.
**Tech Stack:** Python 3.12+, FastAPI, pytest; React + TS, vitest.
**Spec:** `docs/superpowers/specs/2026-11-20-cv-evidence-design.md`

## Global Constraints
- CV và câu trích không ghi file/DB/log.
- `LISTED_FACTOR = 0.5`; CV `num_predict` = 2048.
- Lệnh test: `$env:PYTHONPATH="src"; .venv\Scripts\python -m pytest`; FE: `cd frontend; npm test; npm run build`.

## Review Focus
1. Model trả câu trích không có trong CV → hạ `listed` (test ở Task 3).
2. Hai tên chuẩn hoá trùng nhau, một `used` một `listed` → một mục `used` (Task 3).
3. Output sai schema (thiếu `evidence`, giá trị lạ) → 503, không 500 (Task 3).
4. CV toàn `listed` → điểm = một nửa so với toàn `used` (Task 2).
5. `listed` khác hoa thường với tên JD vẫn nhận hệ số (Task 2).

---

### Task 1: `ollama_runner` nhận schema và num_predict
**Files:** Modify `src/jobmarket/extract/local.py`; Test `tests/test_extract_local.py`
**Produces:** `ollama_runner(model, post=_post, schema: dict = llm.SCHEMA, num_predict: int = MAX_OUTPUT)`
- [ ] Test `test_runner_custom_schema_and_budget`: body gửi đi có `format == schema` truyền vào và `options.num_predict == 2048`. Chạy → FAIL.
- [ ] Sửa → PASS. Commit `feat(extract): ollama_runner nhận schema và num_predict`.

### Task 2: `query.match` hạ trọng số kỹ năng chỉ liệt kê
**Files:** Modify `src/jobmarket/query.py`; Test `tests/test_query.py`
**Produces:** `match(conn, cv_skills, top_k, today, listed: Iterable[str] = ()) -> list[dict]`, hằng `LISTED_FACTOR = 0.5`. Output không đổi khoá.
- [ ] Test `test_match_listed_counts_half`: DB 1 JD `["Python","SQL"]`; `match(c, ["python","sql"], 10, T, listed=["PYTHON","Sql"])[0]["score"] == 0.5`; với `listed=["sql"]` điểm = (w_py + 0.5·w_sql)/(w_py+w_sql). Chạy → FAIL.
- [ ] Sửa → PASS, test cũ vẫn xanh. Commit `feat(query): kỹ năng chỉ liệt kê tính nửa trọng số`.

### Task 3: API CV có bằng chứng
**Files:** Create `src/jobmarket/extract/prompts/cv_v2.txt`; Modify `src/jobmarket/api/app.py`, `tests/test_api.py`, `docs/api.md`
**Consumes:** Task 1, Task 2.
**Produces:** `CV_SCHEMA`; `_cv_skills(out: str, text: str) -> list[dict] | None` (None = output hỏng); response `cv_skills: [{"skill","evidence","quote"}]`.
- [ ] Đổi `_runner_returning` trả `{"structured_output": {"skills": [...]}}`; test:
  - `test_match_txt`: `cv_skills` có cấu trúc, `matches` như cũ.
  - `test_cv_quote_not_in_text_downgraded`: quote bịa → `evidence == "listed"`, `quote == ""`.
  - `test_cv_duplicate_after_normalize_used_wins`.
  - `test_cv_bad_schema_503` (evidence `"maybe"`).
  - `test_listed_lowers_score`: cùng CV, Python `listed` → score JD b < 1.0.
  - `test_match_pdf_text_reaches_runner`: input = text CV (không còn tiền tố `### JD cv`).
  Chạy → FAIL.
- [ ] Viết `cv_v2.txt`, sửa app (`get_runner` dùng `CV_SCHEMA`, `num_predict=2048`) → PASS. Cập nhật `docs/api.md`. Commit `feat(api): kỹ năng CV kèm bằng chứng project`.

### Task 4: Giao diện
**Files:** Modify `frontend/src/api.ts`, `frontend/src/views/MatchCv.tsx`, `frontend/src/App.test.tsx`
**Consumes:** response Task 3.
- [ ] Sửa test "gửi multipart…": `cv_skills` có cấu trúc; thấy nhóm "Có trong project/kinh nghiệm", "Chỉ liệt kê", câu trích, chip "✓ SQL (chỉ liệt kê)". `npm test` → FAIL.
- [ ] Sửa types + view → `npm test`, `npm run build` xanh. Commit `feat(frontend): hiện bằng chứng kỹ năng CV`.

### Task 5: Chạy tay
- [ ] `scripts\run_local.ps1`, khớp 1 CV thật; ghi số kỹ năng used/listed, số câu trích bị hạ, thời gian.
