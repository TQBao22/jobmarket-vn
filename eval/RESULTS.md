# Kết quả eval trích kỹ năng

Chỉ thêm dòng, không sửa dòng cũ.

| ngày | cấu hình | model | prompt | P | R | F1 | chi phí /1.000 JD | độ trễ p50 | ghi chú |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-17 | baseline | thẻ ITviec | — | 0.619 | 0.147 | 0.238 | $0 | — | 40 JD gold. Nhãn gold do claude-opus-5-5 gán, chưa người duyệt. Rò rỉ: alias v1 lập từ lô 20 JD đầu (8 JD gold). |
| 2026-11-17 | api | claude-haiku-5-5 | v1 | 0.894 | 0.812 | 0.851 | $0.80 | 39s/lô | 40 JD gold. Nhãn gold do claude-opus-5-5 gán, chưa người duyệt. Rò rỉ: alias v1 lập từ lô 20 JD đầu (8 JD gold). |
| 2026-11-17 | baseline | thẻ ITviec | — | 0.619 | 0.147 | 0.238 | $0 | — | 40 JD gold. Gold: 2/40 người duyệt, 38/40 Opus gán + Sonnet 5.5 duyệt (4 thêm, 1 xoá, câu trích đã đối chiếu). Vẫn là nhãn AI. |
| 2026-11-17 | api | claude-haiku-5-5 | v1 | 0.895 | 0.813 | 0.852 | $0.80 | 39s/lô | 40 JD gold. Gold: 2/40 người duyệt, 38/40 Opus gán + Sonnet 5.5 duyệt (4 thêm, 1 xoá, câu trích đã đối chiếu). Vẫn là nhãn AI. |
| 2026-11-17 | local | qwen3:1.7b | v1 | 0.496 | 0.376 | 0.428 | $0.00 | 7s/lô | 40 JD gold. Ollama local, GTX 1650, 1 JD/lần gọi (latency = s/JD), prompt v1 zero-shot, chưa fine-tune, think=false. 1/40 JD lỗi (output bị cắt ở 1.024 token) tính là dự đoán rỗng. Gold: 2 người duyệt, 38 AI. |
| 2026-11-18 | local | qwen3:8b | v1 | 0.619 | 0.581 | 0.599 | $0.00 | 40s/lô | 40 JD gold. Ollama local, GTX 1650 (model không vừa 4 GB VRAM, một phần chạy CPU), 1 JD/lần gọi (latency = s/JD), prompt v1 zero-shot, chưa fine-tune, think=false. 1/40 JD lỗi (JSON bị cắt) tính là dự đoán rỗng. Gold: 2 người duyệt, 38 AI. |
| 2026-11-18 | api | claude-haiku-5-5 | v1 | 0.891 | 0.809 | 0.848 | $0.80 | 37s/lô | 20 JD gold (dev). Mốc dev cho v2, số liệu như dòng 40 JD cùng model, chỉ tách nửa dev. |
| 2026-11-18 | local | qwen3:1.7b | v1 | 0.464 | 0.355 | 0.402 | $0.00 | 7s/lô | 20 JD gold (dev). Mốc dev cho v2, số liệu như dòng 40 JD cùng model, chỉ tách nửa dev. |
| 2026-11-18 | local | qwen3:8b | v1 | 0.621 | 0.532 | 0.573 | $0.00 | 40s/lô | 20 JD gold (dev). Mốc dev cho v2, số liệu như dòng 40 JD cùng model, chỉ tách nửa dev. |
