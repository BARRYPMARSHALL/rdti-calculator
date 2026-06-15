#!/bin/bash
# RDTI Calculator — One-command deploy
# Usage: DOMAIN=rdtcalculator.1st4.mobi STRIPE_SECRET_KEY=sk_live_xxx ./deploy.sh

set -euo pipefail

DOMAIN="${DOMAIN:-rdtcalculator.1st4.mobi}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-4}"

echo "==> RDTI Calculator Deploy"
echo "    Domain: $DOMAIN"
echo "    Port:   $PORT"

# Install deps
echo "==> Installing dependencies..."
python3 -m pip install -r requirements.txt -q

# Create .env for production
echo "==> Creating .env..."
cat > .env <<EOF
FLASK_ENV=production
DOMAIN=https://$DOMAIN
STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-}
STRIPE_PRICE_ID=${STRIPE_PRICE_ID:-price_rdti_report}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-}
PORT=$PORT
EOF

# Create systemd service
echo "==> Setting up systemd service..."
SERVICE_NAME="rdti-calculator"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=RDTI Calculator
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
EnvironmentFile=$(pwd)/.env
ExecStart=$(which gunicorn) app:app --workers $WORKERS --bind 0.0.0.0:\$PORT --timeout 30
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "==> Checking service..."
sleep 2
curl -s -o /dev/null -w "HTTP %{http_code}" "http://localhost:$PORT/api/calculate" \
  -X POST -H "Content-Type: application/json" -d '{"staff_count":1,"avg_salary":100000}' \
  && echo "" \
  || echo "⚠️  Health check failed"

echo ""
echo "==> ✅ Deployed at http://localhost:$PORT"
echo "    Public: https://$DOMAIN"

# Nginx hint
echo ""
echo "==> Nginx config hint:"
echo "    server {"
echo "        listen 80;"
echo "        server_name $DOMAIN;"
echo "        location / { proxy_pass http://localhost:$PORT; }"
echo "    }"
