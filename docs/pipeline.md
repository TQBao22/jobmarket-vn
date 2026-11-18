# Pipeline — từ trang tuyển dụng tới dashboard

Mỗi bước đọc output của bước trước và ghi kết quả vào chỗ cố định, nên chạy lại một bước không cần chạy lại các bước trước nó.
Thuật ngữ: `GLOSSARY.md`. Thành phần và lưu trữ: `docs/architecture.md`.

```
[1 Crawl] → [2 Lọc PII] → [3 Trích kỹ năng] → [4 Chuẩn hoá] → [5 Tổng hợp] → [6 Dashboard]
                                   ↑                  ↑
                          [E Eval: gold set → P/R/F1 → eval/RESULTS.md]
```

| # | Bước | Đầu vào | Đầu ra | Module | Trạng thái |
|---|---|---|---|---|---|
| 1 | Crawl | sitemap của nguồn | `data/raw/<nguồn>/*.html` + `.meta.json`, bảng `jobs` | `crawl/jobposting.py` + `crawl/itviec.py` | xong (124 JD, chỉ ITviec — ADR 0002) |
| 2 | Lọc PII | `description` vừa parse | `description` đã che SĐT/email | `extract/pii.py` | xong, chạy bên trong bước 1 |
| 3 | Trích kỹ năng | bảng `jobs` | bảng `llm_calls`, `extractions` | `extract/llm.py` + `prompts/v1.txt` | xong: 124/124 JD (123 nội dung khác nhau), 7 lần gọi, 0 lỗi |
| 4 | Chuẩn hoá | `extractions.skills` | tên chuẩn (tính lúc đọc) | `normalize/` + `normalize/aliases.csv` | xong (bảng alias bản đầu, tên chuẩn chọn tay) |
| 5 | Tổng hợp | `jobs` + kỹ năng đã chuẩn hoá | `data/public/skill_counts.csv` | `aggregate.py` | xong (124 JD, 727 kỹ năng khác nhau) |
| 6 | Dashboard | `data/public/skill_counts.csv` | trang Streamlit có URL công khai | `app.py` | đã deploy: https://jobmarket-vn-tndk7vgqeiu5zqkfkxpwrw.streamlit.app/ |
| E | Eval | `data/gold/labels.jsonl` + lần trích trên gold set | 1 dòng trong `eval/RESULTS.md` | `gold.py`, `evaluate.py`, skill `run-eval` | xong: 40/40 JD gold (nhãn do claude-opus-5-5 gán, chưa người duyệt); LLM F1 0,851 vs baseline 0,238 |

## 1. Crawl
- Lấy mọi URL trong sitemap, tải mỗi trang cách nhau ≥2 giây, lưu HTML gốc rồi mới parse. Chỉ lưu DB JD AI/Data: tiêu đề có từ khoá vai trò, hoặc mô tả có ≥3 thuật ngữ ML/Data khác nhau (`itviec.is_ai_data`). Lọc theo slug cũ bỏ sót JD có slug không chứa từ khoá.
- Parse khối JSON-LD `JobPosting` → `title, company, date_posted, valid_through, tags, description`.
- Chạy: `$env:PYTHONPATH="src"; .venv\Scripts\python -m jobmarket.crawl.itviec --limit 200`
- Chạy lại sẽ dùng lại HTML đã có (không tải lại), chỉ parse và ghi DB lại.

## 2. Lọc PII
- Regex che email → `[EMAIL]`, số điện thoại VN → `[SĐT]`. Chạy trước khi ghi DB, nên DB và LLM chỉ thấy bản đã che.
- Chưa che tên người (cần NER). Kiểm tay khi gán gold set; thấy tên người tuyển dụng thì thêm.

## 3. Trích kỹ năng
- Gom 20 JD một lô → một lần gọi `claude -p` (Haiku, schema JSON `[{jd_id, skills}]`). Cách gọi: `.claude/rules/llm-extraction.md`.
- Bỏ qua JD đã có kết quả cho cùng `(content_hash, model, prompt_version)` — đây chính là cache.
- Prompt nằm ở `src/jobmarket/extract/prompts/v<N>.txt`. Đổi nội dung prompt → tạo file `v<N+1>`, không sửa file cũ.
- Mỗi lô ghi một dòng `llm_calls` (chi phí quy đổi, token, độ trễ, lỗi); mỗi JD ghi một dòng `extractions`.
- Lô lỗi hoặc thiếu `jd_id` → ghi lỗi vào `llm_calls`, JD thiếu được trích lại ở lần chạy sau.
- Hạn mức: >20 JD (tức >1 lô) → hỏi người dùng trước. 123 JD = 7 lần gọi.
- Chạy: `$env:CLAUDE_BIN="<đường dẫn claude.exe>"; $env:PYTHONPATH="src"; .venv\Scripts\python -m jobmarket.extract.llm --limit 20`
- Đo được (2026-11-17, 123 JD, 7 lần gọi): tổng $0,098 quy đổi (~$0,80/1.000 JD), trung vị 39 giây/lô 20 JD, 0 lỗi, không chạm hạn mức gói.

