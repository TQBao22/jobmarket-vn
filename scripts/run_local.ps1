# Chạy hệ thống local: Ollama (:11434) + BE FastAPI (:8000) + FE Vite (:5173). Dừng: đóng các cửa sổ vừa mở.
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:OLLAMA_MODELS = [Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
try { Invoke-RestMethod http://localhost:11434/api/version -TimeoutSec 2 | Out-Null }
catch { Start-Process ollama -ArgumentList "serve" -WindowStyle Minimized }

$env:PYTHONPATH = Join-Path $root "src"
if (-not $env:JOBMARKET_DB) { $env:JOBMARKET_DB = Join-Path $root "data\jobs.db" }
Start-Process (Join-Path $root ".venv\Scripts\python.exe") -ArgumentList "-m", "uvicorn", "jobmarket.api.app:app", "--port", "8000" -WorkingDirectory $root
Start-Process "cmd.exe" -ArgumentList "/k", "npm run dev" -WorkingDirectory (Join-Path $root "web")
"Mở http://localhost:5173 (API: http://localhost:8000/docs)"
