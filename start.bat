@echo off

echo ========================================
echo   TL Item Fire Price Monitor - Starting
echo ========================================
echo.
echo [1/2] Checking dependencies...
python -c "import server, scraper, notifier" >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Dependencies not installed. Please run setup.bat first.
    echo.
    pause
    exit /b 1
)
echo   OK - All dependencies ready

echo [2/2] Starting server...
echo.
python server.py
