"""Chấm trích xuất kỹ năng trên gold set: precision, recall, F1 micro sau chuẩn hoá. Skill `run-eval` dùng lệnh này.

  python -m jobmarket.evaluate --system llm           # kết quả LLM (model + prompt hiện tại)
  python -m jobmarket.evaluate --system tags          # baseline: thẻ ITviec
  python -m jobmarket.evaluate --system llm --append  # thêm 1 dòng vào eval/RESULTS.md
"""
import argparse
import datetime
import statistics
from pathlib import Path

from jobmarket import db, gold
from jobmarket.extract import llm
from jobmarket.normalize import load_aliases, normalize_all

RESULTS = Path("eval/RESULTS.md")
HEADER = (
    "| ngày | cấu hình | model | prompt | P | R | F1 | chi phí /1.000 JD | độ trễ p50 | ghi chú |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
)


def score(labels: dict[str, list[str] | None], preds: dict[str, list[str]], table) -> dict:
    """So khớp không phân biệt hoa thường sau chuẩn hoá. JD chưa gán nhãn bị bỏ qua; JD thiếu dự đoán tính là rỗng."""
    tp = fp = fn = 0
    per_jd = []
    labeled = {u: s for u, s in labels.items() if s is not None}
    for url, truth in labeled.items():
        t = {s.casefold(): s for s in normalize_all(truth, table)}
        p = {s.casefold(): s for s in normalize_all(preds.get(url, []), table)}
        tp += len(t.keys() & p.keys())
        missed, extra = sorted(t[k] for k in t.keys() - p.keys()), sorted(p[k] for k in p.keys() - t.keys())
        fn, fp = fn + len(missed), fp + len(extra)
        per_jd.append({"url": url, "missed": missed, "extra": extra})
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "p": prec, "r": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "tp": tp, "fp": fp, "fn": fn, "n_jd": len(labeled),
        "missing_pred": sum(u not in preds for u in labeled),
        "worst": sorted(per_jd, key=lambda d: -(len(d["missed"]) + len(d["extra"])))[:5],
    }


def _cost_and_latency(conn, model: str, prompt: str) -> tuple[str, str]:
    rows = conn.execute(
        "SELECT cost_usd, n_jd, latency_ms FROM llm_calls WHERE model = ? AND prompt_version = ? AND error IS NULL",
        (model, prompt),
    ).fetchall()
    n = sum(r[1] for r in rows)
    if not n:
        return "—", "—"
    return f"${sum(r[0] or 0 for r in rows) / n * 1000:.2f}", f"{statistics.median(r[2] for r in rows) / 1000:.0f}s/lô"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--system", choices=["llm", "tags"], default="llm")
    ap.add_argument("--prompt", default=llm.PROMPT_VERSION)
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    conn = db.connect("data/jobs.db")
    jobs = db.load_all(conn)
    if args.system == "tags":
        preds = {j["url"]: j["tags"] or [] for j in jobs}
        config, model, prompt, cost, latency = "baseline", "thẻ ITviec", "—", "$0", "—"
    else:
        by_hash = {e["content_hash"]: e["skills"] for e in db.load_extractions(conn, llm.MODEL, args.prompt)}
        preds = {j["url"]: by_hash[h] for j in jobs if (h := llm.content_hash(j["description"] or "")) in by_hash}
        config, model, prompt = "api", llm.MODEL, args.prompt
        cost, latency = _cost_and_latency(conn, llm.MODEL, args.prompt)
    r = score(gold.load(), preds, load_aliases())
    if r["n_jd"] == 0:
        raise SystemExit("Gold set chưa có JD nào được gán nhãn — xem `python -m jobmarket.gold`.")
    print(f"{args.system}: P={r['p']:.3f} R={r['r']:.3f} F1={r['f1']:.3f} trên {r['n_jd']} JD (thiếu dự đoán: {r['missing_pred']})")
    for d in r["worst"]:
        print(f"- {d['url']}\n  sót: {d['missed']}\n  thừa: {d['extra']}")
    note = f"{r['n_jd']} JD gold. {args.note}".strip()
    row = f"| {datetime.date.today()} | {config} | {model} | {prompt} | {r['p']:.3f} | {r['r']:.3f} | {r['f1']:.3f} | {cost} | {latency} | {note} |\n"
    print(row, end="")
    if args.append:
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS, "a", encoding="utf-8") as f:
            if f.tell() == 0:
                f.write("# Kết quả eval trích kỹ năng\n\nChỉ thêm dòng, không sửa dòng cũ.\n\n" + HEADER)
            f.write(row)
