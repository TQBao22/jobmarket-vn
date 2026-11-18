import json

from jobmarket import db
from jobmarket.extract import llm

MODEL, PROMPT = "claude-haiku-5-5", "v1"


def job(i, description="Cần Python, Docker."):
    return {
        "url": f"https://itviec.com/viec-lam-it/x-{i:04d}", "source": "itviec", "title": f"AI Engineer {i}",
        "company": "X", "date_posted": "2026-10-20", "valid_through": None, "tags": ["Python"],
        "description": description, "fetched_at": "2026-11-16T20:31:00+07:00",
    }


def cli_output(results, cost=0.01, is_error=False):
    out = {"is_error": is_error, "total_cost_usd": cost,
           "usage": {"input_tokens": 100, "cache_creation_input_tokens": 50, "cache_read_input_tokens": 0, "output_tokens": 20}}
    if results is not None:
        out["structured_output"] = {"results": results}
    return json.dumps(out)


class FakeRunner:
    """Trả lời mọi JD trong input bằng skills cố định; ghi lại số lần gọi."""

    def __init__(self, skills=("Python", "Docker"), fail=False):
        self.skills, self.fail, self.calls = list(skills), fail, 0

    def __call__(self, system, user_input):
        self.calls += 1
        if self.fail:
            return cli_output(None, is_error=True)
        ids = [line.split()[2] for line in user_input.splitlines() if line.startswith("### JD ")]
        return cli_output([{"jd_id": i, "skills": self.skills} for i in ids])


def test_content_hash_ignores_whitespace_differences():
    assert llm.content_hash("Cần  Python,\nDocker.") == llm.content_hash("Cần Python, Docker.")


def test_parse_output_cleans_skills_and_reads_usage():
    out = cli_output([{"jd_id": "a", "skills": [" Python ", "python", "", "Docker"]}])
    parsed = llm.parse_output(out, {"a"})
    assert parsed.skills == {"a": ["Python", "Docker"]}
    assert parsed.error is None
    assert parsed.cost_usd == 0.01
    assert (parsed.input_tokens, parsed.output_tokens) == (150, 20)


def test_parse_output_drops_unknown_ids():
    out = cli_output([{"jd_id": "a", "skills": ["SQL"]}, {"jd_id": "zzz", "skills": ["Go"]}])
    assert llm.parse_output(out, {"a", "b"}).skills == {"a": ["SQL"]}


def test_parse_output_error_when_cli_reports_error():
    parsed = llm.parse_output(cli_output(None, is_error=True), {"a"})
    assert parsed.skills == {} and parsed.error


def test_parse_output_error_when_structured_output_invalid():
    out = json.dumps({"is_error": False, "structured_output": {"results": [{"jd_id": "a"}]}})
    parsed = llm.parse_output(out, {"a"})
    assert parsed.skills == {} and parsed.error


def test_extract_saves_results_and_logs_calls(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    for i in range(25):
        db.save(conn, job(i, f"Mô tả {i}"))
    runner = FakeRunner()
    stats = llm.extract(conn, MODEL, PROMPT, "system", runner=runner)
    assert runner.calls == 2  # 20 + 5
    assert stats["extracted"] == 25
    rows = db.load_extractions(conn, MODEL, PROMPT)
    assert len(rows) == 25 and rows[0]["skills"] == ["Python", "Docker"]
    assert conn.execute("SELECT count(*), sum(n_jd) FROM llm_calls").fetchone() == (2, 25)


def test_extract_skips_jobs_already_in_cache(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    db.save(conn, job(1))
    llm.extract(conn, MODEL, PROMPT, "system", runner=FakeRunner())
    runner = FakeRunner()
    assert llm.extract(conn, MODEL, PROMPT, "system", runner=runner)["extracted"] == 0
    assert runner.calls == 0


def test_extract_failed_batch_is_logged_and_retried_next_run(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    db.save(conn, job(1))
    stats = llm.extract(conn, MODEL, PROMPT, "system", runner=FakeRunner(fail=True))
    assert stats["failed_batches"] == 1
    assert conn.execute("SELECT error IS NOT NULL FROM llm_calls").fetchone() == (1,)
    assert llm.extract(conn, MODEL, PROMPT, "system", runner=FakeRunner())["extracted"] == 1


def test_extract_respects_limit(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    for i in range(5):
        db.save(conn, job(i, f"Mô tả {i}"))
    assert llm.extract(conn, MODEL, PROMPT, "system", limit=3, runner=FakeRunner())["extracted"] == 3


def test_extract_batch_size_one_calls_runner_per_jd(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    for i in range(3):
        db.save(conn, job(i, f"Cần Python {i}."))
    runner = FakeRunner()
    stats = llm.extract(conn, "qwen3:1.7b", PROMPT, "sys", runner=runner, batch=1)
    assert runner.calls == 3 and stats["extracted"] == 3


def test_extract_only_restricts_to_given_urls(tmp_path):
    conn = db.connect(tmp_path / "jobs.db")
    for i in range(3):
        db.save(conn, job(i, f"Cần Python {i}."))
    stats = llm.extract(conn, MODEL, PROMPT, "sys", runner=FakeRunner(), only={job(1)["url"]})
    assert stats["extracted"] == 1
    assert [e["url"] for e in db.load_extractions(conn, MODEL, PROMPT)] == [job(1)["url"]]
