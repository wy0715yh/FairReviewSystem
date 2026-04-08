#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  test)
    sudo nginx -t
    ;;
  reload)
    sudo systemctl reload nginx
    ;;
  restart)
    sudo systemctl restart nginx
    ;;
  status)
    sudo systemctl status nginx --no-pager -l
    ;;
  logs)
    sudo journalctl -u nginx -n 200 --no-pager
    ;;
  *)
    echo "usage: $0 {test|reload|restart|status|logs}"
    exit 1
    ;;
esac
