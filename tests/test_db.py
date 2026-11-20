import json
import sqlite3

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
    assert db.load_all(conn) == [{**JOB, "last_seen": None}]


def test_save_same_url_twice_keeps_one_row_with_latest_values(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    db.save(conn, JOB)
    db.save(conn, {**JOB, "title": "AI Engineer (updated)"})
    rows = db.load_all(conn)
    assert len(rows) == 1
    assert rows[0]["title"] == "AI Engineer (updated)"


def _old_db(tmp_path):
    """DB tạo trước khi có cột last_seen."""
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE jobs (url TEXT PRIMARY KEY, source TEXT, title TEXT, company TEXT, date_posted TEXT,"
                " valid_through TEXT, tags TEXT, description TEXT, fetched_at TEXT)")
    old.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [json.dumps(JOB[c]) if c == "tags" else JOB[c] for c in db.COLUMNS])
    old.commit()
    old.close()
    return path


def test_connect_adds_last_seen_to_old_db(tmp_path):
    conn = db.connect(_old_db(tmp_path))
    assert db.load_all(conn) == [{**JOB, "last_seen": None}]
    db.mark_seen(conn, [JOB["url"]], "2026-11-22")
    assert db.load_all(conn)[0]["last_seen"] == "2026-11-22"


def test_load_all_reads_old_db_opened_read_only(tmp_path):
    # API/MCP mở DB chỉ đọc, không chạy migration: DB cũ vẫn đọc được
    ro = sqlite3.connect(f"{_old_db(tmp_path).as_uri()}?mode=ro", uri=True)
    assert db.load_all(ro) == [{**JOB, "last_seen": None}]


def test_save_keeps_last_seen(tmp_path):
    # crawl lần sau parse lại và ghi đè các trường của JD, không được xoá ngày thấy trên sitemap
    conn = db.connect(tmp_path / "jobs.db")
    db.save(conn, JOB)
    db.mark_seen(conn, [JOB["url"]], "2026-11-22")
    db.save(conn, {**JOB, "title": "AI Engineer (updated)"})
    row = db.load_all(conn)[0]
    assert row["title"] == "AI Engineer (updated)" and row["last_seen"] == "2026-11-22"
