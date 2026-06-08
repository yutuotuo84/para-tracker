@echo off
cd /d %~dp0
echo ==============================
echo   PARA Tracker 启动中...
echo ==============================

if not exist venv (
    echo 正在创建虚拟环境...
    python -m venv venv
    call venv\Scripts\pip install -r requirements.txt
)

echo 激活虚拟环境...
call venv\Scripts\activate

echo 启动服务...
python main.py
