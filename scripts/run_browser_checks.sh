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

# check_with_server <app.py> <check script>
check_with_server() {
  solara run "example/$1" --production --port "$PORT" --no-open >"server-$1.log" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 60); do
    if curl -sf "http://localhost:$PORT" >/dev/null; then break; fi
    sleep 1
  done
  python "example/$2" --url "http://localhost:$PORT" --screenshot "/tmp/solara-html-$2.png"
  cleanup
  SERVER_PID=""
}

check_with_server greeting_app.py check.py
check_with_server beacon_app.py check_beacon.py
check_with_server settings_app.py check_settings.py
check_with_server quiz_app.py check_quiz.py
check_with_server security_app.py check_security.py
python example/check_hot_reload.py
