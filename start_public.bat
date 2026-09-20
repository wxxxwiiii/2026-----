@echo off
chcp 936 >nul
cd /d "%~dp0"

echo ============================================================
echo   云体智师 - 公网演示一键启动（ngrok 内网穿透）
echo ============================================================
echo.

where ngrok >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 ngrok 命令。
    echo   请先完成以下步骤：
    echo   1. 下载 ngrok 并解压到本地目录；
    echo   2. 将该目录加入系统环境变量 PATH；
    echo   3. 执行 ngrok config add-authtoken 你的token 完成认证。
    echo.
    pause
    exit /b 1
)
echo [提示] 已检测到 ngrok。请确认已配置 ngrok authtoken。

echo.
echo [1/2] 正在新窗口启动 Flask 服务（start.bat）...
start "云体智师-Flask服务" cmd /k call start.bat

echo [提示] 等待 Flask 服务启动（约 10 秒，首次运行安装依赖会更久）...
timeout /t 10 /nobreak >nul

echo [2/2] 正在新窗口启动 ngrok 内网穿透（http 5000）...
start "云体智师-ngrok内网穿透" cmd /k ngrok http 5000

echo.
echo ============================================================
echo   启动完成！
echo   - Flask 服务窗口：本地 http://127.0.0.1:5000
echo   - ngrok 窗口：会显示公网访问链接（Forwarding 行）
echo     该 https:// 链接即为评审访问的测试网址。
echo.
echo   【重要】两个窗口均不可关闭，关闭则公网访问失效。
echo   【提示】若 ngrok 提示认证失败，请先执行
echo          ngrok config add-authtoken 你的token
echo ============================================================
echo.
pause
