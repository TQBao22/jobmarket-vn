"""Phần chung cho mọi nguồn có khối JSON-LD `JobPosting`: fetch lịch sự, đọc sitemap, parse, vòng crawl lưu HTML gốc + SQLite."""
import datetime
import json
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

from jobmarket import db
from jobmarket.extract.pii import redact

UA = "jobmarket-vn-research/0.1"
DELAY_SECONDS = 2

_BLOCK_TAGS = {"p", "li", "br", "ul", "ol", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
_TAG_SEP = re.compile(r",(?![^()]*\))")  # dấu phẩy không nằm trong ngoặc


class _LdJson(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks: list[str] = []
        self._inside = False

    def handle_starttag(self, tag, attrs):
        self._inside = tag == "script" and ("type", "application/ld+json") in attrs
        if self._inside:
            self.blocks.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self._inside = False

    def handle_data(self, data):
        if self._inside:
            self.blocks[-1] += data


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def _to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    lines = (" ".join(line.split()) for line in "".join(p.parts).splitlines())
    return "\n".join(line for line in lines if line)


def _job_posting(html: str) -> dict | None:
    p = _LdJson()
    p.feed(html)
    for block in p.blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            return data
    return None


def _squash(value: str | None) -> str | None:
    """Bỏ khoảng trắng thừa ở hai đầu và giữa các từ; chuỗi rỗng → None."""
    return " ".join(value.split()) or None if value else None


def parse(html: str) -> dict | None:
    """Trả về các trường của JD, hoặc None nếu trang không có JobPosting. Trường thiếu → None."""
    job = _job_posting(html)
    if job is None:
        return None
    skills = job.get("skills")
    description = job.get("description")
    return {
        "title": _squash(job.get("title")),
        "company": _squash((job.get("hiringOrganization") or {}).get("name")),
        "date_posted": job.get("datePosted"),
        "valid_through": job.get("validThrough"),
        "tags": [s.strip() for s in _TAG_SEP.split(skills) if s.strip()] if skills else None,
        "description": _to_text(description) if description else None,
    }


class Blocked(Exception):
    """Trang trả 403: dừng crawl cả domain và báo người dùng."""


def fetch(url: str, opener=urllib.request.urlopen, sleep=time.sleep) -> bytes | None:
    """GET có User-Agent; 429/5xx thử lại tối đa 3 lần (chờ 2, 4, 8 giây); 403 → Blocked; 4xx khác → None."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with opener(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise Blocked(url) from e
            if e.code != 429 and e.code < 500:
                return None
            if attempt == 3:
                raise
            sleep(2 * 2**attempt)


def job_urls(sitemap_xml) -> list[str]:
    """Mọi `<loc>` trong sitemap; với sitemap index thì đây là URL các sitemap con."""
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    return [loc.text.strip() for loc in ET.fromstring(sitemap_xml).iter(f"{ns}loc")]


def crawl(
    source: str,
    robots_url: str,
    list_urls: Callable[[], list[str]],
    raw_name: Callable[[str], str],
    limit: int,
    raw_dir: Path,
    db_path: Path,
) -> Counter:
    """Kiểm robots → lấy danh sách URL → tải (bỏ qua nếu đã có HTML gốc) → parse → lọc PII → lưu DB."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(fetch(robots_url).decode("utf-8").splitlines())
    time.sleep(DELAY_SECONDS)
    urls = list_urls()
    conn, stats = db.connect(db_path), Counter(candidates=len(urls))
    for url in urls[:limit]:
        if not robots.can_fetch(UA, url):
            stats["robots_disallowed"] += 1
            continue
        name = raw_name(url)
        page, meta_path = raw_dir / f"{name}.html", raw_dir / f"{name}.meta.json"
        if page.exists():  # đã có bản gốc: không tải lại, không ghi đè
            stats["reused_raw"] += 1
        else:
            time.sleep(DELAY_SECONDS)
            body = fetch(url)
            if body is None:
                stats["not_found"] += 1
                continue
            page.write_bytes(body)
            now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
            meta_path.write_text(json.dumps({"url": url, "fetched_at": now}), encoding="utf-8")
            stats["fetched"] += 1
        job = parse(page.read_text(encoding="utf-8"))
        if job is None:
            stats["parse_failed"] += 1
            continue
        if job["description"]:
            job["description"] = redact(job["description"])
        fetched_at = json.loads(meta_path.read_text(encoding="utf-8"))["fetched_at"]
        db.save(conn, {"url": url, "source": source, **job, "fetched_at": fetched_at})
        stats["saved"] += 1
    return stats
