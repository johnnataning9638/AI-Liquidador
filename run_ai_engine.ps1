$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path '.venv\Scripts\Activate.ps1') {
    . .\.venv\Scripts\Activate.ps1
}
python -m uvicorn src.api:app --host 127.0.0.1 --port 8787
