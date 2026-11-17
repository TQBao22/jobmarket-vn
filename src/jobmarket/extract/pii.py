"""Lọc thông tin cá nhân khỏi nội dung JD trước khi lưu DB hoặc gửi LLM."""
import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Số VN: +84 hoặc 0 đầu, 9–11 chữ số, cho phép dấu cách/chấm giữa các nhóm.
_PHONE = re.compile(r"(?:\+84|(?<!\d)0)(?:[\s.]?\d){8,10}(?!\d)")


def redact(text: str) -> str:
    # shortcut: chưa lọc tên người (regex không nhận ra tên); thêm NER nếu kiểm tay thấy tên người tuyển dụng trong JD.
    return _PHONE.sub("[SĐT]", _EMAIL.sub("[EMAIL]", text))
