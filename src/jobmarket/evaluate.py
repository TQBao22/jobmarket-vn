"""Chấm trích xuất kỹ năng trên gold set: precision, recall, F1 micro sau chuẩn hoá. Skill `run-eval` dùng lệnh này.

  python -m jobmarket.evaluate --system llm           # kết quả LLM (model + prompt hiện tại)
  python -m jobmarket.evaluate --system tags          # baseline: thẻ ITviec
  python -m jobmarket.evaluate --system llm --append  # thêm 1 dòng vào eval/RESULTS.md
  python -m jobmarket.evaluate --split test           # mặc định chấm nửa dev; test chỉ chạy khi chốt cấu hình
  python -m jobmarket.evaluate --model qwen3:8b-think --vs qwen3:8b   # thêm ΔF1 ghép cặp so với model khác

F1 kèm khoảng tin cậy 95% bootstrap theo JD: 20 JD dev cho sai số lớn, chênh lệch có khoảng chứa 0 thì chưa kết luận được.
"""
import argparse
import datetime
import random
import statistics
from collections.abc import Callable
from pathlib import Path

from jobmarket import db, gold
from jobmarket.extract import llm
from jobmarket.normalize import load_aliases, normalize_all

RESULTS = Path("eval/RESULTS.md")
HEADER = (
    "| ngày | cấu hình | model | prompt | P | R | F1 | chi phí /1.000 JD | độ trễ p50 | ghi chú |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
)
BOOT_ROUNDS = 2000  # số lần lấy mẫu lại; seed cố định để chạy lại ra cùng khoảng


def _per_jd(labels: dict[str, list[str] | None], preds: dict[str, list[str]], table) -> list[dict]:
    """Mỗi JD có nhãn: số kỹ năng đúng, kỹ năng sót, kỹ năng thừa. JD chưa gán nhãn bị bỏ qua; JD thiếu dự đoán tính là rỗng."""
    out = []
    for url, truth in labels.items():
        if truth is None:
            continue
        t = {s.casefold(): s for s in normalize_all(truth, table)}
        p = {s.casefold(): s for s in normalize_all(preds.get(url, []), table)}
        out.append({"url": url, "tp": len(t.keys() & p.keys()),
                    "missed": sorted(t[k] for k in t.keys() - p.keys()), "extra": sorted(p[k] for k in p.keys() - t.keys())})
    return out


def _f1(jds: list[dict]) -> float:
    tp = sum(d["tp"] for d in jds)
    wrong = sum(len(d["missed"]) + len(d["extra"]) for d in jds)
    return 2 * tp / (2 * tp + wrong) if tp else 0.0


def _ci(stat: Callable[[list[int]], float], n: int) -> tuple[float, float]:
    """Khoảng tin cậy 95% bootstrap: lấy mẫu lại n JD có hoàn lại BOOT_ROUNDS lần, lấy phân vị 2,5% và 97,5% của `stat`."""
    rng = random.Random(0)
    vals = sorted(stat([rng.randrange(n) for _ in range(n)]) for _ in range(BOOT_ROUNDS))
    return vals[int(0.025 * BOOT_ROUNDS)], vals[int(0.975 * BOOT_ROUNDS)]


def score(labels: dict[str, list[str] | None], preds: dict[str, list[str]], table) -> dict:
    """P, R, F1 micro, so khớp không phân biệt hoa thường sau chuẩn hoá; `f1_ci`: khoảng tin cậy 95% bootstrap theo JD."""
    jds = _per_jd(labels, preds, table)
    tp = sum(d["tp"] for d in jds)
    fp, fn = sum(len(d["extra"]) for d in jds), sum(len(d["missed"]) for d in jds)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "p": prec, "r": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "f1_ci": _ci(lambda idx: _f1([jds[i] for i in idx]), len(jds)) if jds else (0.0, 0.0),
        "tp": tp, "fp": fp, "fn": fn, "n_jd": len(jds),
        "missing_pred": sum(d["url"] not in preds for d in jds),
        "worst": [{k: d[k] for k in ("url", "missed", "extra")}
                  for d in sorted(jds, key=lambda d: -(len(d["missed"]) + len(d["extra"])))[:5]],
    }


def compare(labels: dict[str, list[str] | None], preds_a: dict[str, list[str]], preds_b: dict[str, list[str]], table) -> dict:
    """F1(A) − F1(B) trên cùng các JD, khoảng tin cậy 95% bootstrap ghép cặp (mỗi lần lấy mẫu dùng chung JD cho A và B)."""
    a, b = _per_jd(labels, preds_a, table), _per_jd(labels, preds_b, table)

    def diff(idx):
        return _f1([a[i] for i in idx]) - _f1([b[i] for i in idx])
    return {"diff": diff(range(len(a))), "ci": _ci(diff, len(a)) if a else (0.0, 0.0)}


