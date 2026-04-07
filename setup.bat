@echo off
@chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Python 依赖包自动安装工具 (国内极速版)

:: 定义要安装的包列表
set "packages=playwright pyyaml numpy pillow winotify pywin32"
set "failed_packages="
set "success_count=0"
set "fail_count=0"

:: 定义国内镜像源地址 (清华大学)
set "PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"
set "TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn"

:: 强制切换到脚本所在目录，避免路径问题
cd /d "%~dp0"

cls
echo ==========================================
echo 正在检查 Python 环境...
echo ==========================================

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 并勾选"Add Python to PATH"
    pause
    exit /b 1
)

echo [成功] 检测到 Python 环境
python --version
echo.

:: 升级 pip 到最新版本 (使用国内源)
echo ==========================================
echo 正在升级 pip 到最新版本...
echo ==========================================
python -m pip install --upgrade pip -i %PYPI_MIRROR% --trusted-host %TRUSTED_HOST%
echo.

echo ==========================================
echo 开始批量安装依赖包
echo (使用清华镜像源，单包超时120秒)
echo ==========================================

:: 循环安装每个包
for %%p in (%packages%) do (
    echo.
    echo [正在安装] %%p
    echo ------------------------------------------
    
    pip install --default-timeout=120 -i %PYPI_MIRROR% --trusted-host %TRUSTED_HOST% %%p
    
    if !errorlevel! equ 0 (
        echo [成功] %%p 安装完成
        set /a success_count+=1
    ) else (
        echo [失败] %%p 安装未完成
        set "failed_packages=!failed_packages! %%p"
        set /a fail_count+=1
    )
)

:: 特殊处理：Playwright 浏览器安装
echo.
echo ==========================================
echo 正在配置 Playwright 浏览器内核...
echo ==========================================
playwright install
echo.

:: 最终安装报告
echo ==========================================
echo          安装任务执行完毕
echo ==========================================
echo 成功安装: !success_count! 个
echo 安装失败: !fail_count! 个

if !fail_count! gtr 0 (
    echo.
    echo ------------------------------------------
    echo 以下包安装失败，请手动重试:
    echo !failed_packages!
    echo ------------------------------------------
    echo 手动重试命令:
    echo pip install [包名] --default-timeout=120 -i %PYPI_MIRROR% --trusted-host %TRUSTED_HOST%
) else (
    echo.
    echo 恭喜！所有依赖包均已成功安装
)

echo ==========================================
pause