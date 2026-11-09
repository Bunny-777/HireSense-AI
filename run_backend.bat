@echo off
title HireSense AI - Backend Server
echo ========================================================
echo  HireSense AI - FastAPI Backend Server
echo  Listening at http://127.0.0.1:8000
echo ========================================================
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
) else (
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
)
pause
