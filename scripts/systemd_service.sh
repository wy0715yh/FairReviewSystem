#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fair-review.service"

case "${1:-}" in
  start)
    sudo systemctl start "$SERVICE_NAME"
    ;;
  stop)
    sudo systemctl stop "$SERVICE_NAME"
    ;;
  restart)
    sudo systemctl restart "$SERVICE_NAME"
    ;;
  status)
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
    ;;
  logs)
    sudo journalctl -u "$SERVICE_NAME" -n 200 --no-pager
    ;;
  enable)
    sudo systemctl enable "$SERVICE_NAME"
    ;;
  disable)
    sudo systemctl disable "$SERVICE_NAME"
    ;;
  *)
    echo "usage: $0 {start|stop|restart|status|logs|enable|disable}"
    exit 1
    ;;
esac
