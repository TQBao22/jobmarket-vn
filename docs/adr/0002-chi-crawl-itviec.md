# ADR 0002 — Chỉ crawl ITviec, hạ mốc v1 từ 1.000 xuống ~120 JD

Ngày: 2026-11-17 · Trạng thái: đã chốt

## Bối cảnh
Tiêu chí v1 ban đầu: ≥1.000 JD, gold set 200 JD. ITviec chỉ có ~120 JD AI/Data đang mở (`docs/research/itviec.md`). Đã khảo sát 5 nguồn khác để bù (`docs/research/topcv.md`, `docs/research/nguon-khac.md`).

## Các lựa chọn
| Nguồn | Vì sao không dùng |
|---|---|
| TopCV | robots + điều khoản cho phép, nhưng Cloudflare trả 403 (challenge) ở 2/46 sitemap khi crawl 2 giây/request |
| TopDev | domain chính cắt TLS với client không phải trình duyệt; `api.topdev.vn` cấm trong robots |
| VietnamWorks | không có sitemap; danh sách JD chỉ lấy được qua API nội bộ |
| JobsGO | điều khoản mục VII.2 cấm robot/spider |
| CareerViet | điều khoản cấm "trình thu thập dữ liệu, người máy" |

Phương án còn lại: crawl TopCV chậm hơn (rủi ro bị chặn tiếp, trang challenge là tín hiệu họ không muốn bot); xin phép JobsGO bằng văn bản (chờ không biết bao lâu); crawl ITviec định kỳ để tích luỹ (mất nhiều tháng, ngoài lộ trình).

## Quyết định
Chỉ dùng ITviec. Mốc v1: toàn bộ JD AI/Data đang mở trên ITviec tại thời điểm crawl (124 JD ngày 2026-11-17). Gold set: 40 JD; ~84 JD còn lại dùng để viết và thử prompt.

## Lý do
- Giá trị project nằm ở eval và chi phí đo được, không ở số JD. 40 JD gold × ~10 kỹ năng/JD ≈ 400 cặp nhãn, đủ để F1 có ý nghĩa ở mức so sánh cấu hình.
- Chỉ crawl nguồn cho phép và truy cập được bằng User-Agent trung thực — cũng là một điểm đáng kể trong bài viết v4.

## Hệ quả
- Dashboard chỉ phản ánh thị trường IT qua ITviec, không phải toàn thị trường. Ghi rõ giới hạn này trên dashboard và trong bài viết.
- 124 JD là quá ít để fine-tune ở v2 nếu chỉ dùng JD gốc. Xem lại ở đầu v2 (crawl ITviec lặp lại để tích luỹ, hoặc xin phép JobsGO).
- `crawl/jobposting.py` (phần chung, tách ra khi thử TopCV) vẫn giữ: thêm nguồn có JSON-LD sau này chỉ cần một file cấu hình nhỏ.
