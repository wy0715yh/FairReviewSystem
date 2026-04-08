#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/user/progect/FairReviewSystem"
RUNNER="$BASE_DIR/scripts/run_gunicorn.sh"
LOG_FILE="/tmp/fair_review_system.log"
PID_FILE="/tmp/fair_review_system.pid"

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start() {
  if is_running; then
    echo "already running: PID $(cat "$PID_FILE")"
    return 0
  fi

  cd "$BASE_DIR"
  nohup setsid "$RUNNER" >>"$LOG_FILE" 2>&1 < /dev/null &
  local pid=$!
  echo "$pid" > "$PID_FILE"

  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    echo "started: PID $pid"
  else
    echo "start failed, check $LOG_FILE"
    return 1
  fi
}

stop() {
  if ! is_running; then
    echo "not running"
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid=$(cat "$PID_FILE")
  kill "$pid" 2>/dev/null || true
  pkill -f "gunicorn.*app:app" 2>/dev/null || true
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  echo "stopped"
}

status() {
  if is_running; then
    local pid
    pid=$(cat "$PID_FILE")
    echo "running: PID $pid"
  else
    echo "not running"
  fi
}

restart() {
  stop || true
  start
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  *)
    echo "usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
