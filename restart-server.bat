@echo off
title TF Showbuilder - Restart Server
cd /d "%~dp0"

echo ========================================
echo   TF Showbuilder - Pull and Restart
echo ========================================
echo.

echo [1/3] Pulling latest changes...
git pull origin claude/install-test-server-jvnPC
echo.

echo [2/3] Stopping existing server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq TF*" 2>nul
timeout /t 2 /nobreak >nul

echo [3/3] Starting server...
cd backend
start "TF Showbuilder Server" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo ========================================
echo   Server started on http://localhost:8000
echo   Press any key to close this window.
echo ========================================
pause >nul
