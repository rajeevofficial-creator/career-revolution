@echo off
echo Opening Career Revolution Frontend...
echo.
echo Make sure the backend is running first!
echo Backend: http://localhost:8000
echo.
echo Opening frontend in browser...
start "" "simple_frontend\index.html"
echo.
echo Frontend opened!
echo.
echo If you see "API Offline" message:
echo 1. Make sure backend is running (python run.py)
echo 2. Wait a few seconds for backend to start
echo 3. Refresh the page
echo.
pause