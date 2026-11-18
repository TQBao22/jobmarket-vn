# ADR 0004 — v3: BE FastAPI + FE React chạy local; khớp CV chỉ trên máy cá nhân

Ngày: 2026-11-17 · Trạng thái: đã chốt

## Bối cảnh
v1 có dashboard Streamlit đọc CSV tổng hợp, deploy công khai. Người dùng muốn thêm: tách BE/FE, và tính năng upload CV để xem hợp JD nào nhất. Ràng buộc: gọi Claude qua `claude -p` chỉ hợp lệ trên máy cá nhân (ADR 0001); Streamlit Cloud không gọi được Ollama trên máy người dùng và không đủ sức chạy model 1.7B–8B; CV chứa thông tin cá nhân.

## Các lựa chọn
| Lựa chọn | Đánh đổi |
|---|---|
| Giữ Streamlit, thêm trang CV | Nhanh nhất (~1 ngày), không có BE/FE tách rời |
| **FastAPI + React/TypeScript, chạy local** | **Chọn.** Thêm Node vào stack, ~2–3 ngày; FE/BE tách thật, REST API dùng chung lớp truy vấn với MCP server |
| Deploy công khai + CV qua API trả tiền | Cần API key, chi phí theo token, phải xử lý CV người lạ; chưa cần |
| CV công khai bằng so khớp từ khoá (không LLM) | Chạy được trên host miễn phí, nhưng người dùng chỉ muốn tự chạy và test trước |

## Quyết định
- BE: FastAPI `localhost:8000`, route `/api/*` (hợp đồng: `docs/api.md`), đọc `jobs.db` chế độ chỉ đọc. Hàm truy vấn nằm ở `src/jobmarket/query.py`, dùng chung với MCP server (v3).
- FE: Vite + React + TypeScript trong `web/`, `localhost:5173`, gọi BE qua proxy `/api`. Không UI kit, không thư viện biểu đồ.
- Khớp CV: kỹ năng CV trích bằng model local qua Ollama; xếp hạng JD đang mở theo độ phủ kỹ năng có trọng số `ln(N/df)+1`; trả kỹ năng còn thiếu. CV chỉ xử lý trong bộ nhớ.
- Không deploy BE/FE. Dashboard Streamlit công khai giữ nguyên (đọc CSV).

## Lý do
- Thị trường: REST API 19%, FastAPI 12%, TypeScript 12% JD trong dữ liệu dự án; người dùng chọn React/TS.
- Một lớp truy vấn, hai cổng (MCP + REST): không lặp logic, có câu chuyện kiến trúc cho bài viết v4.
- Local-only giữ đúng ADR 0001 và không đưa CV ra ngoài.

## Hệ quả
- Chất lượng khớp CV phụ thuộc model local (qwen3:1.7b F1 0,428 trên JD; 8B và bản fine-tune đang đo). Chưa có eval riêng cho trích kỹ năng CV.
- Chạy cần 3 tiến trình: Ollama, uvicorn, Vite dev server.
- JD đóng (hết `valid_through`) không được gợi ý; crawl hàng tuần giữ danh sách JD mở cập nhật.
