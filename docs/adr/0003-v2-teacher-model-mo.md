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

## Cập nhật 2026-11-19: thử teacher `think=true` trên nửa dev
Quy tắc chọn (thiết kế `docs/superpowers/specs/2026-11-18-teacher-think-va-mcp-design.md`): dùng `think` nếu F1 dev tăng ≥ 0,05 so với 0,573 **và** sinh nhãn 88 JD ≤ một đêm (~8 giờ).

| | `think=false` | `think=true` |
|---|---|---|
| F1 dev, 20 JD (JD không ra kết quả tính rỗng) | 0,573 | 0,635 (+0,062) |
| F1 trên 17 JD `think` trả được (cùng 17 JD; Haiku 0,871) | 0,583 | 0,721 |
| Precision / recall (20 JD) | 0,621 / 0,532 | 0,818 / 0,518 |
| Trung vị thời gian/JD | 40 s | 263 s (1.124 token, 2,8 token/s) |
| JD không ra kết quả | 1/20 | 3/20: suy nghĩ vượt 4.096 token; chạy lại với 8.192 vẫn hết giới hạn 30 phút/lần gọi |

Ước lượng 88 JD với `think`: 85% JD × 263 s + 15% JD × 1.800 s (chờ hết giới hạn) ≈ 5,5 + 6,6 ≈ **12 giờ** > 8 giờ.

**Kết luận theo quy tắc: chưa dùng `think`** (đạt điều kiện F1, trượt điều kiện thời gian). Teacher vẫn là Qwen3-8B `think=false`.

Phương án mở, cần người dùng quyết: `think=true` với giới hạn ~10 phút/JD, JD không xong thì bỏ khỏi tập train (không gán nhãn rỗng). Ước tính ~8 giờ (sát ngưỡng) và mất ~25% JD (2/17 JD thành công cũng mất hơn 10 phút). Đổi lại nhãn chính xác hơn rõ (precision 0,82 so với 0,62).

Hạn chế của phép đo: 20 JD, chênh < 0,05 coi như nhiễu (+0,062 chỉ vừa qua ngưỡng); thời gian đo trên máy có lúc chạy song song việc khác và một lần máy ngủ (đã loại khỏi trung vị).
