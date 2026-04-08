#!/usr/bin/env bash
set -euo pipefail

SITE_NAME="fair-review"
CONF_SRC="/home/user/progect/FairReviewSystem/deploy/nginx-fair-review.conf"
CONF_DST="/etc/nginx/sites-available/${SITE_NAME}.conf"
LINK_DST="/etc/nginx/sites-enabled/${SITE_NAME}.conf"

if [[ ! -f "$CONF_SRC" ]]; then
  echo "nginx conf not found: $CONF_SRC"
  exit 1
fi

echo "[1/4] Copy nginx site config"
sudo cp "$CONF_SRC" "$CONF_DST"

echo "[2/4] Enable site"
sudo ln -sf "$CONF_DST" "$LINK_DST"

echo "[3/4] Validate nginx config"
sudo nginx -t

echo "[4/4] Reload nginx"
sudo systemctl reload nginx

echo "Done."
