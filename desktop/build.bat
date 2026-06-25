@echo off
REM Build TokenScope.exe (system-tray app). Run from the desktop\ folder.
setlocal
cd /d "%~dp0"

echo [1/3] Creating build venv...
python -m venv .venv || goto :err
call .venv\Scripts\activate.bat || goto :err

echo [2/3] Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller || goto :err

echo [3/3] Building single-file exe...
pyinstaller --noconfirm tokenscope-tray.spec || goto :err

echo.
echo  DONE  ->  dist\TokenScope.exe
echo  Double-click it: a tray icon appears and the dashboard opens in your browser.
goto :eof

:err
echo.
echo  BUILD FAILED (see output above).
exit /b 1
