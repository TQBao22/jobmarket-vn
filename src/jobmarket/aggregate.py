"""Đếm số JD có mỗi kỹ năng (đã chuẩn hoá) theo nguồn và tháng đăng → CSV công khai.

Chỉ xuất số đếm, không xuất nội dung JD (điều khoản ITviec §2.2).
Chạy: python -m jobmarket.aggregate
"""
import csv
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

from jobmarket import db
from jobmarket.extract import llm
from jobmarket.normalize import load_aliases, normalize_all

OUT = Path("data/public/skill_counts.csv")
FIELDS = ["source", "month", "skill", "jd_count", "jd_total"]


def count_skills(jobs: list[dict], skills_for: Callable[[str], list[str] | None], table) -> list[dict]:
    """`skills_for(description)` trả kỹ năng thô của JD, hoặc None nếu JD chưa được trích (không tính vào tổng)."""
    counts: dict[tuple, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    spellings: dict[str, Counter] = defaultdict(Counter)  # tên chưa có trong bảng alias: gộp theo chữ thường
    for job in jobs:
        skills = skills_for(job["description"])
        if skills is None:
            continue
        group = (job["source"], (job["date_posted"] or "")[:7] or "?")
        totals[group] += 1
        keys = {s.casefold(): s for s in normalize_all(skills, table)}
        counts[group].update(keys.keys())
        for k, s in keys.items():
            spellings[k][s] += 1
    display = {k: c.most_common(1)[0][0] for k, c in spellings.items()}
    rows = [
        {"source": g[0], "month": g[1], "skill": display[k], "jd_count": n, "jd_total": totals[g]}
        for g, c in counts.items() for k, n in c.items()
    ]
    return sorted(rows, key=lambda r: (r["source"], r["month"], -r["jd_count"], r["skill"]))


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    conn = db.connect("data/jobs.db")
    by_hash = {e["content_hash"]: e["skills"] for e in db.load_extractions(conn, llm.MODEL, llm.PROMPT_VERSION)}
    rows = count_skills(db.load_all(conn), lambda d: by_hash.get(llm.content_hash(d or "")), load_aliases())
    write_csv(rows, OUT)
    print(f"{len(rows)} dòng → {OUT}")
