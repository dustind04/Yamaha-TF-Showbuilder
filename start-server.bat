@echo off
title TF Showbuilder Server
cd /d "%~dp0\backend"

echo ========================================
echo   TF Showbuilder Server
echo   http://localhost:8000
echo   Press Ctrl+C to stop
echo ========================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
