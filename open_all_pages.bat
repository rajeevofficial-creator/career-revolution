@echo off
echo Opening Career Revolution Application...
echo.

echo 1. Opening Login Page (Main Landing Page)...
start "" "login.html"

echo 2. Opening Registration Page...
start "" "register.html"

echo 3. Opening Dashboard (will redirect to login if not authenticated)...
start "" "dashboard.html"

echo.
echo All pages opened!
echo.
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
pause