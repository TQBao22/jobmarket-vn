# JobMarket VN

Thuật ngữ dùng thống nhất trong code, tài liệu và bài viết về thị trường việc làm AI/Data ở Việt Nam.

## Dữ liệu tuyển dụng

**JD**:
Một tin tuyển dụng, định danh bằng URL trên trang nguồn.
_Avoid_: job, bài đăng, posting

**Nguồn**:
Một trang tuyển dụng được crawl (ITviec, ...).
_Avoid_: site, provider

**HTML gốc**:
Trang JD đúng như lúc tải về, chưa parse.
_Avoid_: raw page, snapshot

**Thẻ**:
Danh sách kỹ năng do nguồn tự gắn cho JD (trường `skills` trong JSON-LD của ITviec); có lẫn mục không phải kỹ năng như "English", "Fresher Accepted".
_Avoid_: tag ITviec, nhãn (nhãn dành cho gold set)

**PII**:
Thông tin cá nhân của người tuyển dụng trong JD: tên, số điện thoại, email.

## Kỹ năng

**Kỹ năng**:
Kỹ năng kỹ thuật mà JD yêu cầu hoặc ưu tiên: ngôn ngữ lập trình, framework/thư viện/công cụ, nền tảng/cloud, kỹ thuật hoặc lĩnh vực (Machine Learning, RAG, ETL). Không gồm kỹ năng mềm, ngoại ngữ, bằng cấp, số năm kinh nghiệm.
_Avoid_: yêu cầu, requirement

**Kỹ năng thô**:
Chuỗi kỹ năng đúng như LLM (hoặc nguồn) trả về, chưa chuẩn hoá.
_Avoid_: raw skill

**Tên chuẩn**:
Tên duy nhất đại diện cho một kỹ năng sau chuẩn hoá; ưu tiên nhãn ESCO.
_Avoid_: canonical name, kỹ năng chuẩn hoá

**Alias**:
Một cách viết khác của cùng kỹ năng, ánh xạ về một tên chuẩn (`py` → `Python`).
_Avoid_: từ đồng nghĩa, synonym

**Lần trích**:
Kết quả trích kỹ năng của một JD với một model và một phiên bản prompt cố định.
_Avoid_: extraction run, inference

## Đánh giá

**Gold set**:
Tập JD được người gán tay danh sách tên chuẩn; chỉ dùng để chấm điểm.
_Avoid_: test set, ground truth

**Nhãn**:
Danh sách tên chuẩn gán tay cho một JD trong gold set.

**Baseline**:
Cách trích đơn giản nhất dùng làm mốc so sánh; baseline đầu tiên là thẻ của nguồn.

**Cấu hình**:
Cách hệ thống chọn model để trích: `api` (chỉ Claude), `local` (chỉ model nhỏ), `routing` (router chọn).
_Avoid_: setup, mode

**Chi phí quy đổi**:
Số tiền một lần trích sẽ tốn nếu trả theo giá API niêm yết (`total_cost_usd`), dù thực tế chạy bằng hạn mức gói Claude.
_Avoid_: chi phí thật, cost
