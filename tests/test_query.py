import math

import pytest

from jobmarket import db, query
from jobmarket.extract import llm

TODAY = "2026-11-17"


def _db(tmp_path, jobs):
    """jobs: (slug, date_posted, valid_through, skills) → DB tạm với JD giả và kết quả trích của Claude."""
    conn = db.connect(tmp_path / "t.db")
    for slug, posted, until, skills in jobs:
        desc = f"mô tả giả {slug}"
        db.save(conn, {"url": f"https://x.test/{slug}", "source": "itviec", "title": slug, "company": "C", "date_posted": posted,
                       "valid_through": until, "tags": [], "description": desc, "fetched_at": "2026-11-17"})
        db.save_extraction(conn, llm.content_hash(desc), llm.MODEL, llm.PROMPT_VERSION, f"https://x.test/{slug}", skills, 0)
    return conn


@pytest.fixture
def conn(tmp_path):
    return _db(tmp_path, [
        ("a", "2026-10-01", "2026-12-01", ["Python", "Docker"]),
        ("b", "2026-11-05", "", ["Python", "SQL"]),
        ("c", "2026-11-10", "2026-11-01", ["Python", "Kubernetes"]),  # đã hết hạn
        ("d", "2026-11-12", "2026-11-17", ["Docker"]),  # hết hạn đúng hôm nay: vẫn mở
    ])


def test_health(conn):
    assert query.health(conn) == {"jobs": 4}


def test_top_skills_share_and_sort(conn):
    r = query.top_skills(conn, None, 20)
    assert r["months"] == ["2026-10", "2026-11"] and r["jd_total"] == 4
    assert r["skills"][0] == {"skill": "Python", "jd_count": 3, "share": 0.75}
    assert [s["skill"] for s in r["skills"]] == ["Python", "Docker", "Kubernetes", "SQL"]  # jd_count giảm, rồi tên tăng


def test_top_skills_month_and_limit(conn):
    r = query.top_skills(conn, "2026-11", 1)
    assert r["jd_total"] == 3 and r["skills"] == [{"skill": "Python", "jd_count": 2, "share": 0.667}]


def test_top_skills_unknown_month(conn):
    with pytest.raises(query.NotFound):
        query.top_skills(conn, "2020-01", 5)


def test_jobs_skill_case_insensitive_open_only(conn):
    r = query.jobs(conn, "pYtHoN", True, 50, TODAY)
    assert r["total"] == 2
    assert [j["title"] for j in r["jobs"]] == ["b", "a"]  # mới nhất trước
    assert r["jobs"][0].keys() == {"url", "title", "company", "date_posted", "valid_through", "skills"}
    assert query.jobs(conn, "Python", False, 50, TODAY)["total"] == 3


def test_jobs_limit_keeps_total(conn):
    r = query.jobs(conn, None, True, 1, TODAY)
    assert r["total"] == 3 and len(r["jobs"]) == 1 and r["jobs"][0]["title"] == "d"


def test_match_rare_skill_outweighs_common(tmp_path):
    c = _db(tmp_path, [("a", "2026-11-01", "", ["Python", "Rust"]), ("b", "2026-11-02", "", ["Python", "Go"]),
                       ("c", "2026-11-03", "", ["Python", "Go"])])
    m = query.match(c, ["Rust"], 10, TODAY)
    assert m[0]["title"] == "a"
    w_py, w_rust = math.log(3 / 3) + 1, math.log(3 / 1) + 1
    assert m[0]["score"] == pytest.approx(w_rust / (w_py + w_rust), abs=1e-3)
    assert m[0]["matched"] == ["Rust"] and m[0]["missing"] == ["Python"]


def test_match_order_and_exclusions(conn):
    m = query.match(conn, ["sql", "PYTHON"], 10, TODAY)
    assert {x["title"] for x in m} == {"a", "b", "d"}  # c đã đóng
    assert m[0]["title"] == "b" and m[0]["matched"] == ["SQL", "Python"]  # SQL hiếm hơn nên đứng trước
    a = next(x for x in m if x["title"] == "a")
    assert a["matched"] == ["Python"] and a["missing"] == ["Docker"]
    assert [x["score"] for x in m] == sorted((x["score"] for x in m), reverse=True)
    assert len(query.match(conn, ["Python"], 1, TODAY)) == 1


def test_jobs_without_skills_ignored(tmp_path):
    c = _db(tmp_path, [("a", "2026-11-01", "", [])])
    assert query.match(c, ["Python"], 10, TODAY) == []
