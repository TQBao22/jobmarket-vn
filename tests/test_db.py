from jobmarket import db

JOB = {
    "url": "https://itviec.com/viec-lam-it/ai-engineer-x-0001",
    "source": "itviec",
    "title": "AI Engineer",
    "company": "X",
    "date_posted": "2026-10-20",
    "valid_through": "2026-11-24",
    "tags": ["Python", "LLM"],
    "description": "Mô tả",
    "fetched_at": "2026-11-16T20:31:00+07:00",
}


def test_save_then_load_roundtrip(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    db.save(conn, JOB)
    assert db.load_all(conn) == [JOB]


def test_save_same_url_twice_keeps_one_row_with_latest_values(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    db.save(conn, JOB)
    db.save(conn, {**JOB, "title": "AI Engineer (updated)"})
    rows = db.load_all(conn)
    assert len(rows) == 1
    assert rows[0]["title"] == "AI Engineer (updated)"
