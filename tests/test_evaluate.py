import json

import pytest

from jobmarket import gold
from jobmarket.evaluate import score


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
