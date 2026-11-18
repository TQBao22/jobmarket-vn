# Thiết kế: thử teacher `think` (v2) song song MCP server (v3)

Ngày: 2026-11-18 · Trạng thái: chờ người dùng duyệt · đã qua kiểm tra của một builder (3 điểm, Claude tự quyết, đánh dấu "quyết định của Claude")

## Mục đích
Người dùng muốn hoàn thiện các ý tưởng đã đặt ra trong lộ trình thay vì thêm tính năng mới. Hai phần còn dang dở có thể chạy song song vì dùng tài nguyên khác nhau:

- **v2:** teacher Qwen3-8B zero-shot chỉ đạt F1 0,573 trên nửa dev (gold 20 JD). Student 1.7B học từ nhãn teacher nên khó vượt mức này. Cần biết bật chế độ suy nghĩ (`think=true`) có nâng teacher đủ để dùng không, trước khi bỏ ~1–4 giờ GPU sinh nhãn cho 88 JD ngoài gold. Việc này chạy bằng GPU local, không tốn hạn mức Claude.
- **v3:** MCP server là tiêu chí xong còn thiếu của v3. Dùng lại `src/jobmarket/query.py` (đã phục vụ REST API).

## Mục tiêu
1. Một dòng mới trong `eval/RESULTS.md`: Qwen3-8B `think=true`, nửa dev, kèm thời gian/JD. Một quyết định ghi vào ADR 0003: dùng teacher nào để sinh nhãn.
2. MCP server đạt tiêu chí v3 trong `CLAUDE.md`: Claude Code kết nối được · ≥3 tool · mỗi tool có test · trả lời đúng 5 câu hỏi mẫu trong `docs/mcp-demo.md`.

## Không làm
- Không sinh nhãn cho 88 JD, không fine-tune, không router/cache (bước sau, tuỳ kết quả mục 1).
- Không chấm nửa test của gold (chỉ chấm khi đã chốt cấu hình teacher).
- MCP không có tool ghi/sửa DB, không nhận SQL thô, không nhận file CV (CV chỉ qua API local, ADR 0004).
- Không dùng MCP SDK (mục tiêu học: tự viết JSON-RPC, `.claude/rules/mcp-server.md`).

## Thất bại dù chạy được
- Dòng RESULTS cho `think` bị lẫn với kết quả `think=false` do cache trích xuất dùng chung tên model.
- MCP server in log ra stdout làm hỏng luồng JSON-RPC.
- 5 câu hỏi mẫu có đáp án "đúng" chỉ vì chép từ output của chính server, không đối chiếu độc lập.

## Ràng buộc
- Quy tắc trong `CLAUDE.md`, `.claude/rules/llm-extraction.md`, `.claude/rules/mcp-server.md`.
- GTX 1650 4 GB VRAM; Qwen3-8B một phần chạy CPU (đo: ~40 giây/JD khi `think=false`).
- CLAUDE.md hiện chỉ cho FastAPI + FE của v3 chạy song song v2; người dùng đã chọn hướng này (2026-11-18), cần sửa ngoại lệ để gồm MCP.

## Các hướng đã cân nhắc
| Hướng | Đánh đổi | Chọn? |
|---|---|---|
| **v2 teacher `think` chạy nền + viết MCP cùng lúc** | GPU và người viết code không chờ nhau; phải sửa ngoại lệ "làm tuần tự" | **Người dùng chọn** |
| Chỉ v2 theo đúng thứ tự | Đúng lộ trình, nhưng nhiều giờ chờ GPU không làm gì khác | Không |
| Làm đẹp dashboard (xu hướng theo tuần, cặp kỹ năng) | Dễ thấy, nhưng không hoàn thiện ý tưởng nào; dữ liệu mới 2 tháng | Không |

## Phần A: teacher `think`
- `extract/local.py`: thêm tham số `think: bool` cho `ollama_runner` và cờ CLI `--think`. Khi bật: gửi `"think": true`, nâng `num_predict` để chỗ cho phần suy nghĩ (giá trị cụ thể: builder chọn, có lý do; phải giữ chặn lặp vô hạn), và lưu kết quả dưới tên model `qwen3:8b-think` để cache và `evaluate --model` tách khỏi `qwen3:8b`.
- Chạy: `python -m jobmarket.extract.local --model qwen3:8b --think --gold dev` (20 JD), rồi `python -m jobmarket.evaluate --model qwen3:8b-think --split dev --append`.
- Ghi thời gian/JD vào ghi chú dòng RESULTS (để ước lượng thời gian sinh nhãn 88 JD).
- JD bị cắt do hết `num_predict` (quyết định của Claude): mục tiêu 0 JD bị cắt để kết luận phản ánh chất lượng suy nghĩ chứ không phản ánh ngân sách token. Có JD bị cắt → nâng `num_predict` gấp đôi và chạy lại riêng các JD đó một lần; còn sót thì tính là dự đoán rỗng như các dòng trước, ghi số lượng vào ghi chú. Kiểm tra ở JD đầu tiên rằng Ollama nhận `format` cùng `think: true`.
- Quy tắc quyết định (ghi vào ADR 0003):
  - F1 dev tăng ≥ 0,05 so với 0,573 và thời gian sinh nhãn 88 JD ≤ một đêm (~8 giờ) → dùng `think` làm teacher.
  - Ngược lại → giữ `think=false`; hướng nâng tiếp là prompt few-shot với ví dụ do người dùng tự gán trên JD ngoài gold (bàn sau, không thuộc thiết kế này).
  - 20 JD cho sai số lớn: ghi rõ trong ADR, chênh < 0,05 coi như không khác.

