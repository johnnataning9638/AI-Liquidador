@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title DIAN AI ENGINE - Diagnostico
cls
echo ================================================================
echo          DIAGNOSTICO DIAN AI ENGINE v0.6.4
echo ================================================================
echo.

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo [ERROR] Python no encontrado.
    goto END
)

echo Python:
%PYTHON_EXE% --version
echo.
echo Paquetes:
%PYTHON_EXE% -c "import fastapi,uvicorn,pydantic,numpy,torch; print('fastapi',fastapi.__version__); print('uvicorn',uvicorn.__version__); print('pydantic',pydantic.__version__); print('numpy',numpy.__version__); print('torch',torch.__version__)"
if errorlevel 1 echo [ERROR] Falta alguna dependencia.
echo.
echo API:
%PYTHON_EXE% -c "import src.api; print('API OK - version', src.api.ENGINE_VERSION)"
if errorlevel 1 echo [ERROR] No se pudo importar src.api.
echo.
echo Puerto 8787:
netstat -ano | findstr ":8787"
if errorlevel 1 echo [INFO] No hay proceso escuchando en 8787.
echo.
:END
echo ================================================================
pause
endlocal
