@echo off
echo ========================================
echo Career Revolution - Complete Startup
echo ========================================
echo.
echo This script will:
echo 1. Check and install Python dependencies
echo 2. Start the backend API server
echo 3. Open the frontend in your browser
echo.
echo ========================================
echo.

REM Step 1: Check Python installation
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)
echo ✓ Python is installed

REM Step 2: Check dependencies
echo.
echo [2/3] Checking Python dependencies...
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check for essential packages
python -c "import fastapi, uvicorn, sqlalchemy, jose, passlib" >nul 2>&1
if errorlevel 1 (
    echo Installing required dependencies...
    pip install -r requirements.txt --user
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        echo Please check your Python/pip installation
        pause
        exit /b 1
    )
    echo ✓ Dependencies installed
) else (
    echo ✓ All dependencies are already installed
)

REM Step 3: Start backend
echo.
echo [3/3] Starting Career Revolution system...
echo.

REM Start backend in a new window
echo Starting backend API server...
echo Backend will run at: http://localhost:8010
echo API Documentation: http://localhost:8010/docs
echo.
start "Career Revolution Backend" cmd /k "venv\Scripts\python.exe run.py"

REM Wait for backend to start
echo Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

REM Step 4: Open frontend
echo.
echo Opening frontend in browser...
start "" "simple_frontend\index.html"

echo.
echo ========================================
echo SYSTEM STARTED SUCCESSFULLY!
echo ========================================
echo.
echo Backend API: http://localhost:8010
echo Frontend: simple_frontend/index.html
echo API Docs: http://localhost:8010/docs
echo.
echo Instructions:
echo 1. Register a new account in the frontend
echo 2. Login with your credentials
echo 3. Upload documents (CVs, certifications)
echo 4. Edit your profile
echo 5. View your dashboard
echo.
echo Sample credentials for testing:
echo Email: test@example.com
echo Password: SecurePass123
echo.
echo Press any key to close this window...
pause >nul