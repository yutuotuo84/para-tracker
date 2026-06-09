#!/bin/bash
# PARA Tracker 服务器部署脚本（Ubuntu/Debian）
set -e

echo "=== PARA Tracker 部署开始 ==="

# 1. 安装系统依赖
echo "[1/6] 安装系统依赖..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git

# 2. 克隆项目
echo "[2/6] 克隆项目..."
sudo mkdir -p /opt
sudo git clone https://github.com/yutuotuo84/para-tracker.git /opt/para-tracker
cd /opt/para-tracker

# 3. 创建虚拟环境并安装依赖
echo "[3/6] 安装 Python 依赖..."
sudo python3 -m venv venv
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt

# 4. 配置 .env
echo "[4/6] 配置环境变量..."
if [ ! -f .env ]; then
    sudo cp .env.example .env
    echo "===== 请编辑 /opt/para-tracker/.env 填入你的配置 ====="
    echo "  如 TICKTICK_USERNAME、FLOMO_API_URL 等"
    echo "  也可留空纯本地使用"
fi

# 5. 配置 systemd 服务
echo "[5/6] 配置 systemd 服务..."
sudo cp deploy/para-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable para-tracker
sudo systemctl start para-tracker

# 6. 配置 nginx
echo "[6/6] 配置 nginx..."
echo "===== 请先编辑 deploy/para-tracker.nginx ====="
echo "  将 your-domain.com 替换为你的实际域名或 IP"
echo "然后执行以下命令:"
echo "  sudo cp deploy/para-tracker.nginx /etc/nginx/sites-available/para-tracker"
echo "  sudo ln -s /etc/nginx/sites-available/para-tracker /etc/nginx/sites-enabled/"
echo "  sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "如需 HTTPS，请运行:"
echo "  sudo apt install -y certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d your-domain.com"
echo ""
echo "=== 部署完成 ==="
echo "服务状态: sudo systemctl status para-tracker"
echo "查看日志: sudo journalctl -u para-tracker -f"
