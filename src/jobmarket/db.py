"""Lưu JD vào SQLite. Một dòng mỗi URL; lưu lại cùng URL thì ghi đè các trường của JD bằng giá trị mới.

`last_seen`: ngày gần nhất JD còn trên sitemap của nguồn ở một lần crawl đủ; chỉ `mark_seen` ghi cột này."""
import json
import sqlite3

COLUMNS = ("url", "source", "title", "company", "date_posted", "valid_through", "tags", "description", "fetched_at")
_COLS = ", ".join(COLUMNS)


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS jobs (url TEXT PRIMARY KEY, source TEXT, title TEXT, company TEXT,"
        " date_posted TEXT, valid_through TEXT, tags TEXT, description TEXT, fetched_at TEXT, last_seen TEXT);"
        "CREATE TABLE IF NOT EXISTS llm_calls (call_id INTEGER PRIMARY KEY AUTOINCREMENT, model TEXT, prompt_version TEXT,"
        " n_jd INTEGER, cost_usd REAL, input_tokens INTEGER, output_tokens INTEGER, latency_ms INTEGER, error TEXT, created_at TEXT);"
        # khoá chính = khoá cache: cùng nội dung JD + model + prompt thì không gọi LLM lần nữa
        "CREATE TABLE IF NOT EXISTS extractions (content_hash TEXT, model TEXT, prompt_version TEXT, url TEXT, skills TEXT,"
        " call_id INTEGER REFERENCES llm_calls(call_id), PRIMARY KEY (content_hash, model, prompt_version));"
    )
    if "last_seen" not in {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}:  # DB tạo trước khi có cột
        conn.execute("ALTER TABLE jobs ADD COLUMN last_seen TEXT")
        conn.commit()
    return conn


def save_call(conn: sqlite3.Connection, call: dict) -> int:
    cols = ", ".join(call)
    cur = conn.execute(f"INSERT INTO llm_calls ({cols}) VALUES ({', '.join('?' * len(call))})", list(call.values()))
    conn.commit()
    return cur.lastrowid


def save_extraction(conn: sqlite3.Connection, content_hash: str, model: str, prompt_version: str, url: str, skills: list[str], call_id: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO extractions VALUES (?, ?, ?, ?, ?, ?)",
        (content_hash, model, prompt_version, url, json.dumps(skills, ensure_ascii=False), call_id),
    )
    conn.commit()


def load_extractions(conn: sqlite3.Connection, model: str, prompt_version: str) -> list[dict]:
    rows = conn.execute(
        "SELECT content_hash, url, skills FROM extractions WHERE model = ? AND prompt_version = ? ORDER BY url",
        (model, prompt_version),
    )
    return [{"content_hash": h, "url": u, "skills": json.loads(s)} for h, u, s in rows]


def save(conn: sqlite3.Connection, job: dict) -> None:
    row = {**job, "tags": json.dumps(job["tags"], ensure_ascii=False)}
    update = ", ".join(f"{c} = excluded.{c}" for c in COLUMNS[1:])  # không đụng last_seen
    conn.execute(f"INSERT INTO jobs ({_COLS}) VALUES ({', '.join('?' * len(COLUMNS))}) ON CONFLICT(url) DO UPDATE SET {update}",
                 [row[c] for c in COLUMNS])
    conn.commit()


def mark_seen(conn: sqlite3.Connection, urls: list[str], day: str) -> None:
    conn.executemany("UPDATE jobs SET last_seen = ? WHERE url = ?", [(day, u) for u in urls])
    conn.commit()


def load_all(conn: sqlite3.Connection) -> list[dict]:
    """Mọi JD; `last_seen` = None nếu chưa có hoặc DB cũ chưa có cột (API/MCP mở chỉ đọc, không chạy migration)."""
    cur = conn.execute("SELECT * FROM jobs ORDER BY url")
    cols = [d[0] for d in cur.description]
    return [{"last_seen": None, **dict(zip(cols, r)), "tags": json.loads(r[cols.index("tags")])} for r in cur]
