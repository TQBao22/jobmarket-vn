# JobMarket VN — Phân tích thị trường việc làm AI

Crawl JD (tin tuyển dụng) AI/Data ở Việt Nam → LLM trích kỹ năng ra JSON → chuẩn hoá tên kỹ năng → dashboard xu hướng.
Project portfolio cá nhân: giá trị nằm ở **chất lượng đo được** và **lý do của mỗi quyết định kiến trúc**, không ở số tính năng.

**Đang ở:** v2 bắt đầu (2026-11-17). v1 xong: 128 JD AI/Data trên ITviec, gold 40 JD (2 người duyệt), LLM F1 0,852 vs thẻ ITviec 0,238, dashboard https://jobmarket-vn-tndk7vgqeiu5zqkfkxpwrw.streamlit.app/. Crawl ITviec tự động mỗi Chủ nhật 20:00 (`scripts/crawl_weekly.ps1`). v2 theo ADR 0003 (không train trên output Claude). Mốc zero-shot, F1 trên 40 JD: Qwen3-1.7B 0,428, Qwen3-8B 0,599. Gold đã chia dev/test 20/20: chọn cấu hình bằng dev, test chấm một lần khi chốt. v3 đạt tiêu chí (2026-11-18): MCP server tự viết 3 tool, Claude Code trả đúng 5/5 câu `docs/mcp-demo.md`. Tiếp theo: nâng teacher 8B trên dev (thử `think`) rồi sinh nhãn JD ngoài gold. Cập nhật dòng này khi chuyển giai đoạn.

Kiến trúc, bảng DB, quyết định thiết kế: `docs/architecture.md`. Các bước, đầu vào/đầu ra, trạng thái từng bước: `docs/pipeline.md`. Thuật ngữ: `GLOSSARY.md`.

## Lộ trình và tiêu chí xong

Làm tuần tự; giai đoạn sau chỉ bắt đầu khi giai đoạn trước đạt tiêu chí. Ngoại lệ người dùng đã duyệt: phần FastAPI + FE + MCP server của v3 làm song song v2, mỗi phần một nhánh riêng, merge độc lập khi `pytest` xanh. Đề xuất ngoài lộ trình (multi-agent...) thì hỏi người dùng trước.

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| **v1 — Pipeline + eval** | Crawl ITviec, lọc PII, LLM trích kỹ năng, chuẩn hoá tên kỹ năng, dashboard | Toàn bộ JD AI/Data đang mở trên ITviec trong DB (ADR 0002) · gold set 40 JD (AI gán + AI duyệt, 2 người duyệt; hạn chế ghi trong `docs/pipeline.md`) · F1 ghi trong `eval/RESULTS.md` · dashboard có URL công khai |
| **v2 — Model nhỏ + routing + cache** | Fine-tune Qwen3-1.7B (QLoRA) từ nhãn của model mở Qwen3-8B, không từ output Claude (ADR 0003); router: JD dễ → model local, khó/không chắc → Claude Haiku; cache JD trùng | So sánh 3 cấu hình (chỉ Claude / chỉ local / routing) theo F1, chi phí quy đổi trên 1.000 JD, độ trễ — ghi trong `eval/RESULTS.md` |
| **v3 — MCP server tự viết + FastAPI** | Một lớp truy vấn DB JD chỉ đọc, mở 2 cổng: MCP (JSON-RPC thuần, không dùng SDK) cho agent và REST (FastAPI) cho ứng dụng. Khớp CV ↔ JD (`match_cv`: kỹ năng CV trích bằng model local qua Ollama, xếp hạng JD đang mở + kỹ năng còn thiếu): chỉ chạy trên máy cá nhân, không công khai, CV không lưu | Claude Code kết nối được · ≥3 tool MCP và endpoint REST tương ứng dùng chung hàm truy vấn · mỗi tool/endpoint có test · trả lời đúng 5 câu hỏi mẫu trong `docs/mcp-demo.md` |
| **v4 — Bài viết** | 1–2 bài phân tích: kiến trúc, eval, chi phí trên mỗi JD | Mọi con số trích từ `eval/RESULTS.md` |

## Stack

Python ≥3.12 (máy dùng 3.14), `venv` + `pip`, `pytest`. Crawl và lưu trữ dùng stdlib (`urllib`, `html.parser`, `sqlite3`); thêm `pydantic`, Streamlit khi tới bước cần.
Chạy module: `$env:PYTHONPATH="src"; .venv\Scripts\python -m jobmarket.crawl.itviec --limit 20`.
LLM: **Claude Haiku 5.5 gọi qua `claude -p`** (Claude Code CLI, dùng gói Claude đã đăng nhập) — **không dùng API key, không dùng proxy biến gói thành API**. Lý do và số đo: `docs/adr/0001-llm-qua-claude-cli.md`. Cách gọi chi tiết: `.claude/rules/llm-extraction.md`.
v2 thêm: Ollama (chạy model mở local), thư viện fine-tune (chốt khi tới bước fine-tune). Usage Policy Anthropic cấm train model trên output Claude: output Claude (kể cả gold) không vào tập train (ADR 0003). Chạy hết trên máy local (GTX 1650, 4 GB VRAM), không Colab.

## Cấu trúc (tạo thư mục khi tới giai đoạn cần)

