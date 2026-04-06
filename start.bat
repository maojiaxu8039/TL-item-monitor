@echo off
chcp 65001 >nul
title TL物品火价监控
cd /d "%~dp0"

echo ========================================
echo   TL 物品火价监控 - 启动中
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

:: 安装依赖（如果需要）
echo [1/2] 检查依赖...
pip show pyyaml >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 pyyaml...
    pip install pyyaml
)

pip show playwright >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 playwright...
    pip install playwright
    echo [提示] 正在安装 Chromium 浏览器...
    python -m playwright install chromium
)

:: 启动服务器
echo [2/2] 启动服务器...
echo.
echo 访问地址: http://localhost:19877
echo 关闭方法: 按 Ctrl+C 或关闭此窗口
echo.
python server.py
pause
