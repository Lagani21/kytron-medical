#!/usr/bin/env bash
# deploy.sh — Run this on the EC2 instance after uploading the project
# Usage: bash deploy.sh
set -e

APP_DIR="/home/ubuntu/kyron-medical"

echo "=== [1/6] Installing system packages ==="
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv nodejs npm nginx

echo "=== [2/6] Backend: Python venv + dependencies ==="
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" -q

echo "=== [3/6] Frontend: npm install + build ==="
cd "$APP_DIR/frontend"
npm install --silent
npm run build

echo "=== [4/6] Copy frontend build to web root ==="
sudo mkdir -p /var/www/kyron-medical
sudo cp -r "$APP_DIR/frontend/dist/." /var/www/kyron-medical/

echo "=== [5/6] Configure Nginx ==="
sudo cp "$APP_DIR/nginx.conf" /etc/nginx/sites-available/kyron-medical
sudo ln -sf /etc/nginx/sites-available/kyron-medical /etc/nginx/sites-enabled/kyron-medical
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "=== [6/6] Install + start systemd service ==="
sudo cp "$APP_DIR/kyron-backend.service" /etc/systemd/system/kyron-backend.service
sudo systemctl daemon-reload
sudo systemctl enable kyron-backend
sudo systemctl restart kyron-backend
sudo systemctl status kyron-backend --no-pager

echo ""
echo "=== Done! ==="
EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "<your-ec2-ip>")
echo "App is live at: http://$EC2_IP"
