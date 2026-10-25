@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === Building frame pickers for videos (originals are not touched) ===
if not exist ".venv\Scripts\python.exe" (echo Run run_stage1.bat first & pause & exit /b 1)
".venv\Scripts\python.exe" film.py
echo.
echo Done. Reload review.html.
pause
