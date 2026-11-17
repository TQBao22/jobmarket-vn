# Crawl ITviec hàng tuần (Task Scheduler "JobMarketVN crawl"). Chỉ crawl + lưu DB; trích kỹ năng chạy tay vì tốn hạn mức gói Claude.
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = "src"
$env:PYTHONIOENCODING = "utf-8"
New-Item -ItemType Directory -Force "data\logs" | Out-Null
$log = "data\logs\crawl-$(Get-Date -Format yyyy-MM-dd).log"
"start $(Get-Date -Format s)" | Out-File -Append -Encoding utf8 $log
& .venv\Scripts\python.exe -m jobmarket.crawl.itviec --limit 2000 2>&1 | Out-File -Append -Encoding utf8 $log
"exit $LASTEXITCODE $(Get-Date -Format s)" | Out-File -Append -Encoding utf8 $log
