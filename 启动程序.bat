@echo off
chcp 65001 >nul
title YouTube 视频下载器

echo ========================================
echo    YouTube 视频下载器 v2.0
echo    UI优化版 - 2025-02-12
echo ========================================
echo.
echo 正在启动程序...
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python！
    echo 请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 启动主程序
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo 程序运行出错！
    echo ========================================
    echo.
    echo 请检查以下内容：
    echo 1. 是否安装了所有依赖：pip install -r requirements.txt
    echo 2. Python 版本是否为 3.8+
    echo 3. 查看错误信息并修复
    echo.
)

pause
