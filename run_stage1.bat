@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === Trip album - stage 1 (reads originals, never changes them) ===
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  echo Python 3 was not found. Install it from https://www.python.org/downloads/ ^(tick "Add to PATH"^), then run this again.
  pause & exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating private Python environment...
  %PY% -m venv .venv || (echo venv failed & pause & exit /b 1)
)
echo Installing libraries ^(first run only^)...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check av pillow pillow-heif==1.1.1 numpy opencv-python-headless || (echo pip install failed & pause & exit /b 1)
echo Processing... this can take 20-60 minutes for 10 GB. You can stop it (Ctrl+C) and re-run; it resumes.
".venv\Scripts\python.exe" album_index.py ".." 
echo.
pause
