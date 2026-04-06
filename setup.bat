@echo off

echo ============================================
echo  TL Monitor - Environment Setup
echo ============================================
echo.

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Please install Python 3.11+
    echo   Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

echo [2/3] Installing Python packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo   ERROR: Package installation failed
    pause
    exit /b 1
)
echo.

echo [3/3] Installing Chromium browser...
playwright install chromium
if errorlevel 1 (
    echo   ERROR: Chromium installation failed
    pause
    exit /b 1
)
echo.

echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo Next step: Run start.bat to launch the server
echo.
pause
