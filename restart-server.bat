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
taskkill /F /IM python.exe 2>nul
taskkill /F /IM py.exe 2>nul
timeout /t 2 /nobreak >nul

echo [3/3] Starting server...
cd backend

REM Try python first, then py
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "TF Showbuilder Server" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        start "TF Showbuilder Server" cmd /k "py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    ) else (
        echo ERROR: Python not found in PATH
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo   Server started on http://localhost:8000
echo ========================================
timeout /t 3 >nul
