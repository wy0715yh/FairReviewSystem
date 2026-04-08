#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/user/progect/FairReviewSystem"
VENV_GUNICORN="$PROJECT_DIR/.venv-deploy/bin/gunicorn"
USER_GUNICORN="$HOME/.local/bin/gunicorn"
CONF="$PROJECT_DIR/deploy/gunicorn.conf.py"

if [[ -x "$VENV_GUNICORN" ]]; then
  exec "$VENV_GUNICORN" app:app -c "$CONF"
fi

if [[ -x "$USER_GUNICORN" ]]; then
  exec "$USER_GUNICORN" app:app -c "$CONF"
fi

echo "gunicorn not found. Run install script first." >&2
exit 1
