@echo off
chcp 65001 >nul
echo ========================================
echo    YouTube 下载器 - 快速配置脚本
echo ========================================
echo.
echo 正在检查配置...
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [✓] Python 已安装

REM 检查 pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] pip 不可用
    pause
    exit /b 1
)
echo [✓] pip 可用

REM 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [⚠] Node.js 未安装（可选）
) else (
    echo [✓] Node.js 已安装
)

REM 检查 Deno
deno --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo [⚠] Deno 未安装
    echo ========================================
    echo.
    echo Deno 是下载 YouTube 视频的必要组件。
    echo.
    echo 请按以下步骤安装 Deno：
    echo.
    echo 1. 以管理员身份打开 PowerShell
    echo 2. 运行命令：
    echo    irm https://deno.land/install.ps1 ^| iex
    echo.
    echo 或者访问：https://deno.land/
    echo.
    pause
    exit /b 1
) else (
    echo [✓] Deno 已安装
)

echo.
echo ========================================
echo    所有依赖检查完成！
echo ========================================
echo.
echo 现在可以运行主程序了：
echo    python main.py
echo.
pause
