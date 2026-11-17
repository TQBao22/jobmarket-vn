from jobmarket.normalize import load_aliases, normalize, normalize_all, unmapped

CSV = """alias,canonical
# chú thích bị bỏ qua
py,Python
scikit learn,scikit-learn
Large Language Models,LLM
"""


def table(tmp_path):
    path = tmp_path / "aliases.csv"
    path.write_text(CSV, encoding="utf-8")
    return load_aliases(path)


def test_alias_maps_to_canonical_ignoring_case_and_spaces(tmp_path):
    t = table(tmp_path)
    assert normalize("  PY ", t) == "Python"
    assert normalize("large  language models", t) == "LLM"


def test_canonical_name_maps_to_itself(tmp_path):
    t = table(tmp_path)
    assert normalize("python", t) == "Python"
    assert normalize("LLM", t) == "LLM"


def test_unknown_skill_kept_as_written(tmp_path):
    assert normalize(" LangGraph ", table(tmp_path)) == "LangGraph"


def test_normalize_all_dedupes_after_mapping(tmp_path):
    assert normalize_all(["py", "Python", "scikit learn"], table(tmp_path)) == ["Python", "scikit-learn"]


def test_exact_case_alias_wins_over_case_insensitive_match(tmp_path):
    path = tmp_path / "aliases.csv"
    path.write_text("alias,canonical\nReAct,Agentic AI\nReactJS,React\n", encoding="utf-8")
    t = load_aliases(path)
    assert normalize("ReAct", t) == "Agentic AI"
    assert normalize("React", t) == "React"
    assert normalize("REACTJS", t) == "React"


def test_unmapped_counts_skills_missing_from_table(tmp_path):
    counts = unmapped([["py", "LangGraph"], ["LangGraph", "dbt"]], table(tmp_path))
    assert counts == {"LangGraph": 2, "dbt": 1}
