# Khớp CV có bằng chứng từ project (thiết kế ngắn, đã duyệt 2026-11-20)

## Mục đích
Khi khớp CV ↔ JD, kỹ năng có bằng chứng trong project/kinh nghiệm làm việc nặng hơn kỹ năng chỉ liệt kê; giao diện cho người dùng thấy câu trích làm bằng chứng.

## Mục tiêu / không làm
- Làm: phân loại mỗi kỹ năng CV `used` / `listed`, kèm câu trích; hạ trọng số `listed`; hiện bằng chứng.
- Không làm: so khớp ngữ nghĩa (embedding), số năm kinh nghiệm, đánh giá chất lượng project.
- Không được: lưu CV hay câu trích (file, DB, log).

## Ràng buộc
- CV chỉ xử lý local qua Ollama, không lưu (CLAUDE.md v3).
- Không có bộ CV có đáp án → không đo F1; kiểm bằng test + chạy tay 1 CV.

## Cách đã cân nhắc
1. Gắn bằng chứng từng kỹ năng (chọn): sửa prompt + schema + công thức điểm, nhỏ, chạy được trên GTX 1650.
2. So khớp ngữ nghĩa bằng embedding: bắt được kỹ năng không ghi tên, nhưng thêm model, chậm trên máy hiện tại.

## Thiết kế
- Prompt `cv_v2.txt`: mỗi kỹ năng `{name, evidence: used|listed, quote}`; `used` = có trong mô tả project/kinh nghiệm; `listed` = chỉ ở mục kỹ năng/học vấn/chứng chỉ; `quote` ≤ ~12 từ chép nguyên văn từ CV, rỗng nếu `listed`.
- Schema riêng cho CV; `ollama_runner` nhận `schema`, `num_predict` (CV: 2048).
- `query.match(..., listed=())`: kỹ năng khớp thuộc `listed` nhân hệ số 0,5. MCP `match_skills` không đổi (mọi kỹ năng là `used`).
- `/api/match`: `cv_skills` = `[{skill, evidence, quote}]`.
- Giao diện: 2 nhóm kỹ năng CV, câu trích trong `<details>`, kỹ năng khớp nhưng chỉ liệt kê ghi "(chỉ liệt kê)".

## Quyết định của người làm (Claude), người dùng có thể sửa
- Hệ số 0,5 cho `listed`: chọn tay, không đo được; ghi trong `docs/api.md`.
- Câu trích không tìm thấy trong CV (so sau khi gộp khoảng trắng, không phân biệt hoa thường) → hạ về `listed`, bỏ câu trích: bằng chứng phải kiểm được, không tin model bịa.
- Hai mục chuẩn hoá về cùng tên → gộp, `used` thắng.
- (Thêm khi chạy thật 2026-11-20) Câu trích phải chứa tên kỹ năng: qwen3:8b gắn Spark `used` với câu trích có trong CV nhưng không nhắc Spark. Cái giá: kỹ năng model dịch sang tiếng Anh ("học máy" → Machine Learning) bị hạ về `listed`.
