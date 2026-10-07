#!/usr/bin/env bash
# Run all browser checks (needs `playwright install chromium`). Used locally and in CI.
# Usage: scripts/run_browser_checks.sh   (uses `python` and `solara` from the active environment)
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8765}"
SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

# Solara flags for the mode: "--production" or nothing (development mode, which also uses Vue's development build).
MODE_FLAGS=""

# check_with_server <app.py> <check script>   (paths from the repository root)
check_with_server() {
  local name="${1//\//-}"
  solara run "$1" $MODE_FLAGS --port "$PORT" --no-open >"server-$name.log" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 60); do
    if curl -sf "http://localhost:$PORT" >/dev/null; then break; fi
    sleep 1
  done
  python "$2" --url "http://localhost:$PORT" --screenshot "/tmp/solara-html-${2//\//-}.png"
  cleanup
  SERVER_PID=""
}

run_all() {
  check_with_server example/greeting_app.py example/check.py
  check_with_server example/greeting_app.py example/check_sessions.py
  check_with_server example/beacon_app.py example/check_beacon.py
  check_with_server example/settings_app.py example/check_settings.py
  check_with_server example/quiz_app.py example/check_quiz.py
  check_with_server example/security_app.py example/check_security.py
  check_with_server example/todo_app.py example/check_todo.py
  check_with_server tests/browser/errors_app.py tests/browser/check_errors.py
}

MODE_FLAGS="--production"
run_all
MODE_FLAGS=""
run_all
python example/check_hot_reload.py
