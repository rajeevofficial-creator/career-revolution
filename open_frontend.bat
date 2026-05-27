@echo off
echo ========================================
echo Career Revolution Frontend Launcher
echo ========================================
echo.
echo This will open the Career Revolution frontend in your default browser.
echo Make sure the backend API is running first!
echo.
echo Backend API: http://localhost:8000
echo Frontend: simple_frontend/index.html
echo.
echo Press any key to open the frontend...
pause > nul

start "" "simple_frontend\index.html"

echo.
echo Frontend opened in browser!
echo.
echo To start the backend API, run:
echo   python run.py
echo.
pause