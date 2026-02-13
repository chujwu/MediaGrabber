@echo off
chcp 65001 >nul
title 安装依赖

echo ========================================
echo    安装项目依赖
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python！
    pause
    exit /b 1
)

echo [1/3] 升级 pip...
python -m pip install --upgrade pip

echo.
echo [2/3] 安装项目依赖...
pip install -r requirements.txt

echo.
echo [3/3] 安装 yt-dlp 完整包（包含 YouTube 支持）...
pip install "yt-dlp[default]"

echo.
echo ========================================
echo    安装完成！
echo ========================================
echo.
echo 下一步：
echo 1. 安装 Deno（YouTube 下载需要）
echo    PowerShell 管理员模式运行：
echo    irm https://deno.land/install.ps1 ^| iex
echo.
echo 2. 运行程序
echo    双击 "启动程序.bat"
echo.
pause
