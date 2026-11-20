"""Truy vấn chỉ đọc trên DB JD, dùng chung cho API (v3) và MCP server sau này. Quy tắc tính điểm: `docs/api.md`.

Kỹ năng của JD lấy từ extractions của `llm.MODEL` + `llm.PROMPT_VERSION`, chuẩn hoá lúc đọc; JD chưa được trích bị bỏ qua.
"""
import math
import sqlite3
from collections import Counter
from collections.abc import Iterable

from jobmarket import db
from jobmarket.aggregate import count_skills
from jobmarket.extract import llm
from jobmarket.normalize import load_aliases, normalize, normalize_all


class NotFound(Exception):
    pass


def _jobs_with_skills(conn) -> list[dict]:
    table = load_aliases()
    by_hash = {e["content_hash"]: e["skills"] for e in db.load_extractions(conn, llm.MODEL, llm.PROMPT_VERSION)}
    out = []
    for job in db.load_all(conn):
        raw = by_hash.get(llm.content_hash(job["description"] or ""))
        if raw is not None:
            out.append({**job, "skills": normalize_all(raw, table)})
    return out


def _is_open(job: dict, today: str) -> bool:
    return not job["valid_through"] or job["valid_through"] >= today  # ISO YYYY-MM-DD so sánh được theo chuỗi


def health(conn: sqlite3.Connection) -> dict:
    return {"jobs": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]}


def top_skills(conn, month: str | None, limit: int) -> dict:
    jobs = _jobs_with_skills(conn)
    by_desc = {j["description"]: j["skills"] for j in jobs}
    rows = count_skills(jobs, lambda d: by_desc.get(d), {})  # kỹ năng đã chuẩn hoá ở _jobs_with_skills
    months = sorted({r["month"] for r in rows if r["month"] != "?"})
    if month is not None and month not in months:
        raise NotFound(month)
    # mỗi (nguồn, tháng) là một nhóm riêng: cộng các nhóm được chọn, jd_total mỗi nhóm đếm một lần
    rows = [r for r in rows if month is None or r["month"] == month]
    totals = {(r["source"], r["month"]): r["jd_total"] for r in rows}
    jd_total = sum(totals.values())
    counts: Counter = Counter()
    for r in rows:
        counts[r["skill"]] += r["jd_count"]
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return {"months": months, "jd_total": jd_total,
            "skills": [{"skill": s, "jd_count": n, "share": round(n / jd_total, 3)} for s, n in top]}


def jobs(conn, skill: str | None, open_only: bool, limit: int, today: str) -> dict:
    want = normalize(skill, load_aliases()).casefold() if skill else None
    hits = [j for j in _jobs_with_skills(conn)
            if (not open_only or _is_open(j, today)) and (want is None or want in {s.casefold() for s in j["skills"]})]
    hits.sort(key=lambda j: j["date_posted"] or "", reverse=True)
    keys = ("url", "title", "company", "date_posted", "valid_through", "skills")
    return {"total": len(hits), "jobs": [{k: j[k] for k in keys} for j in hits[:limit]]}


LISTED_FACTOR = 0.5  # kỹ năng CV chỉ liệt kê, không có bằng chứng project/kinh nghiệm; chọn tay, không đo được


def match(conn, cv_skills: list[str], top_k: int, today: str, listed: Iterable[str] = ()) -> list[dict]:
    table = load_aliases()
    cv = {s.casefold() for s in normalize_all(cv_skills, table)}
    weak = {s.casefold() for s in normalize_all(listed, table)}
    open_jobs = [j for j in _jobs_with_skills(conn) if j["skills"] and _is_open(j, today)]
    df = Counter(s for j in open_jobs for s in j["skills"])
    weight = {s: math.log(len(open_jobs) / n) + 1 for s, n in df.items()}  # kỹ năng hiếm nặng hơn
    out = []
    for j in open_jobs:
        by_weight = sorted(j["skills"], key=lambda s: (-weight[s], s))
        matched = [s for s in by_weight if s.casefold() in cv]
        out.append({
            "url": j["url"], "title": j["title"], "company": j["company"],
            "score": round(sum(weight[s] * (LISTED_FACTOR if s.casefold() in weak else 1) for s in matched)
                           / sum(weight[s] for s in j["skills"]), 3),
            "matched": matched, "missing": [s for s in by_weight if s.casefold() not in cv],
        })
    out.sort(key=lambda m: (-m["score"], m["url"]))
    return out[:top_k]
