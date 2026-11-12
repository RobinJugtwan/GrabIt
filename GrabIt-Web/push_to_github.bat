@echo off
title Push GrabIt to GitHub
cd /d "%~dp0"
echo ========================================================
echo              Pushing GrabIt Web to GitHub
echo ========================================================
echo.
git remote remove origin 2>nul
git remote add origin https://github.com/RobinJugtwan/GrabIt.git
git branch -M main
git push -u origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Your code is successfully uploaded to GitHub!
) else (
    echo [NOTE] If a browser opened, please click "Authorize" to finish.
)
echo.
pause
