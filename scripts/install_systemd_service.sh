#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fair-review.service"
PROJECT_DIR="/home/user/progect/FairReviewSystem"
UNIT_SRC="$PROJECT_DIR/deploy/$SERVICE_NAME"
UNIT_DST="/etc/systemd/system/$SERVICE_NAME"
VENV_DIR="$PROJECT_DIR/.venv-deploy"

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "service file not found: $UNIT_SRC"
  exit 1
fi

echo "[1/4] Installing Python deps (including gunicorn)..."
if python3 -m venv "$VENV_DIR" 2>/dev/null; then
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
else
  echo "venv unavailable, fallback to user install"
  python3 -m pip install --user --break-system-packages -r "$PROJECT_DIR/requirements.txt"
fi

echo "[2/4] Installing systemd unit..."
sudo cp "$UNIT_SRC" "$UNIT_DST"

echo "[3/4] Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo "[4/4] Restarting service..."
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager -l

echo "Done."
