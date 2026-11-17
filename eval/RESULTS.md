# Kết quả eval trích kỹ năng

Chỉ thêm dòng, không sửa dòng cũ.

| ngày | cấu hình | model | prompt | P | R | F1 | chi phí /1.000 JD | độ trễ p50 | ghi chú |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-17 | baseline | thẻ ITviec | — | 0.619 | 0.147 | 0.238 | $0 | — | 40 JD gold. Nhãn gold do claude-opus-5-5 gán, chưa người duyệt. Rò rỉ: alias v1 lập từ lô 20 JD đầu (8 JD gold). |
| 2026-11-17 | api | claude-haiku-5-5 | v1 | 0.894 | 0.812 | 0.851 | $0.80 | 39s/lô | 40 JD gold. Nhãn gold do claude-opus-5-5 gán, chưa người duyệt. Rò rỉ: alias v1 lập từ lô 20 JD đầu (8 JD gold). |