def _cost_and_latency(conn, model: str, prompt: str) -> tuple[str, str]:
    """Chi phí /1.000 JD tính cả lần gọi lỗi (vẫn tốn tiền, không ra JD nào). Độ trễ = trung vị của (thời gian một lần gọi
    ÷ số JD lần đó trả về), đơn vị s/JD để so được Claude (20 JD/lần gọi) với model local (1 JD/lần); lần lỗi báo riêng."""
    rows = conn.execute(
        "SELECT cost_usd, n_jd, latency_ms, error FROM llm_calls WHERE model = ? AND prompt_version = ?", (model, prompt),
    ).fetchall()
    n = sum(r[1] or 0 for r in rows)
    ok = [r[2] / r[1] for r in rows if r[3] is None and r[1]]
    if not n or not ok:
        return "—", "—"
    failed = [r[2] for r in rows if r[3] is not None or not r[1]]
    latency = f"{statistics.median(ok) / 1000:.1f}s/JD" + (f"; {len(failed)} lần lỗi ({sum(failed) / 60000:.0f} phút)" if failed else "")
    return f"${sum(r[0] or 0 for r in rows) / n * 1000:.2f}", latency


def _preds(conn, jobs: list[dict], model: str, prompt: str) -> dict[str, list[str]]:
    by_hash = {e["content_hash"]: e["skills"] for e in db.load_extractions(conn, model, prompt)}
    return {j["url"]: by_hash[h] for j in jobs if (h := llm.content_hash(j["description"] or "")) in by_hash}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--system", choices=["llm", "tags"], default="llm")
    ap.add_argument("--prompt", default=llm.PROMPT_VERSION)
    ap.add_argument("--model", default=llm.MODEL, help="id model trong bảng extractions (Claude hoặc tên model Ollama)")
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev", help="nửa gold để chấm (gold.dev_test)")
    ap.add_argument("--vs", help="model đối chứng (cùng prompt): thêm ΔF1 ghép cặp và khoảng tin cậy vào ghi chú")
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    conn = db.connect("data/jobs.db")
    jobs = db.load_all(conn)
    if args.system == "tags":
        preds = {j["url"]: j["tags"] or [] for j in jobs}
        config, model, prompt, cost, latency = "baseline", "thẻ ITviec", "—", "$0", "—"
    else:
        preds = _preds(conn, jobs, args.model, args.prompt)
        config = "api" if args.model.startswith("claude") else "local"
        model, prompt = args.model, args.prompt
        cost, latency = _cost_and_latency(conn, args.model, args.prompt)
    labels = gold.load()
    if args.split != "all":
        part = dict(zip(["dev", "test"], gold.dev_test(list(labels))))[args.split]
        labels = {u: s for u, s in labels.items() if u in part}
    r = score(labels, preds, load_aliases())
    if r["n_jd"] == 0:
        raise SystemExit("Gold set chưa có JD nào được gán nhãn — xem `python -m jobmarket.gold`.")
    lo, hi = r["f1_ci"]
    print(f"{args.system}: P={r['p']:.3f} R={r['r']:.3f} F1={r['f1']:.3f} (KTC95% {lo:.3f}–{hi:.3f}) "
          f"trên {r['n_jd']} JD (thiếu dự đoán: {r['missing_pred']})")
    for d in r["worst"]:
        print(f"- {d['url']}\n  sót: {d['missed']}\n  thừa: {d['extra']}")
    note = f"{r['n_jd']} JD gold ({args.split}). {args.note}".strip()
    if args.vs:
        c = compare(labels, preds, _preds(conn, jobs, args.vs, args.prompt), load_aliases())
        vs = f"ΔF1 so với {args.vs} trên cùng JD: {c['diff']:+.3f} (KTC95% {c['ci'][0]:+.3f}…{c['ci'][1]:+.3f})."
        print(vs)
        note = f"{note} {vs}"
    row = (f"| {datetime.date.today()} | {config} | {model} | {prompt} | {r['p']:.3f} | {r['r']:.3f} | {r['f1']:.3f} ({lo:.3f}–{hi:.3f}) "
           f"| {cost} | {latency} | {note} |\n")
    print(row, end="")
    if args.append:
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS, "a", encoding="utf-8") as f:
            if f.tell() == 0:
                f.write("# Kết quả eval trích kỹ năng\n\nChỉ thêm dòng, không sửa dòng cũ.\n\n" + HEADER)
            f.write(row)
