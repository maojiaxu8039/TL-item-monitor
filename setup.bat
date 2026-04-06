@echo off
chcp 65001 >nul
echo ============================================
echo  TL Monitor 环境安装脚本
echo ============================================
echo.

echo [1/3] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python，请先安装 Python 3.11+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

echo [2/3] 安装 Python 依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误：依赖安装失败
    pause
    exit /b 1
)
echo.

echo [3/3] 安装 Chromium 浏览器...
playwright install chromium
if errorlevel 1 (
    echo 错误：Chromium 安装失败
    pause
    exit /b 1
)
echo.

echo ============================================
echo  环境安装完成！
echo ============================================
echo.
echo 运行方式：
echo   python server.py
echo.
pause
