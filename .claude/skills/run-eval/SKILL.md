---
name: run-eval
description: Eval trích xuất kỹ năng trên gold set, ghi một dòng vào eval/RESULTS.md. Dùng sau khi đổi prompt, model hoặc bảng chuẩn hoá, hoặc khi người dùng yêu cầu đo/so sánh.
---

# Chạy eval trích xuất

Lệnh (từ thư mục gốc, `PYTHONPATH=src`): `python -m jobmarket.gold status`, `python -m jobmarket.extract.llm`, `python -m jobmarket.evaluate --system llm|tags [--model ...] [--split dev|test|all] [--append] [--note "..."]`.

Gold chia đôi cố định (`gold.dev_test`): **dev** (mặc định) để so cấu hình khi đang thử; **test** chỉ chấm một lần khi đã chốt cấu hình, ghi rõ trong ghi chú. So sánh chỉ giữa các dòng cùng nửa.

1. Kiểm tra `data/gold/labels.jsonl` có JD đã gán nhãn (`gold status`). Chưa có → báo người dùng cần gán nhãn trước, dừng.
2. Chạy trích xuất cho các JD gold chưa có kết quả với cấu hình hiện tại (model, phiên bản prompt); cache bỏ qua JD đã trích.
3. `evaluate` chuẩn hoá kỹ năng ở cả dự đoán lẫn nhãn, rồi tính precision, recall, F1 (micro).
4. Thêm **một dòng** vào cuối `eval/RESULTS.md` (`--append` tự tạo file nếu chưa có):
   `| ngày | cấu hình (api/local/routing) | model | prompt | P | R | F1 | chi phí /1.000 JD | độ trễ p50 | ghi chú |`
   Không sửa các dòng cũ.
5. Liệt kê 5 JD sai nhiều nhất, mỗi JD ghi: kỹ năng bị sót, kỹ năng bị thừa.
6. So với dòng trước đó trong `RESULTS.md`: tăng hay giảm, bao nhiêu.
