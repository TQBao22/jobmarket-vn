---
paths:
  - "src/jobmarket/mcp/**"
  - "tests/**/test_mcp*.py"
---

# Quy tắc MCP server (v3)

- Mục tiêu học: tự viết JSON-RPC 2.0 qua stdio bằng stdlib (`json`, `sys`), không dùng MCP SDK.
- Spec mới nhất là `2026-07-28` (stateless, `server/discover`). Trước khi code: kiểm tra phiên bản Claude Code đang dùng gửi lên, rồi viết theo đúng phiên bản đó; ghi kết quả vào `docs/research/`.
- Kết nối DB ở chế độ chỉ đọc (`sqlite3.connect("file:...?mode=ro", uri=True)`).
- Tool nhận tham số có kiểu, SQL dùng tham số ràng buộc (`?`); không nhận SQL thô từ agent.
- Mỗi tool giới hạn số dòng trả về (mặc định 50).
- Lỗi giao thức (JSON hỏng, method không có, tool không có, `arguments` không phải object, thiếu `_meta`) → lỗi JSON-RPC có `code` + `message`. Tham số tool sai kiểu/giá trị và lỗi khi tool chạy (vd. tháng không có dữ liệu, thiếu DB) → `result` với `isError: true` + thông báo tiếng Việt, để model đọc và gọi lại (spec SEP-1303, `docs/research/mcp-spec.md` mục 4). Sau mọi lỗi server chạy tiếp.
- stdout chỉ dành cho message JSON-RPC; log ghi ra stderr.
- Mỗi tool có test gửi request JSON-RPC và kiểm tra response, không cần Claude Code.
