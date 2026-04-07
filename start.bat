@echo off
@chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: 强制切换到脚本所在目录，防止找不到文件
cd /d "%~dp0"

title TL 产品价格监控 - 智能启动器

:: ==========================================
:: 定义需要检查的包列表
:: 注意：部分包的安装名和导入名不一致，已在下方映射好
:: ==========================================
set "REQ_PYTHON=Python 环境"
set "REQ_PLAYWRIGHT=playwright (浏览器自动化)"
set "REQ_PYYAML=pyyaml (配置文件)"
set "REQ_NUMPY=numpy (数据计算)"
set "REQ_PILLOW=pillow (图像处理)"
set "REQ_WINOTIFY=winotify (系统通知)"
set "REQ_PYWIN32=pywin32 (Windows系统接口)"

set "ERROR_FLAG=0"

cls
echo ========================================
echo   TL 产品价格监控 - 智能启动器
echo ========================================
echo.
echo [正在进行启动前全面检查...]
echo.

:: ==========================================
:: 第一关：检查 Python 基础环境
:: ==========================================
echo [1/8] 检查 %REQ_PYTHON%...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [✗] 未检测到 Python！请先安装 Python 并添加到环境变量。
    set "ERROR_FLAG=1"
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set VER=%%i
    echo   [✓] !VER!
)

:: 如果Python都没有，后面的检查也不用做了，直接退出
if !ERROR_FLAG! equ 1 goto final_check

:: ==========================================
:: 第二关：逐个检查依赖包
:: ==========================================
echo.
echo [2/8] 检查 %REQ_PLAYWRIGHT%...
python -c "import playwright" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [✗] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [✓] 已安装
)

echo.
echo [3/8] 检查 %REQ_PYYAML%...
:: 注意：pyyaml 安装名是 pyyaml，但导入是 yaml
python -c "import yaml" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [✗] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [✓] 已安装
)

echo.
echo [4/8] 检查 %REQ_NUMPY%...
python -c "import numpy" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [✗] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [✓] 已安装
)

echo.
echo [5/8] 检查 %REQ_PILLOW%...
:: 注意：pillow 导入是 PIL
python -c "import PIL" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [✗] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [✓] 已安装
)

echo.
echo [6/8] 检查 %REQ_WINOTIFY%...
python -c "import winotify" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [✗] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [✓] 已安装
)

echo.
echo [7/8] 检查 %REQ_PYWIN32%...
:: 注意：pywin32 通常导入 win32api 来检测
python -c "import win32api" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [✗] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [✓] 已安装
)

:: ==========================================
:: 第三关：检查项目文件是否存在
:: ==========================================
echo.
echo [8/8] 检查项目核心文件...
if not exist "server.py" (
    echo   [✗] 缺失 server.py
    set "ERROR_FLAG=1"
) else (
    echo   [✓] server.py 存在
)

if not exist "scraper.py" (
    echo   [✗] 缺失 scraper.py
    set "ERROR_FLAG=1"
) else (
    echo   [✓] scraper.py 存在
)

if not exist "notifier.py" (
    echo   [✗] 缺失 notifier.py
    set "ERROR_FLAG=1"
) else (
    echo   [✓] notifier.py 存在
)

:: ==========================================
:: 最终检查结果判定
:: ==========================================
:final_check
echo.
echo ========================================
if !ERROR_FLAG! equ 0 (
    echo   [状态] 所有检查通过 ✓
    echo ========================================
    echo.
    echo 正在启动服务...
    echo.
    python server.py
    
    echo.
    echo 服务已退出。
    pause
) else (
    echo   [状态] 检测到缺失项，无法启动 ✗
    echo ========================================
    echo.
    echo 请运行 "setup.bat" 安装缺失的依赖。
    echo.
    pause
    exit /b 1
)