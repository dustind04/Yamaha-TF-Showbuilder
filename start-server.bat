@echo off
title TF Showbuilder Server
cd /d "%~dp0backend"

echo ========================================
echo   TF Showbuilder Server
echo   http://localhost:8000
echo   Press Ctrl+C to stop
echo ========================================
echo.

REM Try different ways to run uvicorn
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ) else (
        echo ERROR: Python not found in PATH
        echo Please install Python or add it to your PATH
        pause
    )
)

pause
