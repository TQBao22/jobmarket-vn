# Nguồn crawl thứ hai — khảo sát (2026-11-17)

Bối cảnh: TopCV trả 403 (Cloudflare) ở 2/46 sitemap khi crawl 2 giây/request (`topcv.md`). Người dùng chọn tìm nguồn khác.

| Nguồn | robots.txt | Danh sách JD | JSON-LD `JobPosting` | Kết luận |
|---|---|---|---|---|
| TopDev | `www.topdev.vn`: cho phép hết; `api.topdev.vn`: cấm hết | Trang thật ở `topdev.vn`, domain này **cắt TLS** với curl/urllib; `www` chuyển hướng về trang đăng nhập | chưa xem được | Loại: chỉ vào được bằng cách giả lập trình duyệt (trái `crawling.md`) |
| VietnamWorks | không có (404) | Không có sitemap; trang tìm kiếm chỉ render tổng số (`nbHits`), danh sách tải bằng JS qua API nội bộ | chưa xem | Loại: phải gọi API nội bộ không công bố |
| JobsGO | cho phép, chỉ cấm `/candidate*`, `/access/*`... | Trang danh mục `/viec-lam-du-lieu-ai-hoc-may.html` render sẵn link JD; sitemap 22.681 JD mọi ngành | Có, thêm `industry`; không có `skills` | **Loại: điều khoản cấm robot/spider** (xem dưới) |
| CareerViet | cho phép `/vi/tim-viec-lam/...` (cấm `/vi/jobs/*`, `/api/*`) | chưa xem (đọc điều khoản trước) | chưa xem | **Loại: điều khoản cấm "trình thu thập dữ liệu, người máy"** |

CareerViet, [Điều khoản sử dụng](https://careerviet.vn/vi/jobseekers/use): "việc sử dụng hay cố gắng sử dụng bất cứ máy móc, phần mềm, công cụ ... (bao gồm nhưng không giới hạn trình duyệt, trình thu thập dữ liệu, người máy ...) để đánh dấu hoặc tìm ra bất cứ Trang Web CareerViet nào ngoài các công cụ tìm kiếm ... có sẵn" — bị ngăn cấm.

**Kết luận:** không có nguồn thứ hai vừa cho phép crawl vừa truy cập được bằng client trung thực. Quyết định: ADR 0002.

## JobsGO — điều khoản cấm crawl
[Điều khoản dành cho ứng viên v2.0](https://jobsgo.vn/doc/terms) (PDF), mục VII.2 "Những hành vi bị nghiêm cấm":
> "Sử dụng các loại robot, nhện máy (spiders) và/hoặc bất kỳ thiết bị tự động nào, và/hoặc tự tay theo dõi và thu thập tài liệu của website cho bất kỳ mục đích tái sử dụng mà không được sự cho phép trước bằng văn bản của JobsGO"

→ Không crawl. Muốn dùng phải xin phép bằng văn bản (contact@jobsgo.vn).
Bài học: lần khảo sát này đã tải ~6 trang JobsGO trước khi đọc điều khoản (đã xoá). Thứ tự đúng theo skill `add-source`: điều khoản trước, tải sau.
Số đo trước khi loại: danh mục "Dữ Liệu - AI - Học Máy" có 123 JD (T11/2026).

## Quy mô thị trường
Một lần chụp ở mỗi nguồn: ITviec 124, JobsGO 123, TopCV ước ~300–500 (sau khi lọc nhiễu), VietnamWorks 541 kết quả cho "data" (nhiễu). Gộp lại và bỏ trùng khó đạt 1.000 JD đang mở cùng lúc.
