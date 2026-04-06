@echo off

echo ========================================
echo   TL 物品火价监控 - 启动中
echo ========================================
echo.
echo [1/2] 检查依赖...
python -c "import server, scraper, notifier" >nul 2>&1
if errorlevel 1 (
    echo   错误：依赖未安装，请先运行 setup.bat
    echo.
    pause
    exit /b 1
)
echo   OK - 依赖检查通过

echo [2/2] 启动服务器...
echo.
python server.py
