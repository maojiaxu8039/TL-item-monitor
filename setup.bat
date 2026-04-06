@echo off
chcp 65001 >nul
title TL物品火价监控 - 环境安装
cd /d "%~dp0"

echo ========================================
echo   TL 物品火价监控 - 环境安装
echo ========================================
echo.

:: 检测Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 安装 pyyaml...
pip install pyyaml
if errorlevel 1 (
    echo [错误] pyyaml 安装失败
    pause
    exit /b 1
)
echo [OK]

echo [2/3] 安装 playwright...
pip install playwright
if errorlevel 1 (
    echo [错误] playwright 安装失败
    pause
    exit /b 1
)
echo [OK]

echo [3/3] 安装 Chromium 浏览器（约100MB）...
python -m playwright install chromium
if errorlevel 1 (
    echo [错误] Chromium 安装失败
    pause
    exit /b 1
)
echo [OK]

echo.
echo ========================================
echo   环境安装完成！
echo ========================================
echo.
echo 下一步：双击运行 start.bat 启动服务
echo.
pause
