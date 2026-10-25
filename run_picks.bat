@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist "decisions.json" (echo Save decisions.json from the review app into this folder first & pause & exit /b 1)
".venv\Scripts\python.exe" picks.py
pause
