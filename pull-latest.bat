@echo off
title TF Showbuilder - Pull Latest
cd /d "%~dp0"

echo ========================================
echo   TF Showbuilder - Pull Latest
echo ========================================
echo.

git pull origin claude/install-test-server-jvnPC

echo.
echo Done! Press any key to close.
pause >nul
