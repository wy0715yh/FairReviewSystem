#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fair-review.service"
PROJECT_DIR="/home/user/progect/FairReviewSystem"
UNIT_SRC="$PROJECT_DIR/deploy/user/$SERVICE_NAME"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_DST="$UNIT_DIR/$SERVICE_NAME"
VENV_DIR="$PROJECT_DIR/.venv-deploy"

mkdir -p "$UNIT_DIR"
if python3 -m venv "$VENV_DIR" 2>/dev/null; then
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
else
  echo "venv unavailable, fallback to user install"
  python3 -m pip install --user --break-system-packages -r "$PROJECT_DIR/requirements.txt"
fi
cp "$UNIT_SRC" "$UNIT_DST"

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"
systemctl --user status "$SERVICE_NAME" --no-pager -l

echo "Done."
