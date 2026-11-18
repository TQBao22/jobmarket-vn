import io
import json

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from jobmarket import db
from jobmarket.api import app as api
from jobmarket.extract import llm

def _pdf_with_text(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length %d>>stream\n" % len(stream) + stream + b"\nendstream", b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return out + b"trailer<</Root 1 0 R/Size 6>>\nstartxref\n%d\n%%%%EOF" % xref


PDF_WITH_TEXT = _pdf_with_text("Python SQL")


def _blank_pdf():
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(100, 100)
    w.write(buf)
    return buf.getvalue()


def _runner_returning(skills):
    seen = []

    def run(system, user_input):
        seen.append(user_input)
        return json.dumps({"structured_output": {"results": [{"jd_id": "cv", "skills": skills}]}})

    run.seen = seen
    return run


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    conn = db.connect(path)
    for slug, until, skills in [("a", "", ["Python", "Docker"]), ("b", "", ["Python", "SQL"]), ("c", "2000-01-01", ["Rust"])]:
        desc = f"mô tả giả {slug}"
        db.save(conn, {"url": f"https://x.test/{slug}", "source": "itviec", "title": slug, "company": "C", "date_posted": "2026-11-01",
                       "valid_through": until, "tags": [], "description": desc, "fetched_at": "x"})
        db.save_extraction(conn, llm.content_hash(desc), llm.MODEL, llm.PROMPT_VERSION, f"https://x.test/{slug}", skills, 0)
    conn.close()
    monkeypatch.setenv("JOBMARKET_DB", str(path))
    monkeypatch.delenv("JOBMARKET_CV_MODEL", raising=False)
    api.app.dependency_overrides[api.get_runner] = lambda: _runner_returning(["Python", "SQL"])
    api.app.dependency_overrides[api.ollama_up] = lambda: True
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "jobs": 3, "ollama": True, "cv_model": "qwen3:8b"}


def test_top_skills(client):
    r = client.get("/api/skills/top", params={"limit": 1}).json()
    assert r["jd_total"] == 3 and r["skills"] == [{"skill": "Python", "jd_count": 2, "share": 0.667}]


def test_top_skills_unknown_month_404(client):
    r = client.get("/api/skills/top", params={"month": "1999-01"})
    assert r.status_code == 404 and isinstance(r.json()["detail"], str)


def test_jobs_filter(client):
    r = client.get("/api/jobs", params={"skill": "docker"}).json()
    assert r["total"] == 1 and r["jobs"][0]["skills"] == ["Python", "Docker"]
    assert client.get("/api/jobs", params={"skill": "Rust", "open_only": "false"}).json()["total"] == 1
    assert client.get("/api/jobs", params={"limit": 500}).status_code == 422


def test_match_txt(client):
    r = client.post("/api/match", files={"file": ("cv.txt", "Tôi biết Python".encode(), "text/plain")}, data={"top_k": "1"})
    body = r.json()
    assert r.status_code == 200 and body["model"] == "qwen3:8b" and body["cv_skills"] == ["Python", "SQL"]
    assert len(body["matches"]) == 1 and body["matches"][0]["title"] == "b" and body["matches"][0]["score"] == 1.0


def test_match_pdf_text_reaches_runner(client):
    run = _runner_returning(["Python"])
    api.app.dependency_overrides[api.get_runner] = lambda: run
    r = client.post("/api/match", files={"file": ("cv.pdf", PDF_WITH_TEXT, "application/pdf")})
    assert r.status_code == 200 and "Python SQL" in run.seen[0] and run.seen[0].startswith("### JD cv\nCV\n")


def test_bad_type_422(client):
    r = client.post("/api/match", files={"file": ("cv.docx", b"x", "application/octet-stream")})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_too_large_422(client):
    r = client.post("/api/match", files={"file": ("cv.txt", b"a" * (5 * 1024 * 1024 + 1), "text/plain")})
    assert r.status_code == 422


def test_empty_text_pdf_422(client):
    r = client.post("/api/match", files={"file": ("cv.pdf", _blank_pdf(), "application/pdf")})
    assert r.status_code == 422 and "ảnh" in r.json()["detail"]


def test_runner_raises_503(client):
    def boom(system, user_input):
        raise OSError("down")

    api.app.dependency_overrides[api.get_runner] = lambda: boom
    r = client.post("/api/match", files={"file": ("cv.txt", b"Python", "text/plain")})
    assert r.status_code == 503


def test_runner_error_output_503(client):
    api.app.dependency_overrides[api.get_runner] = lambda: (lambda s, u: json.dumps({"is_error": True, "result": "ollama: refused"}))
    assert client.post("/api/match", files={"file": ("cv.txt", b"Python", "text/plain")}).status_code == 503


def test_cv_upload_up_to_limit_stays_in_memory():
    # Starlette mặc định ghi phần upload >1 MB ra file tạm; CV không được chạm đĩa
    from starlette.formparsers import MultiPartParser
    from jobmarket.api import app as api_app
    assert MultiPartParser.spool_max_size > api_app.MAX_BYTES