## 4. Chuẩn hoá
- `aliases.csv` gồm hai cột `alias,canonical` (ví dụ `py,Python`, `scikit learn,scikit-learn`). So khớp sau khi hạ chữ thường và bỏ khoảng trắng thừa.
- Tên chuẩn ưu tiên nhãn ESCO; công cụ ESCO chưa có (LangChain, vLLM...) thì tự đặt.
- Kỹ năng thô chưa có trong bảng → giữ nguyên tên (đã gộp khoảng trắng). `unmapped()` liệt kê chúng để bổ sung bảng.
- Khớp đúng hoa thường trước, rồi mới không phân biệt hoa thường (tách `ReAct` khỏi `React`).
- Chuẩn hoá chạy **lúc đọc**, không ghi đè `extractions`: sửa bảng alias không cần gọi lại LLM.

Chạy: `python -m jobmarket.aggregate`

## 5. Tổng hợp
- Đếm số JD có mỗi kỹ năng chuẩn, theo nguồn và tháng đăng (`date_posted`).
- Chỉ xuất số đếm + link nguồn, **không xuất nội dung JD** (điều khoản ITviec §2.2). File này là thứ duy nhất được commit/đưa lên mạng.

## 6. Dashboard
- `streamlit run app.py` (test: `tests/test_app.py` dùng `AppTest`), chỉ đọc `data/public/skill_counts.csv`. Dùng skill `dataviz` khi vẽ biểu đồ.
- Deploy: Streamlit Community Cloud, nhánh `main`, Python 3.12 → https://jobmarket-vn-tndk7vgqeiu5zqkfkxpwrw.streamlit.app/ (công khai). Repo `TQBao22/jobmarket-vn` không chứa `data/raw/`, `jobs.db`, `tests/fixtures/itviec/`. Push lên `main` → app tự cập nhật. `Dockerfile` đóng gói cùng dashboard (chỉ `app.py` + `data/public/`) để chạy ở nơi khác; CI build và gọi `/_stcore/health`.

## E. Eval
- Gold set: 40 JD chọn cố định theo sha256(url) (`python -m jobmarket.gold init`), lưu `data/gold/labels.jsonl` (`{"url", "title", "skills"}`; `skills: null` = chưa gán). Không chép nội dung JD. Gán nhãn: `python -m jobmarket.gold show <n>` để đọc JD, sửa `skills` trong file.
- Chấm: `python -m jobmarket.evaluate --system llm|tags [--append]` `[--split dev|test|all]`.
- Chia dev/test (từ 2026-11-18): 20/20 cố định theo sha256("split:" + url). Chọn cấu hình (prompt, `think`, model teacher, ngưỡng router) bằng điểm **dev**; **test** chấm một lần khi chốt, tránh chọn cấu hình theo chính tập báo kết quả. 2 JD người duyệt đều ở test. Các dòng `RESULTS.md` trước ngày này chấm cả 40 JD (`all`).
- Nhãn hiện tại do claude-opus-5-5 gán theo yêu cầu người dùng (trường `annotator` mỗi dòng), không phải nhãn người: F1 đo mức đồng ý Haiku–Opus, cùng họ model nên có thể cao hơn thực tế. Người duyệt dòng nào thì đổi `annotator` thành `human`.
- Duyệt lần 1 (2026-11-17): 2/40 người duyệt (`human`); 38/40 do Sonnet 5.5 duyệt (`claude-opus-5-5+sonnet-5-5-review`): mỗi đề xuất thêm phải kèm câu trích nguyên văn, đã đối chiếu tự động với JD; kết quả 4 thêm, 1 xoá. Người duyệt thấy nhãn sẵn nên dễ đồng ý theo (anchoring): đây là kiểm tra lỗi rõ ràng, không thay được nhãn người.
- Lỗi LLM nhiều nhất trên gold (lần chấm 2026-11-17) là lệch tên (`S3`/`Amazon S3`, `Server-Sent Events`/`SSE`, `Vue.js`/`Vue`). Không sửa bảng alias theo lỗi trên gold; bổ sung alias chỉ từ JD ngoài gold.
- Rò rỉ đã biết: 8/40 JD gold nằm trong lô 20 JD đầu; bảng alias bản đầu lập từ output của lô này, và 2 JD gold (Nexlab, MB Bank) đã được xem khi kiểm tay. Prompt v1 không sửa theo chúng. Ghi vào ghi chú của dòng eval đầu tiên.
- JD trong gold set chỉ dùng để chấm, không làm nguyên liệu: viết prompt, ví dụ few-shot, ngưỡng router đều lấy từ JD ngoài gold set.
- Chấm sau chuẩn hoá ở cả hai phía; báo P, R, F1 micro. Baseline đầu tiên: thẻ ITviec (`jobs.tags`) chấm như một "model".
- Đổi prompt, model, bảng alias hoặc router → chạy skill `run-eval`.

## Đã chốt
- Chỉ crawl ITviec; gold set 40 JD, ~84 JD còn lại để phát triển prompt (ADR 0002).

## Còn mở (cần người dùng chốt)
1. **Cách gán gold set:** tự gán từ đầu, hay cho LLM gợi ý rồi sửa tay (nhanh hơn nhưng nhãn dễ thiên về LLM — phải ghi rõ trong bài viết).
