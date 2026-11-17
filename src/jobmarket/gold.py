"""Gold set: chọn JD để gán nhãn tay và đọc nhãn. File nhãn chỉ chứa url + title + skills, không chép nội dung JD.

  python -m jobmarket.gold init        # chọn 40 JD, tạo data/gold/labels.jsonl (skills: null = chưa gán)
  python -m jobmarket.gold show 3      # in nội dung JD thứ 3 (đánh số từ 1) để gán nhãn
  python -m jobmarket.gold status      # đã gán bao nhiêu JD

Gán nhãn: sửa `"skills": null` thành danh sách kỹ năng kỹ thuật, vd. `["Python", "Docker"]` (định nghĩa: GLOSSARY.md).
"""
import hashlib
import json
import sys
from pathlib import Path

from jobmarket import db

LABELS = Path("data/gold/labels.jsonl")
SIZE = 40


def select(urls: list[str], n: int) -> list[str]:
    """n URL đầu tiên theo sha256(url): cố định, không phụ thuộc thứ tự đầu vào hay thời điểm chạy."""
    return sorted(urls, key=lambda u: hashlib.sha256(u.encode()).hexdigest())[:n]


def init(jobs: list[dict], path: Path = LABELS, n: int = SIZE) -> None:
    if path.exists():
        raise FileExistsError(f"{path} đã có — không ghi đè nhãn đã gán")
    chosen = set(select([j["url"] for j in jobs], n))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for j in sorted((j for j in jobs if j["url"] in chosen), key=lambda j: j["url"]):
            f.write(json.dumps({"url": j["url"], "title": j["title"], "skills": None}, ensure_ascii=False) + "\n")


def _entries(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load(path: Path = LABELS) -> dict[str, list[str] | None]:
    return {e["url"]: e["skills"] for e in _entries(path)}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    conn = db.connect("data/jobs.db")
    if cmd == "init":
        init(db.load_all(conn))
        print(f"Đã tạo {LABELS} với {SIZE} JD chưa gán nhãn")
    elif cmd == "show":
        entry = _entries(LABELS)[int(sys.argv[2]) - 1]
        job = next(j for j in db.load_all(conn) if j["url"] == entry["url"])
        print(f"{job['title']} | {job['company']}\n{job['url']}\n\n{job['description']}")
    else:
        labels = load()
        print(f"{sum(v is not None for v in labels.values())}/{len(labels)} JD đã gán nhãn")
