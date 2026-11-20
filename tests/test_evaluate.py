import json

import pytest

from jobmarket import db, gold
from jobmarket.evaluate import _cost_and_latency, compare, score


def test_score_micro_precision_recall_f1():
    result = score({"a": ["Python", "SQL"], "b": ["Docker"]}, {"a": ["Python", "Java"], "b": ["Docker"]}, {})
    assert (result["tp"], result["fp"], result["fn"]) == (2, 1, 1)
    assert result["p"] == pytest.approx(2 / 3)
    assert result["r"] == pytest.approx(2 / 3)
    assert result["f1"] == pytest.approx(2 / 3)


def test_score_normalizes_both_sides_and_ignores_case():
    table = {("fold", "py"): "Python"}
    assert score({"a": ["python"]}, {"a": ["py"]}, table)["f1"] == 1.0


def test_score_skips_unlabeled_and_counts_missing_predictions_as_empty():
    result = score({"a": ["SQL"], "b": None}, {}, {})
    assert result["n_jd"] == 1
    assert (result["tp"], result["fp"], result["fn"]) == (0, 0, 1)
    assert result["missing_pred"] == 1


def test_score_lists_worst_jd_first():
    result = score({"a": ["SQL"], "b": ["Go", "Rust"]}, {"a": ["SQL"], "b": ["Java"]}, {})
    assert result["worst"][0] == {"url": "b", "missed": ["Go", "Rust"], "extra": ["Java"]}


def test_gold_selection_is_deterministic_and_order_free():
    urls = [f"u{i}" for i in range(100)]
    assert gold.select(urls, 10) == gold.select(list(reversed(urls)), 10)
    assert len(gold.select(urls, 10)) == 10


def test_gold_init_never_overwrites_existing_labels(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text(json.dumps({"url": "u1", "title": "t", "skills": ["SQL"]}) + "\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        gold.init([{"url": "u2", "title": "t2"}], path, 1)
    assert gold.load(path) == {"u1": ["SQL"]}


def test_gold_init_writes_unlabeled_entries(tmp_path):
    path = tmp_path / "labels.jsonl"
    gold.init([{"url": "u1", "title": "t1"}, {"url": "u2", "title": "t2"}], path, 2)
    assert gold.load(path) == {"u1": None, "u2": None}


def test_dev_test_split_is_half_half_disjoint_and_order_free():
    urls = [f"https://x/{i}" for i in range(40)]
    dev, test = gold.dev_test(urls)
    assert len(dev) == len(test) == 20
    assert dev.isdisjoint(test) and dev | test == set(urls)
    assert gold.dev_test(list(reversed(urls))) == (dev, test)


def _labels(n, skills=("Python", "SQL", "Docker")):
    return {f"u{i}": list(skills) for i in range(n)}


def test_score_f1_ci_brackets_estimate_and_is_reproducible():
    labels = _labels(20)
    preds = {u: ["Python"] if i % 2 else ["Python", "SQL", "Java"] for i, u in enumerate(labels)}
    r = score(labels, preds, {})
    lo, hi = r["f1_ci"]
    assert lo < r["f1"] < hi
    assert score(labels, preds, {})["f1_ci"] == (lo, hi)  # seed cố định: chạy lại ra cùng khoảng


def test_score_f1_ci_collapses_when_every_jd_scores_the_same():
    labels = _labels(10)
    r = score(labels, {u: ["Python"] for u in labels}, {})
    assert r["f1_ci"] == pytest.approx((r["f1"], r["f1"]))


def test_compare_identical_predictions_gives_zero_difference():
    labels = _labels(10)
    preds = {u: ["Python"] if i % 3 else ["SQL", "Go"] for i, u in enumerate(labels)}
    c = compare(labels, preds, preds, {})
    assert c["diff"] == 0 and c["ci"] == (0, 0)


def test_compare_clear_gap_excludes_zero_but_gap_from_few_jd_does_not():
    labels = _labels(20)
    weak = {u: ["Python"] for u in labels}
    assert compare(labels, labels, weak, {})["ci"][0] > 0
    # A đúng hết ở 2 JD, B đúng hết ở 1 JD, còn lại như nhau: A hơn trên toàn tập nhưng chưa đủ để kết luận
    a = {u: list(labels[u]) if i in (0, 1) else ["Python"] for i, u in enumerate(labels)}
    b = {u: list(labels[u]) if i == 2 else ["Python"] for i, u in enumerate(labels)}
    c = compare(labels, a, b, {})
    assert c["diff"] > 0 and c["ci"][0] <= 0 < c["ci"][1]


def test_cost_and_latency_per_jd_and_counts_failed_calls(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    for cost, n, ms, err in [(0.02, 20, 40_000, None), (0.01, 10, 30_000, None), (0.005, 0, 900_000, "timeout")]:
        db.save_call(conn, {"model": "m", "prompt_version": "v1", "n_jd": n, "cost_usd": cost, "latency_ms": ms, "error": err})
    cost, latency = _cost_and_latency(conn, "m", "v1")
    assert cost == "$1.17"  # (0,02 + 0,01 + 0,005) / 30 JD × 1.000: lần gọi lỗi vẫn tính tiền
    assert latency == "2.5s/JD; 1 lần lỗi (15 phút)"  # trung vị của 2,0 và 3,0 s/JD; lần lỗi báo riêng


def test_cost_and_latency_without_successful_calls(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_call(conn, {"model": "m", "prompt_version": "v1", "n_jd": 0, "cost_usd": 0, "latency_ms": 5, "error": "x"})
    assert _cost_and_latency(conn, "m", "v1") == ("—", "—")
