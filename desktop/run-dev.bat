@echo off
REM Run the tray app without building an exe (needs deps from requirements.txt).
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python tray.py