## Phần B: MCP server
- Vị trí: `src/jobmarket/mcp/` (`server.py` + `__main__.py`), chạy `python -m jobmarket.mcp`. stdlib (`json`, `sys`, `sqlite3`).
- Phiên bản giao thức: theo quy tắc MCP, bước đầu tiên là ghi lại request `initialize` (hoặc tương đương) mà Claude Code trên máy gửi tới, xác định phiên bản spec, đọc spec đó, ghi vào `docs/research/mcp-spec.md`. Server viết đúng phiên bản đó.
- Transport: stdio, mỗi message JSON-RPC 2.0 một dòng; stdout chỉ cho message, log ra stderr.
- Kết nối DB: `query` hiện nhận `conn`; MCP mở `file:...?mode=ro` giống `api/app.py` (`JOBMARKET_DB`, mặc định `data/jobs.db`).
- Tool (gọi thẳng hàm trong `query.py`, không lặp logic):

  | Tool | Tham số | Gọi |
  |---|---|---|
  | `top_skills` | `month?` (YYYY-MM), `limit` (mặc định 20, ≤ 50) | `query.top_skills` |
  | `search_jobs` | `skill?`, `open_only` (mặc định true), `limit` (mặc định 20, ≤ 50) | `query.jobs` |
  | `match_skills` | `skills` (danh sách tên kỹ năng), `top_k` (mặc định 10, ≤ 50) | `query.match` |

  `match_skills` nhận danh sách kỹ năng do agent đưa, không nhận CV.
- Lỗi (quyết định của Claude, theo spec MCP): lỗi giao thức (JSON hỏng, method không có, tool không có, tham số sai kiểu/thiếu) → lỗi JSON-RPC có `code` + `message`; lỗi khi tool chạy (tháng không có dữ liệu) → `result` với `isError: true` và thông báo tiếng Việt, để model đọc được và thử lại. Server chạy tiếp sau mọi lỗi. Sửa dòng tương ứng trong `.claude/rules/mcp-server.md` cho khớp. Nếu phiên bản spec ghi nhận được phân loại khác thì theo spec đó.
- Kết nối Claude Code: file `.mcp.json` ở gốc repo (project scope), lệnh `.venv\Scripts\python -m jobmarket.mcp`, env `PYTHONPATH=src`. Pipeline gọi `claude -p` với `--strict-mcp-config` nên không bị server này ảnh hưởng.
- Test `tests/test_mcp.py`: chạy server như subprocess (hoặc gọi hàm xử lý một dòng), gửi request JSON-RPC, kiểm tra response; DB tạm trong test như `tests/test_query.py`. Mỗi tool ≥1 test đúng + test lỗi chung.
- `docs/mcp-demo.md`: 5 câu hỏi tiếng Việt về thị trường (ví dụ kỹ năng nhiều nhất tháng X, số JD đang mở cần Docker, với bộ kỹ năng Y thì JD nào hợp nhất và thiếu gì). Đáp án đúng tính độc lập bằng SQL/pytest trên DB thật tại ngày ghi, ghi kèm ngày; demo = hỏi Claude Code, so câu trả lời với đáp án.

## Người dùng đã quyết
- Chạy song song A và B (hướng 1).
- Teacher là model mở, không dùng output Claude để train (ADR 0003).
- Không MCP SDK.

## Để builder quyết
- Giá trị `num_predict` khi `think`; cách đo thời gian/JD.
- Cấu trúc nội bộ `mcp/server.py`, cách test (subprocess hay hàm thuần).
- Nội dung cụ thể 5 câu hỏi mẫu (người dùng duyệt trước khi chốt).

## Thứ tự
1. Sửa ngoại lệ "làm tuần tự" trong `CLAUDE.md` (quyết định của Claude): phần FastAPI + FE + MCP của v3 làm song song v2, mỗi phần một nhánh riêng, merge độc lập khi `pytest` xanh (bỏ "merge sau v2", vì v2 còn nhiều ngày). Sửa trên `feat/mcp`.
2. A: `--think` (TDD) → khởi động chạy nền 20 JD dev.
3. B trong lúc A chạy: ghi nhận phiên bản giao thức → server + test (TDD) → `.mcp.json` → kết nối Claude Code → `docs/mcp-demo.md`.
4. A xong: evaluate, dòng RESULTS, cập nhật ADR 0003.
5. Nhánh: `feat/mcp` (B + thiết kế này + sửa CLAUDE.md), `eval/teacher-think` (A, tách từ `main`). Hai PR độc lập, không phụ thuộc thứ tự merge (khác file, trừ khi cả hai cùng sửa `CLAUDE.md` dòng "Đang ở": PR merge sau rebase).
