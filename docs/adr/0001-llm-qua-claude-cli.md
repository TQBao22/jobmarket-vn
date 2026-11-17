# ADR 0001 — Gọi LLM qua `claude -p` thay vì API key

Ngày: 2026-11-16 · Trạng thái: đã chốt

## Bối cảnh
Cần LLM trích kỹ năng từ ~3.000 JD (v1) và làm teacher/fallback ở v2. Người dùng có gói Claude, không muốn trả thêm tiền API.
Gói Claude không kèm credit API (API tính tiền riêng qua Claude Console).

## Các lựa chọn
1. API key Anthropic: rõ chi phí (~$1,2 cho 3.000 JD với Haiku), nhưng trả thêm tiền.
2. Repo proxy biến token đăng nhập của gói thành API: vi phạm điều khoản Anthropic (02/2026), rủi ro khoá tài khoản.
3. **`claude -p` (Claude Code CLI chính thức) ở chế độ tối giản**, dùng gói đã đăng nhập.
4. Gemini free tier / Qwen local: miễn phí nhưng thêm provider; Qwen để dành cho v2.

## Quyết định
Chọn 3, model `haiku` (Claude Haiku 5.5). Lệnh và quy tắc gọi: `.claude/rules/llm-extraction.md`.

## Số đo (1 lần thử, JD mẫu ngắn)
- Ngữ cảnh 1.659 token (không nạp plugin/CLAUDE.md), 206 token đầu ra, 1,8 giây.
- Output đúng schema: `{"skills": ["Python", "LangChain", "RAG", "Docker"]}`.
- `total_cost_usd` quy đổi: $0,00044.

## Số đo lần chạy thật đầu tiên (2026-11-17, lô 20 JD ITviec, prompt v1)
- `--model claude-haiku-5-5` (id đầy đủ) chạy được.
- 63 giây/lô, $0,020 quy đổi/lô (~$1 cho 1.000 JD), 38K token vào, 17K token ra (~860 token ra/JD — cao hơn độ dài danh sách kỹ năng, chưa rõ lý do).

Toàn bộ 123 JD (7 lần gọi): $0,098 quy đổi (~$0,80/1.000 JD), trung vị 39 giây/lô, 0 lỗi; 7 lần gọi liền nhau không chạm hạn mức 5 giờ.

## Hệ quả
- Chi phí thật = hạn mức gói; số `total_cost_usd` dùng làm chi phí quy đổi khi so sánh ở v2.
- Chỉ hợp lệ cho chạy trên máy cá nhân. Nếu làm app cho người khác gọi LLM lúc chạy → phải đổi sang API key.
- Chưa đo: hạn mức 5 giờ chịu được bao nhiêu lô 20 JD. Đo ở lần chạy hàng loạt đầu tiên và cập nhật ADR này.
- Chưa kiểm tra: điều khoản dùng output Claude làm dữ liệu fine-tune (v2).

## Rủi ro điều khoản (kiểm 2026-11-17, `docs/research/anthropic-dieu-khoan-finetune.md`)
- Consumer Terms cấm truy cập bằng script "except ... where we otherwise explicitly permit it". Tài liệu Claude Code hướng dẫn `-p` trong script và `claude setup-token` cho "CI pipelines and scripts", nhưng không câu nào nói thẳng gói Pro/Max được chạy hàng loạt. Giữ quy mô nhỏ (vài lần gọi/tuần), không chạy liên tục.
- Usage Policy cấm dùng output Claude để train model → v2 không train trên output này (ADR 0003).
- Kỹ thuật: tài liệu ghi `--bare` (không dùng gói) "will become the default for `-p`". Khi đó lệnh hiện tại có thể ngừng chạy bằng gói.
