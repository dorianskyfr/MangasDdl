@echo off
setlocal
cd /d "%~dp0"
title MangasDdl 1.0
if exist "MangasDdl.exe" (
    start "" "MangasDdl.exe"
    exit /b 0
)
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
    if errorlevel 1 goto :error
)
".venv\Scripts\python.exe" -c "import PySide6, httpx, bs4, PIL, img2pdf, lxml, packaging" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
    if errorlevel 1 goto :error
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :error
exit /b 0
:error
echo Impossible de lancer MangasDdl. Installez Python 3.12 et verifiez votre connexion.
pause
exit /b 1
