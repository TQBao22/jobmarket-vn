"""API local (v3): `docs/api.md`. Chạy: uvicorn jobmarket.api.app:app --port 8000

CV chỉ nằm trong bộ nhớ của request: không ghi file, DB hay log.
"""
import datetime
import json
import io
import os
import sqlite3
import urllib.request
from pathlib import Path
from typing import Literal

from starlette.concurrency import run_in_threadpool
from starlette.formparsers import MultiPartParser
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from pypdf import PdfReader

from jobmarket import query
from jobmarket.extract import llm, local
from jobmarket.normalize import load_aliases, normalize

MAX_BYTES = 5 * 1024 * 1024
# Starlette ghi phần upload >1 MB ra file tạm; nâng ngưỡng để CV (≤ MAX_BYTES) chỉ nằm trong bộ nhớ.
MultiPartParser.spool_max_size = MAX_BYTES + 1024 * 1024
MAX_CV_CHARS = 20_000  # vượt thì Ollama tự cắt ngữ cảnh 8K token mà không báo; cắt trước cho rõ ràng
CV_PROMPT = llm.PROMPTS / "cv_v2.txt"
CV_MAX_OUTPUT = 2048  # mỗi kỹ năng kèm câu trích ≤ 12 từ: output dài hơn trích JD
CV_SCHEMA = {
    "type": "object",
    "properties": {"skills": {"type": "array", "items": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "evidence": {"type": "string", "enum": ["used", "listed"]},
                       "quote": {"type": "string"}},
        "required": ["name", "evidence", "quote"],
    }}},
    "required": ["skills"],
}


class _CvSkill(BaseModel):
    name: str
    evidence: Literal["used", "listed"]
    quote: str


class _Cv(BaseModel):
    skills: list[_CvSkill]

app = FastAPI(title="JobMarket VN API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
def _bad_params(request: Request, exc: RequestValidationError):
    fields = ", ".join(str(e["loc"][-1]) for e in exc.errors())
    return JSONResponse({"detail": f"Tham số không hợp lệ: {fields}."}, status_code=422)


def get_conn():
    path = Path(os.environ.get("JOBMARKET_DB", "data/jobs.db")).resolve()
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, check_same_thread=False)  # dependency và endpoint async chạy ở thread khác nhau
    try:
        yield conn
    finally:
        conn.close()


def _cv_model() -> str:
    return os.environ.get("JOBMARKET_CV_MODEL", "qwen3:8b")


def get_runner():
    return local.ollama_runner(_cv_model(), schema=CV_SCHEMA, num_predict=CV_MAX_OUTPUT)


def ollama_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2).close()
        return True
    except OSError:
        return False


@app.get("/api/health")
def health(conn=Depends(get_conn), up: bool = Depends(ollama_up)):
    return {"status": "ok", **query.health(conn), "ollama": up, "cv_model": _cv_model()}


@app.get("/api/skills/top")
def top_skills(month: str | None = None, limit: int = 20, conn=Depends(get_conn)):
    if not 1 <= limit <= 100:
        raise HTTPException(422, "Tham số không hợp lệ: limit (1–100).")
    try:
        return query.top_skills(conn, month, limit)
    except query.NotFound:
        raise HTTPException(404, f"Không có dữ liệu cho tháng {month}.")


@app.get("/api/jobs")
def jobs(skill: str | None = None, open_only: bool = True, limit: int = 50, conn=Depends(get_conn)):
    if not 1 <= limit <= 200:
        raise HTTPException(422, "Tham số không hợp lệ: limit (1–200).")
    return query.jobs(conn, skill, open_only, limit, datetime.date.today().isoformat())


def _cv_text(name: str, data: bytes) -> str:
    suffix = Path(name or "").suffix.lower()
    if suffix == ".txt":
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(422, "File .txt phải mã hoá UTF-8.")
    if suffix == ".pdf":
        try:
            return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
        except Exception:  # pypdf ném nhiều loại lỗi khác nhau với file hỏng
            raise HTTPException(422, "Không đọc được file PDF (file hỏng hoặc có mật khẩu).")
    raise HTTPException(422, "Chỉ nhận CV định dạng .pdf hoặc .txt.")


def _fold(text: str) -> str:
    return " ".join(text.split()).casefold()


def _cv_skills(out: str, text: str) -> list[dict] | None:
    """Output runner → [{skill, evidence, quote}]; None nếu output hỏng. Câu trích không có trong CV → hạ về `listed`."""
    try:
        cv = _Cv.model_validate(json.loads(out)["structured_output"])
    except (json.JSONDecodeError, KeyError, TypeError, ValidationError):
        return None
    table, folded, merged = load_aliases(), _fold(text), {}
    for item in cv.skills:
        if not item.name.strip():
            continue
        quote = " ".join(item.quote.split())
        used = item.evidence == "used" and bool(quote) and _fold(quote) in folded
        skill = normalize(item.name, table)
        prev = merged.get(skill.casefold())
        if prev is None or (used and prev["evidence"] == "listed"):  # cùng tên chuẩn: `used` thắng
            merged[skill.casefold()] = {"skill": skill, "evidence": "used" if used else "listed", "quote": quote if used else ""}
    return list(merged.values())


@app.post("/api/match")
async def match(file: UploadFile = File(...), top_k: int = Form(10), conn=Depends(get_conn), runner=Depends(get_runner)):
    if not 1 <= top_k <= 50:
        raise HTTPException(422, "Tham số không hợp lệ: top_k (1–50).")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(422, "File quá lớn (tối đa 5 MB).")
    text = _cv_text(file.filename, data).strip()
    if not text:
        raise HTTPException(422, "CV không có chữ để đọc (có thể là ảnh scan). Hãy dùng PDF có chữ hoặc file .txt.")
    unavailable = HTTPException(503, "Không trích được kỹ năng từ CV: Ollama chưa chạy hoặc model lỗi. Hãy bật Ollama rồi thử lại.")
    try:
        # model local ~1 phút/CV: chạy ngoài event loop để các request khác không bị chặn
        text = text[:MAX_CV_CHARS]
        out = await run_in_threadpool(runner, CV_PROMPT.read_text(encoding="utf-8"), text)
    except Exception:
        raise unavailable
    cv_skills = _cv_skills(out, text)
    if cv_skills is None:
        raise unavailable
    names = [s["skill"] for s in cv_skills]
    listed = [s["skill"] for s in cv_skills if s["evidence"] == "listed"]
    return {"model": _cv_model(), "cv_skills": cv_skills,
            "matches": query.match(conn, names, top_k, datetime.date.today().isoformat(), listed)}
