# ADR 0003 — v2: nhãn train từ model mở (Qwen3-8B), không từ Claude; chạy hoàn toàn trên máy cá nhân

Ngày: 2026-11-17 · Trạng thái: đã chốt

## Bối cảnh
Kế hoạch v2 ban đầu: lấy JSON kỹ năng do Claude Haiku trích làm nhãn, fine-tune Qwen ~1.5B (LoRA), rồi so 3 cấu hình (chỉ Claude / chỉ local / routing). Usage Policy của Anthropic (hiệu lực 2026-11-12, áp dụng cả Claude Code lẫn API) cấm: "Use outputs to train an AI model (e.g., “model scraping” or “model distillation”) without prior authorization from Anthropic". Không có ngoại lệ cho dùng cá nhân/phi thương mại. Chi tiết và nguồn: `docs/research/anthropic-dieu-khoan-finetune.md`.

Phần cứng: GTX 1650, 4 GB VRAM. Dữ liệu: 128 JD AI/Data, 40 JD là gold → ~88 JD dùng được để train; tăng ~90–100 JD/tháng nhờ crawl hàng tuần.

## Các lựa chọn
| Lựa chọn | Vì sao không/có |
|---|---|
| Train trên output Claude như kế hoạch cũ | Vi phạm Usage Policy |
| Xin phép Anthropic bằng văn bản | Chậm, không chắc có trả lời |
| Bỏ fine-tune, chỉ router model local few-shot ↔ Claude | Hợp lệ, nhưng mất phần fine-tune |
| **Teacher = model mở Apache-2.0 (Qwen3-8B) sinh nhãn, fine-tune Qwen3-1.7B** | **Chọn** |
| Fine-tune trên Google Colab (T4 16 GB) | Người dùng chọn không: nội dung JD ITviec chỉ ở máy local |

## Quyết định
- Nhãn train: Qwen3-8B (Apache-2.0) chạy local (Ollama, lượng tử hoá, một phần trên CPU) trích kỹ năng trên JD **ngoài gold**, cùng prompt/schema với Claude.
- Student: Qwen3-1.7B (Apache-2.0), QLoRA trên GTX 1650. Không dùng Qwen2.5-3B (giấy phép qwen-research, phi thương mại).
- Claude Haiku chỉ dùng để suy luận: baseline và nhánh fallback của router. Không output Claude nào (kể cả gold do Opus gán) vào tập train.
- Thứ tự: (1) đo Qwen3-1.7B và Qwen3-8B chưa fine-tune, prompt v1 zero-shot, trên gold làm mốc; (2) sinh nhãn teacher; (3) fine-tune; (4) router + cache; (5) so 3 cấu hình kèm khoảng tin cậy bootstrap của F1 (40 JD gold cho sai số lớn).

## Lý do
- Tuân thủ điều khoản là điều kiện để đăng repo và bài viết công khai.
- Teacher yếu hơn Claude → trần chất lượng của student thấp hơn. Đây là đánh đổi có chủ đích; đo được bằng F1 của teacher trên gold.
- Chạy local hết: không đưa nội dung JD lên dịch vụ ngoài ngoài Claude (đã có từ v1).

## Hệ quả
- Sinh nhãn teacher chậm: ước tính 3–4 giờ cho ~88 JD trên GTX 1650 (chưa đo). Đo ở lần chạy đầu và cập nhật ADR này.
- QLoRA 1.7B trên 4 GB VRAM sát giới hạn: có thể phải giảm độ dài chuỗi hoặc batch 1. Nếu không chạy được → xét lại (model 0.6B hoặc hỏi lại về Colab).
- Rủi ro còn treo ở ADR 0001: điều khoản gói cá nhân không nói thẳng cho phép chạy `claude -p` theo script.
