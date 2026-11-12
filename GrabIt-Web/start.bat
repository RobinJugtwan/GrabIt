@echo off
title GrabIt Web Server
cd /d "%~dp0"
echo ========================================================
echo               Starting GrabIt Web Server
echo ========================================================
echo.
echo Installing/checking dependencies...
pip install -r requirements.txt
echo.
echo Launching server at http://localhost:8000 ...
echo Press Ctrl+C anytime to stop.
echo.
python main.py
pause
