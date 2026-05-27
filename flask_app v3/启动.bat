@echo off
chcp 65001 >nul
title 小学做题网站

echo ========================================
echo    🚀 小学做题网站 - 一键启动
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)
echo [✓] Python 已就绪

:: 检查并安装依赖
echo.
echo [*] 检查依赖包...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
if %errorlevel% neq 0 (
    echo [!] 清华镜像失败，尝试官方源...
    pip install -r requirements.txt --quiet
)
echo [✓] 依赖已就绪

:: 启动后端
echo.
echo [*] 启动 Flask 后端...
cd /d "%~dp0backend"
start "" python app.py

:: 等待后端启动
echo [*] 等待服务启动...
timeout /t 3 /nobreak >nul

:: 打开浏览器
echo [✓] 启动完成，打开浏览器...
start http://127.0.0.1:5000

echo.
echo 按任意键关闭此窗口（不影响后端运行）
pause >nul
