from pathlib import Path

import pytest

import io
import urllib.error

from jobmarket.crawl.jobposting import Blocked, fetch, job_urls, parse

FIXTURES = Path(__file__).parent / "fixtures" / "itviec"
URL = "https://itviec.com/viec-lam-it/x-0001"
SAMPLES = sorted(FIXTURES.glob("*.html"))


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.stem[:30])
def test_parse_core_fields_not_empty(path):
    job = parse(path.read_text(encoding="utf-8"))
    assert job["title"]
    assert job["company"]
    assert job["description"]


def test_parse_values_from_job_posting():
    job = parse(load("ai-engineer-llm-python-docker-api-rag-vietinbank-0426.html"))
    assert job["title"] == "AI Engineer LLM, Python, Docker, API, RAG"
    assert job["company"] == "VietinBank"
    assert job["date_posted"] == "2026-10-20"
    assert job["valid_through"] == "2026-11-24"
    assert job["tags"] == ["Generative AI", "API", "Docker", "Python", "RAG", "LLM"]


def test_description_is_plain_text():
    job = parse(load("senior-data-engineer-kingfoodmart-4145.html"))
    assert "<" not in job["description"]
    assert "Skills & Experience" in job["description"]  # &amp; đã được giải mã


def test_page_without_job_posting_returns_none():
    assert parse("<html><head><title>404</title></head><body></body></html>") is None


def test_job_urls_reads_loc_entries_from_sitemap():
    xml = (
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://itviec.com/viec-lam-it/a-0001</loc></url>"
        "<url><loc>https://itviec.com/viec-lam-it/b-0002</loc></url></urlset>"
    )
    assert job_urls(xml) == ["https://itviec.com/viec-lam-it/a-0001", "https://itviec.com/viec-lam-it/b-0002"]


def _http_error(code):
    return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(b""))


class FakeOpener:
    """Trả lần lượt các phản hồi cho trước: bytes = 200 OK, int = mã lỗi HTTP."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def __call__(self, req, timeout):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, int):
            raise _http_error(r)
        return io.BytesIO(r)


def test_fetch_retries_on_429_then_returns_body():
    opener, waits = FakeOpener(429, 503, b"<html>ok</html>"), []
    assert fetch(URL, opener=opener, sleep=waits.append) == b"<html>ok</html>"
    assert opener.calls == 3
    assert waits == [2, 4]


def test_fetch_gives_up_after_3_retries():
    opener = FakeOpener(500, 500, 500, 500)
    with pytest.raises(urllib.error.HTTPError):
        fetch(URL, opener=opener, sleep=lambda s: None)
    assert opener.calls == 4


def test_fetch_403_raises_blocked_without_retry():
    opener = FakeOpener(403)
    with pytest.raises(Blocked):
        fetch(URL, opener=opener, sleep=lambda s: None)
    assert opener.calls == 1


def test_fetch_404_returns_none():
    assert fetch(URL, opener=FakeOpener(404), sleep=lambda s: None) is None


def test_parse_strips_whitespace_around_title_and_company():
    page = (
        '<script type="application/ld+json">{"@type": "JobPosting", "title": " AI Engineer ",'
        ' "hiringOrganization": {"name": "Home Credit Vietnam "}}</script>'
    )
    job = parse(page)
    assert job["title"] == "AI Engineer"
    assert job["company"] == "Home Credit Vietnam"


def test_parse_tags_keep_commas_inside_parentheses():
    page = '<script type="application/ld+json">{"@type": "JobPosting", "skills": "SQL, Trực quan hóa (Tableau, Power BI), DA"}</script>'
    assert parse(page)["tags"] == ["SQL", "Trực quan hóa (Tableau, Power BI)", "DA"]
