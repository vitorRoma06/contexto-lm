@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ======================================
echo   CONTEXTO AI - Iniciar no Windows
echo ======================================
set "PY="
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set "PY=py -3.12"
)
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.11 --version >nul 2>nul
        if not errorlevel 1 set "PY=py -3.11"
    )
)
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo Python nao encontrado. Instale Python 3.11 ou 3.12 em python.org.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    %PY% -m venv .venv
    if errorlevel 1 goto :error
)
if not exist ".venv\.instalado" (
    echo Instalando dependencias (requer internet na primeira vez)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m spacy download pt_core_news_md
    if errorlevel 1 goto :error
    echo ok > ".venv\.instalado"
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto :error
pause
exit /b 0
:error
echo.
echo Falha na instalacao ou execucao. Confira a mensagem acima.
pause
exit /b 1
