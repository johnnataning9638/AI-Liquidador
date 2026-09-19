@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title DIAN AI ENGINE v0.6.4 - Servidor local

cls
echo ================================================================
echo              DIAN AI ENGINE v0.6.4
 echo ================================================================
echo.
echo Carpeta: %CD%
echo Puerto : 8787
echo Host   : 127.0.0.1
echo.

REM ---------------------------------------------------------------
REM 1. Locate Python
REM ---------------------------------------------------------------
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo [ERROR] No se encontro Python.
    echo.
    echo Instale Python 3.10 o superior y vuelva a ejecutar este archivo.
    echo Recomendado: marcar ^"Add Python to PATH^" durante la instalacion.
    echo.
    goto :ERROR_PAUSE
)

echo [1/4] Python encontrado:
echo        %PYTHON_EXE%
%PYTHON_EXE% --version
if errorlevel 1 (
    echo [ERROR] Python no pudo ejecutarse correctamente.
    goto :ERROR_PAUSE
)
echo.

REM ---------------------------------------------------------------
REM 2. Check required Python packages
REM ---------------------------------------------------------------
echo [2/4] Verificando dependencias...
%PYTHON_EXE% -c "import fastapi,uvicorn,pydantic,numpy,torch; print('Dependencias OK')" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Faltan una o mas dependencias.
    echo.
    echo Se intentara instalarlas desde requirements.txt.
    echo Esto puede tardar, especialmente al instalar PyTorch.
    echo.
    %PYTHON_EXE% -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] pip no esta disponible en este Python.
        goto :ERROR_PAUSE
    )
    %PYTHON_EXE% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] No fue posible instalar las dependencias.
        echo Revise el mensaje anterior y la conexion a Internet.
        goto :ERROR_PAUSE
    )
) else (
    echo        Dependencias OK.
)
echo.

REM ---------------------------------------------------------------
REM 3. Import test of the actual API
REM ---------------------------------------------------------------
echo [3/4] Verificando el modulo del AI Engine...
%PYTHON_EXE% -c "import src.api; print('API OK - version', src.api.ENGINE_VERSION)"
if errorlevel 1 (
    echo.
    echo [ERROR] El API no pudo cargarse.
    echo La ventana permanecera abierta para revisar el error.
    goto :ERROR_PAUSE
)
echo.

REM ---------------------------------------------------------------
REM 4. Start server
REM ---------------------------------------------------------------
echo [4/4] Iniciando servidor...
echo.
echo ================================================================
echo   AI ENGINE DISPONIBLE EN:
echo   http://127.0.0.1:8787
 echo.
echo   Health: http://127.0.0.1:8787/health
 echo.
echo   NO CIERRE ESTA VENTANA mientras use el Liquidador.
echo ================================================================
echo.

%PYTHON_EXE% -m uvicorn src.api:app --host 127.0.0.1 --port 8787
set "SERVER_EXIT=%ERRORLEVEL%"

echo.
echo ================================================================
echo El servidor se detuvo. Codigo de salida: %SERVER_EXIT%
echo ================================================================
goto :ERROR_PAUSE

:ERROR_PAUSE
echo.
echo ---------------------------------------------------------------
echo La ventana se mantendra abierta para que pueda leer el diagnostico.
echo Presione una tecla para cerrar.
echo ---------------------------------------------------------------
pause >nul
endlocal
exit /b 1
