# JobMarket VN

Dự án đọc tin tuyển dụng AI/Data trên ITviec, dùng LLM tách ra danh sách kỹ năng, gộp các tên gọi khác nhau của cùng một kỹ năng, rồi đếm xem thị trường đang cần gì.

Dashboard: https://jobmarket-vn-tndk7vgqeiu5zqkfkxpwrw.streamlit.app/

Đây là project cá nhân. Mỗi con số về chất lượng đều có lần đo ghi lại, mỗi quyết định kiến trúc có một ADR nêu lý do và số đo.

## Kết quả đo

Trích kỹ năng trên 40 tin tuyển dụng có nhãn sẵn (gold set), tính precision, recall, F1 sau khi chuẩn hoá tên kỹ năng. Toàn bộ các lần đo nằm trong [`eval/RESULTS.md`](eval/RESULTS.md).

| Cách trích | P | R | F1 | Chi phí / 1.000 JD |
|---|---|---|---|---|
| Thẻ kỹ năng ITviec tự gắn | 0,619 | 0,147 | 0,238 | 0 |
| Qwen3-1.7B chạy local, chưa fine-tune | 0,496 | 0,376 | 0,428 | 0 (GPU 4 GB) |
| Qwen3-8B chạy local, chưa fine-tune | 0,619 | 0,581 | 0,599 | 0 (GPU 4 GB) |
| Claude Haiku 5.5 | 0,895 | 0,813 | 0,852 | $0,80 (quy đổi giá API) |

Hạn chế cần biết khi đọc bảng:

- 38/40 tin trong gold set do Claude Opus gán nhãn và Claude Sonnet duyệt; người duyệt 2 tin. Haiku cùng họ model nên điểm của nó có thể cao hơn thực tế.
- 40 tin là ít. Chênh lệch dưới khoảng 0,05 F1 chưa đủ để kết luận.
- Từ 2026-11-18, gold set chia đôi cố định: 20 tin để thử cấu hình, 20 tin chỉ chấm khi đã chốt.

## Cách hoạt động

```
ITviec ──crawl──▶ HTML gốc ──parse + che email/SĐT──▶ SQLite
                                                        │
                       Claude Haiku (claude -p) ◀───────┤ trích kỹ năng, kết quả JSON theo schema
                       hoặc Qwen qua Ollama              │
                                                        ▼
              bảng alias ──▶ chuẩn hoá tên ──▶ đếm theo tháng ──▶ CSV công khai ──▶ Streamlit
```

- Crawl: đọc sitemap của ITviec, tôn trọng `robots.txt`, nghỉ ít nhất 2 giây giữa hai request, giữ tin có tiêu đề thuộc nhóm AI/Data. Chạy tự động mỗi Chủ nhật.
- Nội dung tin tuyển dụng chỉ nằm trên máy cá nhân. Repo và dashboard chỉ chứa số đếm và đường link.
- Chi tiết từng bước: [`docs/pipeline.md`](docs/pipeline.md). Bảng module: [`docs/architecture.md`](docs/architecture.md).

Ngoài dashboard công khai còn có một bản chạy local (FastAPI + React) để xem kỹ năng, lọc việc làm và so CV với các tin đang mở. Kỹ năng trong CV được trích bằng model chạy trên máy qua Ollama; CV không được lưu hay gửi ra ngoài. API mô tả ở [`docs/api.md`](docs/api.md).

## Các quyết định chính

| ADR | Quyết định |
|---|---|
| [0001](docs/adr/0001-llm-qua-claude-cli.md) | Gọi Claude qua Claude Code CLI bằng gói cá nhân, không dùng API key |
| [0002](docs/adr/0002-chi-crawl-itviec.md) | Chỉ crawl ITviec; mốc v1 là toàn bộ tin AI/Data đang mở (~128) thay vì 1.000 tin |
| [0003](docs/adr/0003-v2-teacher-model-mo.md) | Model nhỏ học từ nhãn của Qwen3-8B, không từ output của Claude (điều khoản Anthropic cấm) |
| [0004](docs/adr/0004-be-fe-local.md) | API + giao diện và tính năng so CV chỉ chạy trên máy cá nhân |

## Chạy thử

Cần Python ≥ 3.12. Bản local có giao diện cần thêm Node 24 và [Ollama](https://ollama.com).

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest

streamlit run app.py              # dashboard, chỉ đọc data/public/skill_counts.csv
scripts\run_local.ps1             # Ollama + API :8000 + giao diện :5173 (cần data/jobs.db)
```

`requirements.txt` chỉ chứa thư viện cho dashboard (Streamlit Cloud đọc file này); `requirements-dev.txt` chứa phần còn lại. `data/jobs.db` và HTML gốc không có trong repo, muốn có thì chạy crawl: `$env:PYTHONPATH="src"; python -m jobmarket.crawl.itviec --limit 20`.

## Cấu trúc

```
app.py              dashboard Streamlit (bản công khai)
src/jobmarket/      crawl/  extract/  normalize/  api/  query.py  evaluate.py ...
frontend/           React + TypeScript (bản local)
tests/              pytest, chạy offline trên HTML mẫu
eval/RESULTS.md     mọi lần đo, chỉ thêm dòng
docs/               pipeline, kiến trúc, ADR, ghi chú nghiên cứu, mô tả API
scripts/            crawl hằng tuần, chạy bản local
```

## Lộ trình

- [x] v1: crawl, che thông tin cá nhân, trích kỹ năng bằng LLM, chuẩn hoá, gold set, dashboard
- [ ] v2: fine-tune Qwen3-1.7B (QLoRA) từ nhãn của Qwen3-8B; router gửi tin dễ cho model local, tin khó cho Claude; cache tin trùng. So 3 cấu hình theo F1, chi phí, độ trễ
- [x] v3: MCP server tự viết (JSON-RPC thuần, spec 2026-07-28) cho agent truy vấn dữ liệu, Claude Code trả đúng 5/5 câu hỏi mẫu ([`docs/mcp-demo.md`](docs/mcp-demo.md)); API + giao diện local
- [ ] v4: bài viết về kiến trúc, cách đo và chi phí
