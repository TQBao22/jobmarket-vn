---
name: add-source
description: Thêm nguồn crawl (trang tuyển dụng mới như ITviec, TopCV, JobsGO): kiểm tra robots.txt, lấy HTML mẫu, viết parser + test.
---

# Thêm nguồn crawl mới

Làm lần lượt, dừng ở bước nào thất bại thì báo người dùng.

1. **Kiểm tra quyền:** đọc `https://<domain>/robots.txt` và điều khoản sử dụng **trước khi tải bất kỳ trang nào khác** (sitemap, JD, danh mục). Tìm cả mục cấm robot/spider/"thiết bị tự động". Robots hoặc điều khoản cấm → dừng, báo người dùng, đề xuất nguồn khác.
2. **Lấy mẫu:** tải tay 3 trang JD khác nhau + 1 trang danh sách, lưu vào `tests/fixtures/<domain>/`. Xoá thông tin cá nhân (tên, sđt, email người tuyển) khỏi file mẫu.
3. **Viết parser:** `src/jobmarket/crawl/<domain>.py`, trả về cùng các trường như các nguồn đã có. Theo `.claude/rules/crawling.md`.
4. **Test:** một test trong `tests/` parse 3 file mẫu, kiểm tra tiêu đề, công ty, nội dung JD không rỗng. Chạy `python -m pytest`.
5. **Chạy thử nhỏ:** crawl tối đa 20 JD, kiểm tra tay 3 bản ghi trong DB.
6. **Báo lại:** số JD crawl được, số lỗi parse, trường nào hay bị thiếu. Xong khi `python -m pytest` xanh và 3 bản ghi kiểm tay khớp trang gốc.
