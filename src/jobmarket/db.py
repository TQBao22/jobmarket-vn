"""Lưu JD vào SQLite. Một dòng mỗi URL; lưu lại cùng URL thì ghi đè bằng giá trị mới."""
import json
import sqlite3

COLUMNS = ("url", "source", "title", "company", "date_posted", "valid_through", "tags", "description", "fetched_at")
_COLS = ", ".join(COLUMNS)


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS jobs (url TEXT PRIMARY KEY, source TEXT, title TEXT, company TEXT,"
        " date_posted TEXT, valid_through TEXT, tags TEXT, description TEXT, fetched_at TEXT);"
        "CREATE TABLE IF NOT EXISTS llm_calls (call_id INTEGER PRIMARY KEY AUTOINCREMENT, model TEXT, prompt_version TEXT,"
        " n_jd INTEGER, cost_usd REAL, input_tokens INTEGER, output_tokens INTEGER, latency_ms INTEGER, error TEXT, created_at TEXT);"
        # khoá chính = khoá cache: cùng nội dung JD + model + prompt thì không gọi LLM lần nữa
        "CREATE TABLE IF NOT EXISTS extractions (content_hash TEXT, model TEXT, prompt_version TEXT, url TEXT, skills TEXT,"
        " call_id INTEGER REFERENCES llm_calls(call_id), PRIMARY KEY (content_hash, model, prompt_version));"
    )
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
    conn.execute(f"INSERT OR REPLACE INTO jobs ({_COLS}) VALUES ({', '.join('?' * len(COLUMNS))})", [row[c] for c in COLUMNS])
    conn.commit()


def load_all(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(f"SELECT {_COLS} FROM jobs ORDER BY url")
    return [{**dict(zip(COLUMNS, r)), "tags": json.loads(r[COLUMNS.index("tags")])} for r in rows]
