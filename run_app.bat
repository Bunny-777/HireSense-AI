@echo off
title HireSense AI - Launcher
echo ========================================================
echo  Starting HireSense AI Full-Stack Application...
echo ========================================================
cd /d "%~dp0"
start "HireSense Backend" cmd /k "run_backend.bat"
start "HireSense Frontend" cmd /k "run_frontend.bat"
echo.
echo Both servers are launching!
echo  Backend:  http://127.0.0.1:8000
echo  Frontend: http://localhost:5173
echo.
echo Open http://localhost:5173 in your browser to test the UI.
