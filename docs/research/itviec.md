# ITviec — quyền crawl và cấu trúc (kiểm tra 2026-11-16)

## robots.txt
`Disallow: /subscriptions/new`, còn lại `Allow: /`. Trang JD (`/viec-lam-it/...`) được phép.

## Điều khoản ([Thoả Thuận Sử Dụng](https://itviec.com/blog/terms-conditions-vn/), hiệu lực 01/07/2023)
- Không có điều khoản riêng về crawl/scraping/robot.
- §2.2: nội dung trang web "không được lấy, hiển thị, sửa đổi, sao chép, in, bán, tải về, cho thuê" khi "không có sự đồng ý trước bằng văn bản", "ngoại trừ trường hợp cần thiết và được sử dụng trong chừng mực".
- §2.1: nội dung được bảo hộ bản quyền.

→ Hệ quả cho project: HTML/nội dung JD chỉ lưu trên máy (`data/raw/` đã gitignore); phần công khai (dashboard, bài viết) chỉ chứa **số liệu tổng hợp** + link nguồn, không đăng lại nội dung JD. Crawl chậm (≥2 giây/request).

## Cấu trúc
- Sitemap index: `https://itviec.com/dunggiatminh.xml` (13 sitemap con).
- Danh sách JD: `https://itviec.com/twinnings_jobs_desc_vn.xml` (và `_en`) — mỗi `<url>` là một JD, ~146KB, ước tính vài trăm tới ~1.000 JD đang mở (chưa đếm chính xác).
- URL JD: `https://itviec.com/viec-lam-it/{slug}-{id}`, `{id}` 4 chữ số.
- Dùng sitemap thay cho trang danh sách → không cần parse phân trang.

## Đo được (2026-11-16)
- Sitemap `_vn`: 615 JD IT đang mở; 123 JD có slug khớp từ khoá AI/Data → **một mình ITviec không đủ mốc ≥1.000 JD**.
- Chạy thử 20 JD: 0 lỗi, 0 trường thiếu, mô tả trung bình ~3.900 ký tự, 0 SĐT/email trong mô tả.
- Title trong JSON-LD bỏ dấu ngoặc so với `<h1>` (`Data Scientist ML, AWS` vs `Data Scientist (ML, AWS)`) — chỉ ảnh hưởng hiển thị.
- Có JD đăng qua "ITviec Recruitment Consulting" (headhunter): công ty thật bị ẩn → thống kê theo công ty cần lưu ý.
- Thẻ `skills` của ITviec sơ sài so với nội dung JD → dùng làm baseline so với LLM.

## Chưa biết
- JD đóng có bị xoá khỏi sitemap không (nếu có: crawl nhiều lần theo thời gian sẽ tích luỹ thêm JD).
