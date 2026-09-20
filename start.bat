@echo off
rem 切换控制台代码页为GBK，避免中文乱码，不再使用chcp 65001（UTF8会破坏%~dp0变量）
chcp 936 >nul
cd /d "%~dp0"
echo ======================================
echo 项目目录：%~dp0
echo 正在检测Python环境
echo ======================================
python --version >nul 2>&1
if errorlevel 1 (
    echo × 未识别到python命令！
    echo 请确认已安装Python3.12，并且安装时勾选【Add Python to PATH】
    pause
    exit /b
)
echo √ Python环境正常
echo.
echo 正在检查/安装依赖包（首次运行或者新增依赖会执行）
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
echo 启动Flask服务，浏览器会自动打开 http://127.0.0.1:5000
echo 【关闭此窗口即可停止服务】
echo.
start http://127.0.0.1:5000
python app.py
pause
