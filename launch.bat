@echo off
title AI Software Factory
cd /d "%~dp0"

echo.
echo  =============================================
echo   AI Software Factory  ^|  Autonomous Delivery
echo  =============================================
echo.

REM Run the workflow engine to produce fresh output
echo [1/2] Running workflow engine...
set PYTHONPATH=src
".venv\Scripts\python.exe" -m ai_software_factory
if errorlevel 1 (
    echo ERROR: Workflow engine failed. Check your Python environment.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting dashboard...
echo       http://localhost:8501
echo.
echo  Press Ctrl+C to stop the server.
echo.

start "" http://localhost:8501
".venv\Scripts\streamlit.exe" run ui\app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false
