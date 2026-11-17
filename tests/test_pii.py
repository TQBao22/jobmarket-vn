import pytest

from jobmarket.extract.pii import redact


@pytest.mark.parametrize("phone", ["0901234567", "090 123 4567", "0901.234.567", "+84 901 234 567", "024 3456 7890"])
def test_redacts_phone_formats(phone):
    assert redact(f"Liên hệ {phone} để ứng tuyển") == "Liên hệ [SĐT] để ứng tuyển"


def test_redacts_email():
    assert redact("Gửi CV về hr.lan@company.vn nhé") == "Gửi CV về [EMAIL] nhé"


@pytest.mark.parametrize("text", ["Lương 10.000.000 VND", "Hạn nộp 01/12/2026", "Kinh nghiệm 3-5 năm", "Python 3.12"])
def test_keeps_non_pii_numbers(text):
    assert redact(text) == text
