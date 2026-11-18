import json

from jobmarket.extract import llm, local


def fake_post(content, prompt_tokens=120, output_tokens=30):
    calls = []

    def post(body):
        calls.append(body)
        return {"message": {"content": content}, "prompt_eval_count": prompt_tokens, "eval_count": output_tokens}

    return post, calls


def test_ollama_runner_output_parses_like_claude_cli():
    post, calls = fake_post(json.dumps({"results": [{"jd_id": "a", "skills": ["Python", "python", "SQL"]}]}))
    out = local.ollama_runner("qwen3:1.7b", post=post)("sys", "### JD a\nAI Engineer\nCần Python, SQL.")
    parsed = llm.parse_output(out, {"a"})
    assert parsed.error is None
    assert parsed.skills == {"a": ["Python", "SQL"]}
    assert (parsed.cost_usd, parsed.input_tokens, parsed.output_tokens) == (0.0, 120, 30)


def test_ollama_runner_requests_schema_no_thinking_and_deterministic_output():
    post, calls = fake_post(json.dumps({"results": []}))
    local.ollama_runner("qwen3:8b", post=post)("sys prompt", "input")
    body = calls[0]
    assert body["model"] == "qwen3:8b" and body["stream"] is False and body["think"] is False
    assert body["format"] == llm.SCHEMA
    assert body["options"]["temperature"] == 0
    assert body["options"]["num_predict"] == local.MAX_OUTPUT  # model nhỏ hay lặp vô hạn
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_ollama_runner_invalid_json_becomes_error():
    post, _ = fake_post("not json {")
    parsed = llm.parse_output(local.ollama_runner("m", post=post)("s", "### JD a\nx"), {"a"})
    assert parsed.skills == {} and parsed.error


def test_ollama_runner_connection_failure_becomes_error():
    def post(body):
        raise OSError("connection refused")

    parsed = llm.parse_output(local.ollama_runner("m", post=post)("s", "x"), {"a"})
    assert parsed.error and "connection refused" in parsed.error
