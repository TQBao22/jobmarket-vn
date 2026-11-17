"""Trích kỹ năng từ JD bằng `claude -p` (gói Claude đã đăng nhập, không API key). Quy tắc: `.claude/rules/llm-extraction.md`.

Chạy: python -m jobmarket.extract.llm --limit 20
Cần biến môi trường CLAUDE_BIN nếu `claude` không có trong PATH.
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, ValidationError

from jobmarket import db

MODEL = "claude-haiku-5-5"
PROMPT_VERSION = "v1"
PROMPTS = Path(__file__).parent / "prompts"
BATCH = 20
SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"jd_id": {"type": "string"}, "skills": {"type": "array", "items": {"type": "string"}}},
                "required": ["jd_id", "skills"],
            },
        }
    },
    "required": ["results"],
}


class _Item(BaseModel):
    jd_id: str
    skills: list[str]


class _Batch(BaseModel):
    results: list[_Item]


@dataclass
class Parsed:
    skills: dict[str, list[str]] = field(default_factory=dict)
    error: str | None = None
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


def content_hash(description: str) -> str:
    return hashlib.sha256(" ".join(description.split()).encode("utf-8")).hexdigest()


def _clean(skills: list[str]) -> list[str]:
    """Bỏ khoảng trắng thừa, chuỗi rỗng và mục trùng (không phân biệt hoa thường), giữ thứ tự."""
    seen, out = set(), []
    for s in (" ".join(s.split()) for s in skills):
        if s and s.casefold() not in seen:
            seen.add(s.casefold())
            out.append(s)
    return out


def parse_output(stdout: str, expected_ids: set[str]) -> Parsed:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        return Parsed(error=f"stdout không phải JSON: {e}")
    usage = data.get("usage") or {}
    parsed = Parsed(
        cost_usd=data.get("total_cost_usd"),
        input_tokens=sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
        output_tokens=usage.get("output_tokens"),
    )
    if data.get("is_error") or "structured_output" not in data:
        parsed.error = f"CLI lỗi hoặc thiếu structured_output: {str(data.get('result'))[:300]}"
        return parsed
    try:
        batch = _Batch.model_validate(data["structured_output"])
    except ValidationError as e:
        parsed.error = f"sai schema: {e.errors()[:3]}"
        return parsed
    parsed.skills = {i.jd_id: _clean(i.skills) for i in batch.results if i.jd_id in expected_ids}
    return parsed


def claude_runner(system: str, user_input: str) -> str:
    """Gọi `claude -p` ở chế độ tối giản; cwd là thư mục tạm trống để không nạp CLAUDE.md/plugin của project."""
    cmd = [
        os.environ.get("CLAUDE_BIN", "claude"), "-p", "Trích kỹ năng cho từng JD trong input theo schema.",
        "--setting-sources", "project", "--tools", "", "--strict-mcp-config", "--disable-slash-commands",
        "--no-session-persistence", "--max-turns", "2", "--model", MODEL,
        "--system-prompt", system, "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
    ]
    proc = subprocess.run(cmd, input=user_input, capture_output=True, text=True, encoding="utf-8",
                          cwd=tempfile.mkdtemp(), timeout=900)
    return proc.stdout or json.dumps({"is_error": True, "result": proc.stderr[-500:]})


def _build_input(batch: list[tuple[str, dict]]) -> str:
    return "\n\n".join(f"### JD {jd_id}\n{job['title']}\n{job['description']}" for jd_id, job in batch)


def extract(conn, model: str, prompt_version: str, system: str, limit: int | None = None,
            runner: Callable[[str, str], str] = claude_runner) -> Counter:
    """Trích cho mọi JD chưa có kết quả với (model, prompt_version); mỗi lô ≤20 JD là một lần gọi."""
    done = {r["content_hash"] for r in db.load_extractions(conn, model, prompt_version)}
    pending: dict[str, dict] = {}
    for job in db.load_all(conn):
        h = content_hash(job["description"] or "")
        if job["description"] and h not in done:
            pending.setdefault(h, job)
    todo = list(pending.items())[:limit]
    stats = Counter(pending=len(pending))
    for start in range(0, len(todo), BATCH):
        batch = [(h[:12], job) for h, job in todo[start:start + BATCH]]
        t0 = time.monotonic()
        parsed = parse_output(runner(system, _build_input(batch)), {i for i, _ in batch})
        call_id = db.save_call(conn, {
            "model": model, "prompt_version": prompt_version, "n_jd": len(parsed.skills),
            "cost_usd": parsed.cost_usd, "input_tokens": parsed.input_tokens, "output_tokens": parsed.output_tokens,
            "latency_ms": round((time.monotonic() - t0) * 1000), "error": parsed.error,
            "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        })
        if parsed.error:
            stats["failed_batches"] += 1
            continue
        for (jd_id, job), (h, _) in zip(batch, todo[start:start + BATCH]):
            if jd_id in parsed.skills:
                db.save_extraction(conn, h, model, prompt_version, job["url"], parsed.skills[jd_id], call_id)
                stats["extracted"] += 1
            else:
                stats["missing_in_output"] += 1  # JD thiếu sẽ được trích lại ở lần chạy sau
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--prompt", default=PROMPT_VERSION)
    ap.add_argument("--db", type=Path, default=Path("data/jobs.db"))
    args = ap.parse_args()
    system_prompt = (PROMPTS / f"{args.prompt}.txt").read_text(encoding="utf-8")
    print(dict(extract(db.connect(args.db), MODEL, args.prompt, system_prompt, args.limit)))
