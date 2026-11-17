# TopCV — quyền crawl và cấu trúc (kiểm tra 2026-11-17)

## robots.txt
`User-agent: *`, chỉ cấm các đường dẫn CV/riêng tư (`/xem-cv/`, `/private/`, `/cv-ung-vien/`, `/p/`...). Trang JD (`/viec-lam/...`) được phép. Không có `Crawl-delay`.

## Điều khoản ([terms-of-service](https://www.topcv.vn/terms-of-service), hiệu lực 01/04/2025)
- Không có điều khoản riêng về crawl/robot/công cụ tự động.
- §6 Sở hữu trí tuệ: không được "sao chép, sửa đổi, ... hiển thị, xuất bản, phân phối, ... khai thác Nội dung TopCV" khi chưa được cho phép bằng văn bản.

→ Áp dụng cùng điều kiện như ITviec: nội dung JD chỉ lưu cục bộ, phần công khai chỉ có số liệu tổng hợp + link.

## Cấu trúc
- Sitemap index `https://www.topcv.vn/sitemap/jobs.xml` → 199 sitemap con `jobs_0..198.xml`, ~200 URL mỗi file (~39.600 JD đang mở, **mọi ngành**).
- URL JD: `https://www.topcv.vn/viec-lam/{slug}/{id}.html`, `{id}` 6–7 chữ số.
- Trang JD có JSON-LD `JobPosting` đầy đủ: `title, hiringOrganization, datePosted, validThrough, skills, description` (mô tả + yêu cầu + quyền lợi), thêm `industry`, `baseSalary`. Parser chung `crawl/jobposting.py` chạy được nguyên vẹn.
- Trang JD nặng ~1,6MB (ITviec ~340KB).

## Đo được (2026-11-17)
- **Chặn bởi Cloudflare:** tải 46 sitemap con, cách nhau 2 giây → 2 lần trả 403 kèm trang challenge (`jobs_6`, `jobs_38`). Đã dừng theo quy tắc 403.
- 8.000 URL trong 40 sitemap đọc được → 100 URL khớp bộ lọc slug → ước tính ~500 cho cả TopCV.
- **Slug "data" ở TopCV nhiễu:** nhiều tin sales dùng "data" nghĩa là danh sách khách (`data-co-san`, `data-nong`), và "ai" trong tin dựng video AI. Ước tính nhẩm khoảng 1/3 số khớp là nhiễu. Cần lọc thêm theo `industry` trong JSON-LD (vd. chứa "Công nghệ thông tin" / "IT").

## Chưa biết
- Ngưỡng tốc độ của Cloudflare (403 do tốc độ hay ngẫu nhiên).
- Trang JD có bị challenge với cùng tốc độ không (mới tải 1 trang, thành công).
