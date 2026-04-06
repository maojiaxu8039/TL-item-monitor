@echo off
chcp 65001 >nul
title TL物品火价监控 - 打包构建

echo ========================================
echo   打包构建（包含 Playwright + Chromium）
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装
    pause
    exit /b 1
)

:: 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [1/4] 安装 PyInstaller...
    pip install pyinstaller
) else (
    echo [跳过] PyInstaller 已安装
)

:: 确保 Playwright Chromium 已安装
echo [2/4] 检查 Playwright Chromium...
python -c "from playwright.paths import browser_executable_path; print(browser_executable_path('chromium'))" >nul 2>&1
if errorlevel 1 (
    echo         安装 Chromium（约100MB）...
    python -m playwright install chromium
)

:: 打包
echo [3/4] PyInstaller 打包中（约3-5分钟）...
pyinstaller TL_monitor.spec --clean -y
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

:: 复制浏览器到 dist
echo [4/4] 复制 Chromium 到输出目录...
set "BROWSER_PATH="
for /f "delims=" %%i in ('python -c "from playwright.paths import browser_executable_path; print(browser_executable_path('\''chromium'\''))"') do set "BROWSER_PATH=%%i"
if not "%BROWSER_PATH%"=="" (
    set "CHROMIUM_DIR=%BROWSER_PATH%\..\.."
    xcopy /E /I /Y "%CHROMIUM_DIR%\chromium*" "dist\TL_monitor\playwright_browsers\" >nul 2>&1
    echo         已复制 Chromium
)

echo.
echo ========================================
echo   打包完成！
echo   输出目录: dist\TL_monitor\
echo.
echo   启动方式: 双击 dist\TL_monitor\TL_monitor.exe
echo.
pause
