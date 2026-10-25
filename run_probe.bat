@echo off
chcp 65001 >nul
cd /d "%~dp0"
".venv\Scripts\python.exe" probe_heic.py
echo.
echo Done. You can close this window.
pause
