"""Gộp tên kỹ năng đồng nghĩa về tên chuẩn bằng bảng `aliases.csv` (alias,canonical). Chạy lúc đọc, không ghi đè kết quả trích."""
import csv
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

ALIASES = Path(__file__).parent / "aliases.csv"


Table = dict[tuple[str, str], str]  # ("exact", tên đúng hoa thường) hoặc ("fold", tên hạ chữ thường) → tên chuẩn


def _squash(skill: str) -> str:
    return " ".join(skill.split())


def load_aliases(path: Path = ALIASES) -> Table:
    """Khớp đúng hoa thường trước (tách `ReAct` khỏi `React`), rồi mới khớp không phân biệt hoa thường."""
    table: Table = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["alias"].lstrip().startswith("#"):
                continue
            alias, canonical = _squash(row["alias"]), row["canonical"].strip()
            table["exact", alias] = canonical
            table["fold", alias.casefold()] = canonical
            table["exact", canonical] = canonical
            table["fold", canonical.casefold()] = canonical
    return table


def _lookup(skill: str, table: Table) -> str | None:
    s = _squash(skill)
    return table.get(("exact", s)) or table.get(("fold", s.casefold()))


def normalize(skill: str, table: Table) -> str:
    return _lookup(skill, table) or _squash(skill)


def normalize_all(skills: Iterable[str], table: Table) -> list[str]:
    return list(dict.fromkeys(normalize(s, table) for s in skills))


def unmapped(skill_lists: Iterable[list[str]], table: Table) -> Counter:
    return Counter(_squash(s) for skills in skill_lists for s in skills if _lookup(s, table) is None)