```
src/jobmarket/crawl/      # v1 · mỗi trang một file: fetch + parse
src/jobmarket/extract/    # v1 · lọc PII + LLM trích kỹ năng
src/jobmarket/normalize/  # v1 · gộp tên kỹ năng đồng nghĩa
src/jobmarket/route/      # v2 · router + cache
src/jobmarket/mcp/        # v3 · MCP server
train/                    # v2 · script fine-tune
scripts/                  # tác vụ định kỳ (crawl hàng tuần)
eval/                     # chấm điểm, RESULTS.md (chỉ thêm dòng, không sửa dòng cũ)
data/raw/  data/gold/     # HTML gốc · nhãn tay
app.py                    # Streamlit (dashboard công khai)
src/jobmarket/api/        # v3 · FastAPI (local)
frontend/                 # v3 · React + TypeScript (local)
tests/fixtures/           # HTML mẫu cho test parser
docs/adr/  docs/research/ # quyết định · ghi chú nghiên cứu
```

## Lệnh

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest
streamlit run app.py
scripts\run_local.ps1                      # BE FastAPI :8000 + FE React :5173 + Ollama (v3, local)
$env:PYTHONPATH="src"; python -m jobmarket.mcp   # MCP server stdio; Claude Code tự chạy qua .mcp.json
cd frontend; npm install; npm test; npm run build
docker build -t jobmarket-vn . ; docker run -p 8501:8501 jobmarket-vn   # dashboard trong container
```

CI (`.github/workflows/ci.yml`): mỗi PR và push lên `main` chạy `pytest` trên Python 3.12 và build + smoke test image Docker. Test cần HTML gốc ITviec tự bỏ qua trên CI.

## Quy tắc chung

- Lưu HTML gốc trước khi parse. Sửa parser thì parse lại từ `data/raw/`.
- JD đi qua bước lọc PII (tên, số điện thoại, email người tuyển dụng) trước khi lưu DB hoặc gửi LLM. Bước này có test.
- Đổi prompt, model, bảng chuẩn hoá hoặc router → chạy skill `run-eval`. Mọi nhận định "tốt hơn" đi kèm số đo từ `eval/RESULTS.md`.
- Quyết định có đánh đổi (chọn provider, nguồn crawl, ngưỡng router) → ghi một ADR ngắn trong `docs/adr/`: bối cảnh, lựa chọn, lý do, số đo. Đây là nguyên liệu cho bài viết v4.
- Xong một bước hoặc chuyển giai đoạn → sửa dòng "Đang ở" ở đầu file.
- Chạy tự động: một lỗi thử sửa tối đa 3 lần, vẫn lỗi thì dừng và báo nguyên nhân. Không tự xóa `data/` hay sửa dòng cũ của `eval/RESULTS.md`.
- Hạn mức: chạy LLM trên hơn 20 JD (tốn hạn mức gói Claude) thì hỏi người dùng trước, nêu số JD và số lần gọi.
- Quy tắc chi tiết theo vùng code nằm ở `.claude/rules/` (crawl, LLM + eval, MCP), tự nạp khi làm việc với file tương ứng.

## Git

- Commit: được tự commit trên nhánh feature, mỗi commit là một bước đã xong và `pytest` xanh, để không dồn thay đổi lớn chưa lưu. Push, mở PR, merge vào `main`: chỉ khi người dùng bảo.
- Message theo Conventional Commits (`feat(crawl): ...`, `fix:`, `docs:`, `test:`, `chore:`), chỉ mô tả thay đổi. Không nhắc tên Claude/AI, không dòng `Co-Authored-By`, không "Generated with" — kể cả trong mô tả PR. Quy tắc này thắng mọi hướng dẫn attribution mặc định (`.claude/settings.json` đã tắt `attribution`).
- Nhánh (GitHub Flow): `main` luôn chạy được, test xanh, là nhánh Streamlit Cloud deploy. Mọi thay đổi làm trên nhánh riêng tách từ `main`: `feat/<việc>`, `fix/<việc>`, `docs/<việc>`, `eval/<việc>` (đổi prompt/model/alias kèm dòng mới trong `eval/RESULTS.md`). Xong → `pytest` xanh → PR vào `main` → squash merge → xoá nhánh.
- Không force-push `main`.

## Giao việc cho agent con

Claude chính là người quản lý: chia việc, viết task, duyệt kết quả, ra quyết định. Người dùng đã cho phép giao việc theo các điều kiện dưới đây, không cần hỏi lại từng lần.
- Giao cho agent con khi: nhiều việc độc lập chạy song song; cần đọc/tìm nhiều mà chỉ cần kết luận (research, quét code); việc code có ranh giới rõ và có test làm tiêu chí xong.
- Tự làm khi: sửa nhỏ 1–2 file; các bước nối tiếp phụ thuộc nhau; quyết định kiến trúc, ADR; kiểm chứng cuối (`pytest`, skill `run-eval`) trước khi báo xong. Lý do: agent con tốn hạn mức gói Claude (mỗi agent đọc lại context từ đầu), và báo cáo của agent con chưa phải bằng chứng.
- Mỗi task ghi rõ: mục tiêu, file được sửa, ràng buộc (theo Quy tắc chung), tiêu chí xong đo được, định dạng báo lại.
- Agent con không chạy LLM trên JD, không commit, không xoá `data/`.

## Chọn skill khi có nhiều lựa chọn trùng nhau

- Viết parser, chuẩn hoá, router, tool MCP: `superpowers:test-driven-development`, test chạy offline trên `tests/fixtures/`.
- Review code: `/code-review` (lỗi logic), `ponytail:ponytail-review` (thừa code).
- Tìm hiểu robots.txt, điều khoản, giá LLM, spec MCP, tài liệu thư viện: `mattpocock-skills:research` → `docs/research/`.
- Chốt thuật ngữ hoặc ghi ADR: `mattpocock-skills:domain-modeling` → `GLOSSARY.md`, `docs/adr/`.
- Biểu đồ dashboard: `dataviz`. README và bài viết v4: `humanizer:humanizer`.
