@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python no esta instalado o no esta en PATH.
  pause
  exit /b 1
)
set PYTHONPATH=%CD%\src
python tests\stability_benchmark.py
if errorlevel 1 (
  echo.
  echo [ERROR] El benchmark de estabilidad fallo.
  pause
  exit /b 1
)
echo.
echo [OK] Benchmark de estabilidad completado.
pause
