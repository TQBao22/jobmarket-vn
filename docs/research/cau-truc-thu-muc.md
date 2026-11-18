# Cấu trúc thư mục — các mẫu chính thức và đề xuất cho repo (kiểm tra 2026-11-18)

Câu hỏi: repo vừa là pipeline dữ liệu, vừa có ML (v2), API, FE, MCP server (v3). Các template lớn sắp xếp loại repo này thế nào, và repo này nên đổi gì để gọn và đúng chuẩn mà không làm thừa.

## 1. Các mẫu

### FastAPI full-stack template (chính thức của FastAPI)
Nguồn: [github.com/fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) (xem listing thư mục ngày 2026-11-18).
```
backend/            # Dockerfile, pyproject.toml, alembic.ini, README.md riêng
  app/              # main.py, models.py, crud.py, utils.py, core/, api/, alembic/
    api/            # main.py, deps.py, routes/
  tests/  scripts/
frontend/           # Vite + React + TS: index.html, package.json, vite.config.ts, src/, tests/
  src/              # client/ components/ hooks/ lib/ routes/  (theo README của frontend)
scripts/  compose.yml  pyproject.toml  uv.lock  README.md  development.md  deployment.md
```
- Giải quyết: hai ứng dụng deploy riêng, mỗi bên có Dockerfile, file phụ thuộc và README riêng; `compose.yml` ở gốc ghép lại. README nói FE được build rồi phục vụ qua FastAPI cùng domain với API.
- Tên `backend/`/`frontend/` hợp lý vì toàn bộ Python ở đó *là* web backend (CRUD + Postgres). Không có pipeline batch dùng chung code.

