---
paths:
  - "src/jobmarket/crawl/**"
  - "tests/**/test_crawl*.py"
---

# Quy tắc crawl

- Trước khi crawl một trang mới: đọc `robots.txt` và điều khoản sử dụng. Trang cấm → không crawl, báo người dùng.
- Dùng `urllib.robotparser` kiểm tra từng URL trước khi gửi request.
- Tối thiểu 2 giây giữa hai request cùng domain. Không chạy song song trên cùng domain.
- User-Agent mô tả trung thực (ví dụ `jobmarket-vn-research/0.1`), **không** chứa email hay thông tin cá nhân.
- Chỉ trang công khai. Không đăng nhập, không vượt captcha, không giả lập trình duyệt để lách chặn.
- Lỗi 429/5xx: thử lại tối đa 3 lần, chờ tăng dần. Lỗi 403: dừng cả domain, báo người dùng.
- Mỗi file HTML gốc lưu kèm `url` và `fetched_at`. Không ghi đè file cũ.
- Trường parser không tìm thấy → `None`.
- Mỗi parser có một test chạy trên HTML mẫu trong `tests/fixtures/`, không gọi mạng.
