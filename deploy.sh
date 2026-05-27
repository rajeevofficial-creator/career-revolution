#!/bin/bash
# Deploy Career Revolution to Oracle VM
# Usage:  bash deploy.sh YOUR_ORACLE_IP
#
# What it does:
#   1. Rsyncs the app to /opt/career-revolution on the Oracle VM
#   2. Installs / updates Python dependencies
#   3. Runs DB migrations
#   4. Starts (or restarts) the app with PM2 on port 8010
#   5. Reloads Nginx

ORACLE_IP="${1:?Usage: bash deploy.sh YOUR_ORACLE_IP}"
ORACLE_USER="ubuntu"
SSH_KEY="$HOME/.ssh/oracle_key"
REMOTE_DIR="/opt/career-revolution"
APP_NAME="career-revolution"

echo "==> Deploying Career Revolution to $ORACLE_IP ..."

# ── 1. Push code (exclude secrets, DBs, uploads, profiles) ───────────────────
rsync -avz --progress \
  --exclude='.env' \
  --exclude='*.db' \
  --exclude='uploads/' \
  --exclude='browser_profiles/' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='*.pyc' \
  -e "ssh -i $SSH_KEY" \
  . "$ORACLE_USER@$ORACLE_IP:$REMOTE_DIR/"

echo "==> Code synced."

# ── 2. Remote setup ───────────────────────────────────────────────────────────
ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_IP" << EOF
  set -e
  cd $REMOTE_DIR

  # Create uploads dirs if not present
  mkdir -p uploads browser_profiles

  # Python virtualenv
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi
  source .venv/bin/activate

  # Dependencies
  pip install -q --upgrade pip
  pip install -q -r requirements.txt

  # Playwright browsers (only installs if not present)
  python -m playwright install chromium --with-deps 2>/dev/null || true

  # Copy .env if it doesn't exist on server (first deploy)
  if [ ! -f ".env" ]; then
    echo "WARNING: .env not found on server — app will fail to start."
    echo "         SCP your .env to $REMOTE_DIR/.env and restart."
  fi

  # Start / restart with PM2
  if pm2 describe $APP_NAME > /dev/null 2>&1; then
    pm2 reload $APP_NAME --update-env
    echo "PM2: reloaded $APP_NAME"
  else
    pm2 start ecosystem.config.js --only $APP_NAME
    echo "PM2: started $APP_NAME"
  fi

  pm2 save
EOF

echo "==> App running on port 8010."

# ── 3. Deploy/reload Nginx ────────────────────────────────────────────────────
# Only update the nginx config if kennmi-landing dir is alongside this repo
NGINX_CONF="$(dirname "$0")/../kennmi-landing/nginx-kennmi.conf"
if [ -f "$NGINX_CONF" ]; then
  scp -i "$SSH_KEY" "$NGINX_CONF" "$ORACLE_USER@$ORACLE_IP:/tmp/kennmi.conf"
  ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_IP" "
    sudo cp /tmp/kennmi.conf /etc/nginx/sites-available/kennmi.com
    sudo nginx -t && sudo systemctl reload nginx
    echo 'Nginx reloaded.'
  "
fi

echo ""
echo "✓ Career Revolution deployed!"
echo "  App:    https://career.kennmi.com"
echo ""
echo "Next steps if this is the first deploy:"
echo "  1. SCP your .env:  scp -i $SSH_KEY .env $ORACLE_USER@$ORACLE_IP:$REMOTE_DIR/.env"
echo "  2. Add DNS record:  career.kennmi.com  →  $ORACLE_IP  (A record in Cloudflare)"
echo "  3. Enable HTTPS:   sudo certbot --nginx -d career.kennmi.com"
