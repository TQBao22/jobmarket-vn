import csv

from jobmarket.aggregate import count_skills, write_csv


def job(url, month, description):
    return {"url": url, "source": "itviec", "date_posted": f"{month}-05", "description": description}


def test_count_skills_per_source_month_after_normalizing():
    jobs = [job("a", "2026-10", "A"), job("b", "2026-10", "B"), job("c", "2026-11", "C")]
    skills = {"A": ["py", "Docker"], "B": ["Python"], "C": ["Python"]}
    table = {("fold", "py"): "Python"}
    rows = count_skills(jobs, lambda d: skills.get(d), table)
    assert rows == [
        {"source": "itviec", "month": "2026-10", "skill": "Python", "jd_count": 2, "jd_total": 2},
        {"source": "itviec", "month": "2026-10", "skill": "Docker", "jd_count": 1, "jd_total": 2},
        {"source": "itviec", "month": "2026-11", "skill": "Python", "jd_count": 1, "jd_total": 1},
    ]


def test_unmapped_skills_differing_only_in_case_are_one_skill():
    jobs = [job("a", "2026-10", "A"), job("b", "2026-10", "B"), job("c", "2026-10", "C")]
    skills = {"A": ["pandas"], "B": ["Pandas"], "C": ["Pandas"]}
    rows = count_skills(jobs, lambda d: skills[d], {})
    assert rows == [{"source": "itviec", "month": "2026-10", "skill": "Pandas", "jd_count": 3, "jd_total": 3}]


def test_jobs_without_extraction_are_left_out_of_totals():
    jobs = [job("a", "2026-10", "A"), job("b", "2026-10", "B")]
    rows = count_skills(jobs, lambda d: ["SQL"] if d == "A" else None, {})
    assert rows == [{"source": "itviec", "month": "2026-10", "skill": "SQL", "jd_count": 1, "jd_total": 1}]


def test_write_csv_has_only_aggregate_columns(tmp_path):
    path = tmp_path / "public" / "skill_counts.csv"
    write_csv([{"source": "itviec", "month": "2026-10", "skill": "SQL", "jd_count": 1, "jd_total": 1}], path)
    with open(path, encoding="utf-8", newline="") as f:
        assert list(csv.DictReader(f)) == [{"source": "itviec", "month": "2026-10", "skill": "SQL", "jd_count": "1", "jd_total": "1"}]
