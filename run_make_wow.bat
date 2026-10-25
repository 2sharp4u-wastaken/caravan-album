@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === Building for_wow (numbered, print-ready JPEGs). Originals are not touched. ===
if not exist ".venv\Scripts\python.exe" (echo Run run_stage1.bat first & pause & exit /b 1)
".venv\Scripts\python.exe" make_wow.py %*
echo.
pause