### FastAPI docs — "Bigger Applications"
Nguồn: [fastapi.tiangolo.com/tutorial/bigger-applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
```
app/
  __init__.py  main.py  dependencies.py
  routers/   items.py  users.py
  internal/  admin.py
```
- Giải quyết: tách path operation theo nhóm (`routers/`) nhưng vẫn "part of the same Python Package"; dependency dùng nhiều nơi để trong `dependencies.py`. Điểm vào đặt tên `main.py` (cả template full-stack cũng dùng `app/main.py`, `app/api/main.py`).
- Docs không nói gì về chỗ đặt package `app/` trong repo; đây là cấu trúc *bên trong* package.

### Python Packaging User Guide — src layout vs flat layout
Nguồn: [packaging.python.org/.../src-layout-vs-flat-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/), [tutorial packaging-projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/).
```
pyproject.toml  README.md  LICENSE
src/<package>/__init__.py ...
tests/
```
- src layout: code import được nằm trong `src/`, nên bản cài đặt không bị bản local che mất, và editable install chỉ thấy file đáng import.
- Đánh đổi được ghi rõ: phải cài package (editable) mới chạy được từ cây nguồn. Repo hiện vòng qua bằng `PYTHONPATH=src` và `pythonpath = ["src"]` trong `pyproject.toml` (pytest), không có bảng `[project]`.

### Monorepo JS: Turborepo `apps/` + `packages/`
Nguồn: [turborepo.dev/.../structuring-a-repository](https://turborepo.dev/docs/crafting-your-repository/structuring-a-repository).
```
apps/web  apps/docs      # mỗi thư mục có package.json
packages/ui
package.json  turbo.json  <lockfile>
```
- Docs viết "We recommend starting with splitting your packages into `apps/` ... `packages/` for everything else". Đây là khuyến nghị, không nằm trong "Minimum requirements"; bắt buộc chỉ là workspace config trỏ đúng thư mục và mỗi package có `package.json`.
- Giải quyết: nhiều package JS dùng chung code, build có cache. Repo này chỉ có **một** package JS.

### uv workspaces
Nguồn: [docs.astral.sh/uv/concepts/projects/workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/).
- "a collection of one or more packages ... managed together", dùng chung một lockfile; ví dụ để thành viên trong `packages/`.
- Docs nói dành cho "multiple interconnected packages"; không hợp khi các thành viên có phụ thuộc xung đột. Repo này có một package Python và dùng pip, không dùng uv.

### Cookiecutter Data Science v2 (DrivenData)
Nguồn: [cookiecutter-data-science.drivendata.org](https://cookiecutter-data-science.drivendata.org/), [opinions](https://cookiecutter-data-science.drivendata.org/opinions/).
```
data/{external,interim,processed,raw}
models/  notebooks/  references/  reports/figures/  docs/
pyproject.toml  requirements.txt  Makefile  README.md
<module_name>/  config.py dataset.py features.py plots.py modeling/{train,predict}.py
```
- Giải quyết: tái lập phân tích. Các ý chính: "Don't ever edit your raw data"; pipeline là DAG; `data/` mặc định nằm trong `.gitignore`; code lặp lại giữa notebook phải chuyển vào package; ghi lại thí nghiệm mô hình (JSON đơn giản hoặc MLflow).
- Chính trang opinions viết "be liberal in changing the folders around for your project". Package đặt flat (không `src/`); code train nằm *trong* package (`modeling/train.py`); model đã train để ở `models/`.

### MCP servers chính thức
Nguồn: [modelcontextprotocol/servers/src](https://github.com/modelcontextprotocol/servers/tree/main/src), [src/git](https://github.com/modelcontextprotocol/servers/tree/main/src/git).
```
src/git/  pyproject.toml  uv.lock  Dockerfile  README.md  src/mcp_server_git/  tests/
```
- Mỗi server là một package độc lập (src layout riêng, Dockerfile riêng) vì được phát hành riêng lẻ. Không có quy ước "MCP server đặt ở đâu" trong một ứng dụng: nó chỉ là một package/entry point như mọi CLI khác.

### React / Vite
- React (docs cũ, FAQ "File Structure"): "React doesn't have opinions on how you put files into folders", "don't spend more than five minutes on choosing a file structure", nên giới hạn "three or four nested folders" ([legacy.reactjs.org/docs/faq-structure.html](https://legacy.reactjs.org/docs/faq-structure.html)).
- react.dev hiện tại không đưa ra cấu trúc thư mục, chỉ hướng tới framework hoặc build tool ([react.dev/learn/creating-a-react-app](https://react.dev/learn/creating-a-react-app)).
- Vite: không tìm thấy khuyến nghị chính thức về cấu trúc thư mục ngoài khung `index.html` + `src/` do `create-vite` sinh ra (chưa đọc nguồn sơ cấp cho ý này).
- → **Không có chuẩn chính thức** cho FE; `src/views/` hiện tại là sở thích, không phải lệch chuẩn.

## 2. Cái gì thật sự là chuẩn, cái gì là sở thích

| Thực sự chung (≥3 nguồn) | Chỉ là quy ước/sở thích |
|---|---|
| `README.md` ở gốc (packaging tutorial, cookiecutter, full-stack template, MCP servers) | Tên `backend/` vs `api/` vs `server/` |
| `pyproject.toml` ở gốc mỗi package Python | `apps/` + `packages/` (Turborepo tự gọi là recommend) |
| `tests/` cạnh code, ngoài package | src layout vs flat (Packaging guide trình bày cả hai, cookiecutter dùng flat) |
| Mỗi đơn vị deploy riêng có file phụ thuộc + Dockerfile riêng (full-stack, MCP servers) | Cấu trúc bên trong FE (`views/`, `components/`, `routes/`) |
| Dữ liệu thô bất biến, ngoài git (cookiecutter) | Tên điểm vào FastAPI `main.py` (chỉ là ví dụ trong docs + template) |
| Code dùng chung nằm trong một package, script/notebook import vào (cookiecutter, FastAPI) | `models/`, `reports/`, `notebooks/` (cookiecutter tự nói "be liberal") |
| FE là thư mục riêng có `package.json` (full-stack: `frontend/`; Turborepo: `apps/web`) | |

Kết luận: chuẩn là *ranh giới* (mỗi thứ deploy riêng một thư mục có file phụ thuộc riêng; code dùng chung một package; dữ liệu thô ngoài git), không phải *tên* thư mục.

## 3. Đối chiếu repo hiện tại

Đã đúng chuẩn: src layout `src/jobmarket/`; `tests/` ở gốc; `data/raw/` + `jobs.db` gitignore; `query.py` dùng chung cho REST và MCP (đúng ý "refactor shared logic into source code"); `api/` là subpackage giống `app/api/` của full-stack template; FE là thư mục riêng có `package.json`.

Lệch so với điểm chung:
1. **Không có `README.md`.** Mọi mẫu đều có. Repo công khai cho portfolio nên đây là thiếu sót lớn nhất. `.devcontainer/devcontainer.json` còn mở `README.md` không tồn tại.
2. **`web/tsconfig.tsbuildinfo` bị commit.** File này do `tsc -b` sinh ra (script `build`/`typecheck`), không phải nguồn.
3. **Một `requirements.txt` cho hai đơn vị deploy.** Streamlit Cloud cài cả `fastapi`, `uvicorn`, `pypdf`, `pytest`... dù dashboard chỉ cần `streamlit` (Dockerfile đã tự tách: chỉ `pip install streamlit`).
4. **Hai file tên `app.py`** (`app.py` Streamlit ở gốc, `src/jobmarket/api/app.py` FastAPI). Docs FastAPI và template đều dùng `main.py`.
5. `pyproject.toml` chỉ có cấu hình pytest, không có `[project]`; chạy nhờ `PYTHONPATH=src`. Packaging guide ghi đây là cái giá của src layout; cách vòng hiện tại vẫn chạy được.
6. `.devcontainer/` là file Streamlit Cloud sinh sẵn (Python 3.11), lệch với CI và Cloud (3.12).

## 4. Ràng buộc: Streamlit Community Cloud
- Entrypoint đặt ở đâu cũng được: "their entrypoint files can be anywhere in your repository"; working directory trên Cloud luôn là gốc repo ([file-organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)).
- File phụ thuộc: Cloud tìm ở thư mục của entrypoint trước, rồi gốc repo; thứ tự `uv.lock` → `Pipfile` → `environment.yml` → `requirements.txt` → `pyproject.toml` (Poetry); chỉ dùng file đầu tiên tìm thấy ([app-dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)).
- **Đổi đường dẫn entrypoint của app đã deploy:** Cloud nhận diện app bằng owner, repo, branch, entrypoint path; đổi mà không chuẩn bị thì "will lose access to administer any associated app". Quy trình chính thức: xoá app → đổi trên GitHub → deploy lại ([rename-your-app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app)). Trang App settings chỉ có App URL, sharing, secrets; không có ô sửa main file path ([app-settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)).
- Deploy lại sinh subdomain mới; có thể đặt subdomain tuỳ chỉnh 6–63 ký tự trong App settings (cùng trang). Chưa xác minh được subdomain tự sinh `jobmarket-vn-tndk7vgqeiu5zqkfkxpwrw` có lấy lại được sau khi xoá app hay không → coi như URL sẽ đổi.
- Hệ quả: dời `app.py` khỏi gốc phải xoá app, deploy lại, đổi URL trong `CLAUDE.md`, `docs/pipeline.md` và mọi chỗ đã chia sẻ link. Lợi ích chỉ là gốc repo gọn hơn một file → **giữ `app.py` ở gốc**.
- Tách phụ thuộc không cần dời entrypoint: entrypoint ở gốc thì Cloud đọc `requirements.txt` ở gốc. Chỉ cần để file này chứa phụ thuộc của dashboard, phụ thuộc còn lại đưa sang file khác.

## 5. Đề xuất

### Cây thư mục đích
```
README.md                 # MỚI: mục đích, số đo chính, link dashboard, cách chạy
app.py                    # giữ: Streamlit Cloud trỏ vào đây
requirements.txt          # chỉ phụ thuộc dashboard (Streamlit Cloud)
requirements-dev.txt      # MỚI: -r requirements.txt + pydantic, fastapi, uvicorn, pypdf, pytest...
pyproject.toml            # thêm [project] khi làm MCP (xem dưới)
Dockerfile  .dockerignore
src/jobmarket/
  crawl/ extract/ normalize/
  route/                  # v2
  api/main.py             # đổi tên từ api/app.py (tuỳ chọn)
  mcp/                    # v3, cạnh api/: hai cổng, chung query.py
  query.py db.py aggregate.py evaluate.py gold.py
frontend/                 # đổi tên từ web/
train/                    # v2: script fine-tune, phụ thuộc nặng riêng (requirements-train.txt)
models/                   # v2: adapter QLoRA, gitignore (như cookiecutter)
tests/  eval/  scripts/  data/  docs/
```
Không dùng: `backend/` (code Python không chỉ là backend web mà là pipeline + API + MCP dùng chung `query.py`; dời vào `backend/src/jobmarket` làm hỏng mọi import, CI, rule paths mà không giải quyết vấn đề nào), `apps/`+`packages/` (một package JS), uv workspace (một package Python, repo dùng pip), package MCP riêng như `modelcontextprotocol/servers` (server ở đó được phát hành độc lập; ở đây MCP phải dùng chung `query.py`).

### Bảng di chuyển

| Hiện tại | Mới | Khi nào | Phải sửa theo |
|---|---|---|---|
| (không có) | `README.md` | **ngay** | viết bằng skill `humanizer:humanizer` theo CLAUDE.md |
| `web/` | `frontend/` | **đã làm** (2026-11-18, commit `2ff9248`) | `.github/workflows/ci.yml` (`working-directory`, `cache-dependency-path`), `.gitignore` (`web/node_modules/`, `web/dist/`), `scripts/run_local.ps1`, `CLAUDE.md` (cây + lệnh `cd web`), `docs/architecture.md`. ADR 0004 giữ nguyên (ghi lịch sử) |
| `web/tsconfig.tsbuildinfo` (commit) | xoá khỏi git, thêm `*.tsbuildinfo` vào `.gitignore` | **đã làm**, cùng commit đổi tên | — |
| `requirements.txt` (mọi thứ) | `requirements.txt` (dashboard) + `requirements-dev.txt` | **ngay** | `ci.yml` job `test` cài `requirements-dev.txt`; `CLAUDE.md` lệnh `pip install`. `app.py` import `altair`, `pandas`: ghi rõ trong `requirements.txt`, không dựa vào phụ thuộc gián tiếp của `streamlit` |
| `src/jobmarket/api/app.py` | `src/jobmarket/api/main.py` | tuỳ chọn, rẻ | `scripts/run_local.ps1` (`jobmarket.api.app:app`), `tests/test_api.py`, `docs/architecture.md` |
| `pyproject.toml` chỉ có pytest | thêm `[project]` (name, version, requires-python ≥3.12) + `pip install -e .` | khi viết `mcp/` (v3) | bỏ `PYTHONPATH` ở `ci.yml`, `run_local.ps1`, `CLAUDE.md`; MCP config của Claude Code gọi `python -m jobmarket.mcp` không cần biến môi trường |
| (không có) | `train/`, `models/` | khi bắt đầu fine-tune (v2) | `.gitignore` thêm `models/`; rule `llm-extraction.md` đã có `train/**` |
| `.devcontainer/` | xoá, hoặc sửa image sang Python 3.12 | tuỳ chọn | không file nào khác dùng |
| `app.py` ở gốc | giữ | — | dời đi = xoá app Cloud + URL mới |
| `.archify/` ở gốc | giữ | — | `architecture.md` trỏ tới; dời sang `docs/` chỉ là sở thích |

### Lý do chọn 3 thay đổi "ngay"
1. **README.md**: điểm chung duy nhất mọi mẫu đều có; repo portfolio công khai, người xem mở README trước tiên.
2. **`web/` → `frontend/` + bỏ `tsbuildinfo`**: khớp tên với template FastAPI chính thức; chi phí chỉ là 5 file text, không đụng import Python. File build bị commit là lỗi thật, không phải sở thích.
3. **Tách `requirements.txt`**: đúng ranh giới "mỗi đơn vị deploy một file phụ thuộc" (full-stack, MCP servers); Dockerfile đã tách sẵn, chỉ còn Streamlit Cloud cài thừa. Không phải dời `app.py`.

### Chỉ làm khi repo lớn hơn
- Cấu trúc trong `api/` kiểu `routers/` + `dependencies.py` (FastAPI Bigger Applications): khi `api/` vượt một file, hoặc có >2 nhóm route.
- `frontend/src/components/` vs `views/`: khi có component dùng chung giữa nhiều view. Không có chuẩn chính thức để theo.
- `backend/` + `frontend/` + `compose.yml`: chỉ khi deploy BE công khai bằng container (hiện ADR 0004 chốt chạy local).
- uv workspace hoặc nhiều `pyproject.toml`: khi `train/` cần phụ thuộc xung đột với runtime (torch/bitsandbytes) mà một file `requirements-train.txt` không đủ.
- `notebooks/`, `reports/`: chỉ tạo khi thật sự có notebook/báo cáo sinh tự động; `eval/RESULTS.md` đang làm vai trò `reports/`.

## Chưa xác minh
- Subdomain tự sinh có giữ lại được khi xoá + deploy lại app không (docs không nói).
- Khuyến nghị cấu trúc của Vite: chưa đọc docs Vite trực tiếp.
- Listing GitHub chỉ thấy phần đầu ("View all files"); cấu trúc `frontend/src/` của template lấy từ README, không từ cây file.
