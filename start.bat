@echo off
@chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: 强制切换到脚本所在目录，防止找不到文件
cd /d "%~dp0"

title TL 产品价格监控 - 智能启动器

:: 定义需要检查的包列表
set "ERROR_FLAG=0"

cls
echo ========================================
echo   TL 产品价格监控 - 智能启动器
echo ========================================
echo.
echo [正在进行启动前全面检查...]
echo.

:: 第一关：检查 Python 基础环境
echo [1/8] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [失败] 未检测到 Python！请先安装 Python 并添加到环境变量。
    set "ERROR_FLAG=1"
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set VER=%%i
    echo   [成功] !VER!
)

:: 如果Python都没有，后面的检查也不用做了，直接退出
if !ERROR_FLAG! equ 1 goto final_check

:: 第二关：逐个检查依赖包
echo.
echo [2/8] 检查 playwright (浏览器自动化)...
python -c "import playwright" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [失败] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [成功] 已安装
)

echo.
echo [3/8] 检查 pyyaml (配置文件)...
python -c "import yaml" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [失败] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [成功] 已安装
)

echo.
echo [4/8] 检查 numpy (数据计算)...
python -c "import numpy" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [失败] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [成功] 已安装
)

echo.
echo [5/8] 检查 pillow (图像处理)...
python -c "import PIL" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [失败] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [成功] 已安装
)

echo.
echo [6/8] 检查 winotify (系统通知)...
python -c "import winotify" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [失败] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [成功] 已安装
)

echo.
echo [7/8] 检查 pywin32 (Windows系统接口)...
python -c "import win32api" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [失败] 缺失
    set "ERROR_FLAG=1"
) else (
    echo   [成功] 已安装
)

:: 第三关：检查项目文件是否存在
echo.
echo [8/8] 检查项目核心文件...
if not exist "server.py" (
    echo   [失败] 缺失 server.py
    set "ERROR_FLAG=1"
) else (
    echo   [成功] server.py 存在
)

if not exist "scraper.py" (
    echo   [失败] 缺失 scraper.py
    set "ERROR_FLAG=1"
) else (
    echo   [成功] scraper.py 存在
)

if not exist "notifier.py" (
    echo   [失败] 缺失 notifier.py
    set "ERROR_FLAG=1"
) else (
    echo   [成功] notifier.py 存在
)

:: 最终检查结果判定
:final_check
echo.
echo ========================================
if !ERROR_FLAG! equ 0 (
    echo   [状态] 所有检查通过
    echo ========================================
    echo.
    echo 正在启动服务...
    echo.
    python server.py
    
    echo.
    echo 服务已退出。
    pause
) else (
    echo   [状态] 检测到缺失项，无法启动
    echo ========================================
    echo.
    echo 请运行 "setup.bat" 安装缺失的依赖。
    echo.
    pause
    exit /b 1
)