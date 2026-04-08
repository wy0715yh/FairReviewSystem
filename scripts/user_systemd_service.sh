#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fair-review.service"

case "${1:-}" in
  start)
    systemctl --user start "$SERVICE_NAME"
    ;;
  stop)
    systemctl --user stop "$SERVICE_NAME"
    ;;
  restart)
    systemctl --user restart "$SERVICE_NAME"
    ;;
  status)
    systemctl --user status "$SERVICE_NAME" --no-pager -l
    ;;
  logs)
    journalctl --user -u "$SERVICE_NAME" -n 200 --no-pager
    ;;
  enable)
    systemctl --user enable "$SERVICE_NAME"
    ;;
  disable)
    systemctl --user disable "$SERVICE_NAME"
    ;;
  *)
    echo "usage: $0 {start|stop|restart|status|logs|enable|disable}"
    exit 1
    ;;
esac
