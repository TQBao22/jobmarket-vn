"""Crawl ITviec: tải mọi JD trong một sitemap phẳng, chỉ lưu DB JD AI/Data (lọc theo nội dung). Phần chung: `jobposting.py`.

Chạy: python -m jobmarket.crawl.itviec --limit 20
"""
import argparse
import re
from pathlib import Path

from jobmarket.crawl import jobposting

ROBOTS = "https://itviec.com/robots.txt"
SITEMAP = "https://itviec.com/twinnings_jobs_desc_vn.xml"
# Vai trò lấy từ tiêu đề. Không lọc theo mô tả: đo trên 603 JD (2026-11-17), luật "≥3 thuật ngữ ML/Data
# trong mô tả" chỉ thêm JD backend/SRE có nhắc ETL, Airflow. Tiêu đề ITviec hay bỏ dấu → có cả dạng không dấu.
_TITLE = re.compile(
    r"\b(?:ai|a\.i\.|ml|llm|nlp|genai|gen ai|data|bi|business intelligence|analytics|scientist|"
    r"machine learning|deep learning|computer vision|mlops|llmops|big data|etl|chatbot|rag|agentic|"
    r"dữ liệu|du lieu|học máy|hoc may|mô hình|mo hinh|trí tuệ nhân tạo|tri tue nhan tao|thị giác máy tính)\b"
)


def is_ai_data(job: dict) -> bool:
    return bool(_TITLE.search(job["title"].casefold()))


def raw_name(url: str) -> str:
    return url.rsplit("/", 1)[1]


def list_urls() -> list[str]:
    return jobposting.job_urls(jobposting.fetch(SITEMAP))


def crawl(limit: int, raw_dir=Path("data/raw/itviec"), db_path=Path("data/jobs.db")):
    return jobposting.crawl("itviec", ROBOTS, list_urls, raw_name, limit, raw_dir, db_path, keep=is_ai_data)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=20)
    print(dict(crawl(ap.parse_args().limit)))
