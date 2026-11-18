# API local (v3)

BE: FastAPI tại `http://localhost:8000`, mọi route có tiền tố `/api`. FE (Vite, `http://localhost:5173`) gọi qua proxy `/api` → `:8000`, nên FE chỉ dùng đường dẫn tương đối `/api/...`. Chỉ chạy trên máy cá nhân, không deploy (ADR 0004).

Mọi dữ liệu kỹ năng đều đã chuẩn hoá bằng `normalize/aliases.csv`. Kỹ năng của JD lấy từ bảng `extractions` với model `claude-haiku-5-5`, prompt `v1` (chất lượng tốt nhất hiện có, `eval/RESULTS.md`).

"JD đang mở": `valid_through` rỗng hoặc ≥ ngày hôm nay.

## `GET /api/health`
```json
{"status": "ok", "jobs": 128, "ollama": true, "cv_model": "qwen3:8b"}
```
`ollama`: Ollama có trả lời ở `http://localhost:11434` không (timeout 2 giây). `jobs`: số JD trong DB.

## `GET /api/skills/top?month=2026-11&limit=20`
`month` tuỳ chọn (`YYYY-MM`, theo `date_posted`); bỏ trống = mọi tháng. `limit` mặc định 20, tối đa 100.
```json
{
  "months": ["2026-10", "2026-11"],
  "jd_total": 51,
  "skills": [{"skill": "Python", "jd_count": 34, "share": 0.667}]
}
```
`share = jd_count / jd_total`. Sắp xếp `jd_count` giảm dần, rồi `skill` tăng dần. `month` không có trong dữ liệu → 404.

## `GET /api/jobs?skill=Docker&open_only=true&limit=50`
`skill` tuỳ chọn, so khớp sau chuẩn hoá, không phân biệt hoa thường. `open_only` mặc định `true`. `limit` mặc định 50, tối đa 200. Sắp xếp `date_posted` mới nhất trước.
```json
{
  "total": 12,
  "jobs": [{
    "url": "https://itviec.com/viec-lam-it/...", "title": "AI Engineer", "company": "X",
    "date_posted": "2026-11-10", "valid_through": "2026-12-10", "skills": ["Python", "Docker"]
  }]
}
```
`total`: số JD khớp trước khi cắt `limit`. Không trả nội dung mô tả JD.

## `POST /api/match`
`multipart/form-data`: `file` (CV `.pdf` hoặc `.txt`, ≤ 5 MB), `top_k` (tuỳ chọn, mặc định 10, tối đa 50).
```json
{
  "model": "qwen3:8b",
  "cv_skills": ["Python", "PyTorch", "SQL"],
  "matches": [{
    "url": "...", "title": "...", "company": "...", "score": 0.62,
    "matched": ["Python", "SQL"], "missing": ["Docker", "Kubernetes"]
  }]
}
```
- Trích kỹ năng CV bằng model local qua Ollama (`extract/local.py`, prompt `extract/prompts/cv_v1.txt`), rồi chuẩn hoá.
- Chỉ xét JD đang mở. `score` = tổng trọng số kỹ năng JD có trong CV / tổng trọng số mọi kỹ năng của JD; trọng số kỹ năng `s` = `ln(N / df(s)) + 1` (N = số JD đang mở, df = số JD đang mở có `s`), nên kỹ năng hiếm nặng hơn Python. JD không có kỹ năng nào bị bỏ qua.
- `matched`, `missing`: tên chuẩn, sắp theo trọng số giảm dần. Sắp `matches` theo `score` giảm dần.
- CV chỉ xử lý trong bộ nhớ: không ghi file, DB hay log; không lưu vào `llm_calls`.
- Lỗi: file sai định dạng hoặc quá lớn → 422; PDF không có chữ (ảnh scan) → 422 kèm thông báo; Ollama không chạy → 503.

## Lỗi
Mọi lỗi trả `{"detail": "<thông báo tiếng Việt>"}` với mã HTTP tương ứng.
