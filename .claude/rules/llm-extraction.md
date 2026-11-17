---
paths:
  - "src/jobmarket/extract/**"
  - "src/jobmarket/normalize/**"
  - "src/jobmarket/route/**"
  - "train/**"
  - "eval/**"
---

# Quy tắc trích xuất bằng LLM, routing và đánh giá

## Gọi LLM qua `claude -p`
- Lệnh mẫu đã chạy thành công (2026-11-16, ~1.659 token ngữ cảnh, 1,8 giây):
  ```
  <CLAUDE_BIN> -p "<yêu cầu>" --setting-sources project --tools "" --strict-mcp-config
    --disable-slash-commands --no-session-persistence --max-turns 2 --model haiku
    --system-prompt "<prompt>" --output-format json --json-schema '<schema>'
  ```
  JD truyền qua stdin (giới hạn 10MB).
- `CLAUDE_BIN` đọc từ biến môi trường, mặc định `claude`. Trên máy hiện tại CLI nằm trong extension VS Code (`~/.vscode/extensions/anthropic.claude-code-<version>-win32-x64/resources/native-binary/claude.exe`), đường dẫn đổi theo version.
- Chạy với `cwd` là một thư mục tạm trống (`tempfile.mkdtemp()`), để không nạp `CLAUDE.md` hay plugin của project.
- Gộp tối đa 20 JD mỗi lần gọi, schema trả về danh sách `{jd_id, skills}`; kiểm tra đủ `jd_id` trả về.
- Lấy kết quả từ trường `structured_output`; thiếu trường này hoặc `is_error: true` → ghi log + bỏ qua lô đó.
- Ghi `total_cost_usd` (giá API quy đổi, không phải tiền trả thật) và `usage` vào log để so sánh chi phí ở v2.
- Không dùng `--bare` (bắt buộc API key) và không dùng repo proxy biến gói Claude thành API (vi phạm điều khoản Anthropic từ 02/2026).

## Đầu vào và đầu ra
- Input là JD **đã lọc PII**. Output luôn đi qua schema `pydantic`; parse lỗi → ghi log + bỏ qua JD đó.
- Ghi model id và phiên bản prompt cho mỗi lần chạy.
- Cache kết quả theo hash(nội dung JD + prompt + model) để không trả tiền hai lần cho cùng một JD.
- Ghi số token và chi phí mỗi lần chạy.

## Chuẩn hoá kỹ năng
- Bảng ánh xạ alias → tên chuẩn nằm trong file (dễ đọc, dễ sửa tay); dùng embedding/LLM chỉ cho alias chưa có trong bảng.
- Tên chuẩn: dùng nhãn ESCO khi ESCO có kỹ năng đó (tải bản offline, miễn phí); công cụ/thư viện ESCO chưa có (LangChain, vLLM...) thì tự đặt và ghi vào `GLOSSARY.md`.

## Routing và cache (v2)
- Router quyết định dựa trên tín hiệu đo được (độ tin cậy của model local, độ dài JD...), ngưỡng chọn bằng eval và ghi ADR.
- Cache chỉ dùng lại kết quả khi nội dung JD trùng (sau chuẩn hoá khoảng trắng); trùng gần đúng phải được eval chứng minh không giảm F1 trước khi bật.
- Model teacher cho dữ liệu fine-tune phải có điều khoản cho phép; ghi nguồn dữ liệu huấn luyện vào ADR.

## Eval
- **JD trong `data/gold/` chỉ dùng để chấm điểm** — prompt, dữ liệu fine-tune và ngưỡng router lấy từ JD ngoài gold set.
- Chấm trên tên kỹ năng sau chuẩn hoá. Báo precision, recall, F1 micro.
