"""Crawl ITviec: URL JD lấy từ một sitemap phẳng, lọc AI/Data theo slug. Phần chung: `jobposting.py`.

Chạy: python -m jobmarket.crawl.itviec --limit 20
"""
import argparse
import re
from pathlib import Path

from jobmarket.crawl import jobposting

ROBOTS = "https://itviec.com/robots.txt"
SITEMAP = "https://itviec.com/twinnings_jobs_desc_vn.xml"
# shortcut: lọc AI/Data theo slug URL, có thể sót JD có slug không chứa từ khoá; crawl hết rồi lọc theo `tags` nếu thiếu JD.
_AI_DATA_SLUG = re.compile(r"(?:^|-)(?:ai|ml|llm|nlp|genai|data|machine-learning|deep-learning|computer-vision)(?:-|$)")


def raw_name(url: str) -> str:
    return url.rsplit("/", 1)[1]


def list_urls() -> list[str]:
    return [u for u in jobposting.job_urls(jobposting.fetch(SITEMAP)) if _AI_DATA_SLUG.search(raw_name(u))]


def crawl(limit: int, raw_dir=Path("data/raw/itviec"), db_path=Path("data/jobs.db")):
    return jobposting.crawl("itviec", ROBOTS, list_urls, raw_name, limit, raw_dir, db_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=20)
    print(dict(crawl(ap.parse_args().limit)))
